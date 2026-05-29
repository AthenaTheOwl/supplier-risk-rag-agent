"""Run-evidence emitter for the supplier-risk RAG eval-suite runner.

This module is the source-of-truth emitter for two artifact types:

- Append-only Event records written as JSONL under ``ops/event-ledger/``.
- Final Run records written as JSON under ``ops/run-records/``.

Both records conform to the cross-repo CDCP schemas mirrored in
``ops/schemas-cache/event.schema.json`` and
``ops/schemas-cache/run.schema.json`` (athena-site is the source of
truth). The amended Run schema carries six replay-equivalence fields:
``prompt_snapshot_hash``, ``tool_schemas_snapshot_hash``,
``determinism``, ``checkpoint_ref``, ``sandbox_image_ref``, and
``gate_results_summary``.

A Run in this repo is one eval-suite execution: ``src/evals/runner.py``
walking one of ``retrieval_quality``, ``citation_faithfulness``,
``supplier_risk_questions``, or ``refusal_cases`` against the sample
corpus. Each suite execution emits its own Run record plus a JSONL
ledger of events fired during the run.

Field-population rules followed here:

- ``prompt_snapshot_hash``: SHA-256 of the canonicalized prompt files
  under ``src/agent/prompts/`` (answerer + refusal + planner). Always
  populated.
- ``tool_schemas_snapshot_hash``: SHA-256 of the canonicalized
  retrieval and LLM tool surface — BM25 + hashing-embedder + reranker
  config plus the LLM provider and model identifiers. Always
  populated.
- ``determinism``: populated when the suite YAML carries an explicit
  ``determinism:`` block (seed/temperature/top_p). Today the suites
  ship without one, so the field is omitted by default. The eval
  runner is fully deterministic against the sample corpus regardless
  (no sampling), but the schema treats absence as "not pinned".
- ``checkpoint_ref``: omitted. This repo has no managed-task-runtime
  checkpoint store; the eval runner runs in-process.
- ``sandbox_image_ref``: populated as
  ``repo://supplier-risk-rag-agent@<HEAD-SHA>/`` per the portable
  repo URI grammar defined in athena-site DEC-CDCP-014. Two-pass
  emit: the runner records a ``PENDING`` placeholder when the
  HEAD-SHA the commit will land at is not yet known, and
  ``scripts/finalize_sandbox_ref.py`` rewrites the SHA after the
  data files commit lands.
- ``gate_results_summary``: aggregated from ``gate.check.passed`` and
  ``gate.check.failed`` events emitted per suite-level threshold
  (recall@5 >= 0.70, citation faithfulness >= 0.95, refusal precision
  >= 0.85, supplier-risk per-case answer quality).

The validator gate at ``scripts/validate_run_evidence.py`` walks both
directories and checks every record against the cached schemas.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------- canonical hashing


def canonicalize_prompt(
    extraction_prompt: str,
    answer_prompt: str,
    refusal_prompt: str,
) -> str:
    """Return a stable canonical form of the RAG prompt surface.

    The output is a JSON-serialized mapping with sorted keys so
    byte-equal inputs always produce byte-equal canonical strings.
    Newlines inside each prompt body are preserved as-is. Callers that
    want line-ending normalization should strip CRLFs before calling.

    ``extraction_prompt`` covers the planner/extraction template,
    ``answer_prompt`` covers the answerer template, ``refusal_prompt``
    covers the refusal template. Any None value collapses to an empty
    string so the hash stays well-defined even when one prompt is
    absent.
    """
    payload = {
        "extraction_prompt": extraction_prompt or "",
        "answer_prompt": answer_prompt or "",
        "refusal_prompt": refusal_prompt or "",
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def canonicalize_tool_surface(
    retrieval_config: Mapping[str, Any],
    llm_provider: str,
    llm_model: str,
    embedding_model: str,
    reranker_config: Mapping[str, Any] | None = None,
) -> str:
    """Return a stable canonical form of the retrieval/LLM tool surface.

    ``retrieval_config`` carries vector-store + BM25 weights plus any
    other ranker-level knobs. ``llm_provider`` and ``llm_model`` carry
    the chat provider identifiers (e.g. "anthropic" + "claude-sonnet-4-6").
    ``embedding_model`` names the embedder. ``reranker_config`` is
    optional; when None the reranker section is recorded as null so the
    hash distinguishes "no reranker" from "reranker present".

    All mappings are serialized with sorted keys so the resulting hash
    is insensitive to declaration order.
    """
    payload = {
        "retrieval_config": _normalize_mapping(retrieval_config),
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "embedding_model": embedding_model,
        "reranker_config": (
            _normalize_mapping(reranker_config)
            if reranker_config is not None
            else None
        ),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _normalize_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-friendly dict copy with sorted keys at every level."""
    out: dict[str, Any] = {}
    for key in sorted(value.keys()):
        inner = value[key]
        if isinstance(inner, Mapping):
            out[key] = _normalize_mapping(inner)
        elif isinstance(inner, list | tuple):
            out[key] = [
                _normalize_mapping(item) if isinstance(item, Mapping) else item
                for item in inner
            ]
        else:
            out[key] = inner
    return out


def compute_sha256(canonical: str) -> str:
    """Return the lowercase hex SHA-256 digest of ``canonical``.

    The Run schema requires hashes to match ``^[a-f0-9]{64}$`` so the
    digest is returned without the ``sha256:`` prefix.
    """
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------- portable repo URIs

# Per athena-site DEC-CDCP-014 the run-evidence emitter produces
# portable repo:// URIs that point at this repo by name (not by
# absolute path), so a consumer in any other portfolio repo can
# resolve the reference against a shared portfolio root without
# baking in the producer's local layout.
REPO_NAME = "supplier-risk-rag-agent"

# Placeholder SHA token for the two-pass sandbox-ref emission. The
# Run record lands with this token in place of the real SHA; a
# post-commit step (``scripts/finalize_sandbox_ref.py``) rewrites
# the token to the SHA of the commit that ultimately contains the
# Run record on disk. This closes the systemic off-by-one where a
# single-pass emitter records the parent commit instead of the
# commit that wrote the sample.
PENDING_SHA_TOKEN = "PENDING"


def repo_uri(rel_path: str, sha: str | None = None) -> str:
    """Compose a ``repo://supplier-risk-rag-agent@<sha>/<rel-path>`` URI.

    ``rel_path`` is a POSIX path inside this repo (forward slashes,
    no leading slash). An empty path means the URI points at the
    repo root and the trailing slash after the SHA stays in place
    per the grammar in DEC-CDCP-014.

    ``sha`` defaults to the ``PENDING`` placeholder token (see
    :data:`PENDING_SHA_TOKEN`). Callers that already know the
    target SHA pass it explicitly.
    """
    if rel_path.startswith("/"):
        rel_path = rel_path.lstrip("/")
    rel_path = rel_path.replace("\\", "/")
    sha_token = sha if sha is not None else PENDING_SHA_TOKEN
    return f"repo://{REPO_NAME}@{sha_token}/{rel_path}"


def artifact_uri(artifact_id: str) -> str:
    """Compose an ``artifact://supplier-risk-rag-agent/<id>`` URI."""
    return f"artifact://{REPO_NAME}/{artifact_id}"


def repo_relative(path: Path | str, repo_root: Path) -> str:
    """Return a POSIX relative path from ``repo_root`` to ``path``.

    Falls back to the input string when ``path`` does not live
    under ``repo_root`` so callers can still produce a URI for an
    out-of-tree input (the consumer will fail to resolve it, which
    is the right signal).
    """
    p = Path(path)
    root = Path(repo_root)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def _git_head_sha(repo_path: Path) -> str | None:
    """Return the current HEAD SHA of ``repo_path`` or None."""
    try:
        result = subprocess.run(  # noqa: S603 - args fixed, no shell
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    head = result.stdout.strip()
    if result.returncode != 0 or not head:
        return None
    return head


def derive_sandbox_image_ref(
    repo_path: Path | None, *, sha: str | None = None
) -> str | None:
    """Return ``repo://supplier-risk-rag-agent@<sha>/`` or None.

    When ``sha`` is passed explicitly the URI uses that SHA
    verbatim. When ``sha`` is None the URI uses the
    :data:`PENDING_SHA_TOKEN` placeholder so a post-commit step can
    rewrite the value to the SHA of the commit that ultimately
    wrote the Run record to disk. ``repo_path`` is kept for
    backwards compatibility and to verify that the repo root exists
    before producing a URI that would dangle.

    A ``None`` return tells the caller to omit
    ``sandbox_image_ref`` from the Run record entirely.
    """
    if repo_path is None:
        return None
    repo = Path(repo_path).expanduser()
    if not repo.exists():
        return None
    sha_token = sha if sha is not None else PENDING_SHA_TOKEN
    return f"repo://{REPO_NAME}@{sha_token}/"


# ----------------------------------------------------------------- schema cache loader

_SCHEMA_CACHE: dict[str, Mapping[str, Any]] = {}


def _schemas_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "ops" / "schemas-cache"


def _load_schema(name: str) -> Mapping[str, Any]:
    cached = _SCHEMA_CACHE.get(name)
    if cached is not None:
        return cached
    path = _schemas_dir() / name
    if not path.is_file():
        raise FileNotFoundError(
            f"schema cache missing: {path}. "
            f"Run scripts/check_schema_cache_freshness.py."
        )
    schema = json.loads(path.read_text(encoding="utf-8"))
    _SCHEMA_CACHE[name] = schema
    return schema  # type: ignore[no-any-return]


def _validate(record: Mapping[str, Any], schema_name: str) -> None:
    try:
        import jsonschema  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "run_evidence: jsonschema is required. "
            "Install with `pip install jsonschema>=4.21`."
        ) from exc
    schema = _load_schema(schema_name)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
    if errors:
        details = "; ".join(
            f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
            for err in errors
        )
        raise ValueError(
            f"run_evidence record does not validate against {schema_name}: {details}"
        )


# ----------------------------------------------------------------- emitters


def emit_event(event: Mapping[str, Any], ledger_path: Path) -> None:
    """Append-only writer for one Event record.

    Validates ``event`` against ``event.schema.json`` before writing.
    Writes a single canonical JSON line followed by a newline so the
    file remains valid JSONL.
    """
    _validate(event, "event.schema.json")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, sort_keys=True, ensure_ascii=False)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.write("\n")


def emit_run(run: Mapping[str, Any], record_path: Path) -> None:
    """Final Run record writer.

    Validates ``run`` against ``run.schema.json`` (with the amended
    replay-equivalence fields) before writing. Writes pretty-printed
    JSON with sorted keys so the file is diff-friendly across runs.
    """
    _validate(run, "run.schema.json")
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(run, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ----------------------------------------------------------------- event factory


def now_iso() -> str:
    """Return the current UTC timestamp in RFC 3339 form with second precision."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_event_id() -> str:
    """Return a fresh UUIDv4 for use as an event_id."""
    return str(uuid.uuid4())


def new_run_id() -> str:
    """Return a fresh ``run-<12hex>`` identifier for a suite execution."""
    return f"run-{uuid.uuid4().hex[:12]}"


def make_event(
    *,
    event_type: str,
    actor_kind: str,
    actor_id: str,
    payload: Mapping[str, Any],
    run_id: str | None = None,
    spec_id: str | None = None,
    artifact_id: str | None = None,
    parent_event_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Construct an Event record dict conformant to ``event.schema.json``.

    The factory caller passes ``event_type`` (for example
    ``tool.call.completed``), the actor descriptor, and a payload
    mapping. Optional fields are included only when supplied so the
    resulting dict matches the schema's ``additionalProperties: false``
    constraint.
    """
    event: dict[str, Any] = {
        "event_id": new_event_id(),
        "type": event_type,
        "created_at": created_at or now_iso(),
        "actor": {"kind": actor_kind, "id": actor_id},
        "payload": dict(payload),
    }
    if run_id is not None:
        event["run_id"] = run_id
    if spec_id is not None:
        event["spec_id"] = spec_id
    if artifact_id is not None:
        event["artifact_id"] = artifact_id
    if parent_event_id is not None:
        event["parent_event_id"] = parent_event_id
    return event


# ----------------------------------------------------------------- replay fields builder


@dataclass(frozen=True)
class RunEvidenceFields:
    """The six replay-equivalence fields plus the list of names populated."""

    fields: dict[str, Any]
    populated: list[str]


def build_run_evidence_fields(
    *,
    extraction_prompt: str,
    answer_prompt: str,
    refusal_prompt: str,
    retrieval_config: Mapping[str, Any],
    llm_provider: str,
    llm_model: str,
    embedding_model: str,
    reranker_config: Mapping[str, Any] | None,
    repo_path: Path | None,
    gate_events: Iterable[Mapping[str, Any]],
    determinism: Mapping[str, Any] | None = None,
    sandbox_sha: str | None = None,
) -> RunEvidenceFields:
    """Compute the six replay-equivalence fields where derivable.

    ``gate_events`` is an iterable of Event records (mapping form)
    whose ``type`` matches ``gate.check.passed`` or
    ``gate.check.failed``. The aggregator pulls each event's
    ``payload.gate_name`` and splits the names into the two summary
    lists.

    ``determinism`` is included when the caller supplies a non-empty
    mapping carrying any of ``seed``, ``temperature``, ``top_p``; an
    empty or None value omits the field per the field rules above.

    Returns a :class:`RunEvidenceFields` whose ``fields`` mapping is
    ready to merge into a Run record and whose ``populated`` list is
    suitable for the ``gate.run.evidence_recorded`` event payload.
    """
    fields: dict[str, Any] = {}
    populated: list[str] = []

    prompt_hash = compute_sha256(
        canonicalize_prompt(extraction_prompt, answer_prompt, refusal_prompt)
    )
    fields["prompt_snapshot_hash"] = prompt_hash
    populated.append("prompt_snapshot_hash")

    tool_hash = compute_sha256(
        canonicalize_tool_surface(
            retrieval_config,
            llm_provider,
            llm_model,
            embedding_model,
            reranker_config,
        )
    )
    fields["tool_schemas_snapshot_hash"] = tool_hash
    populated.append("tool_schemas_snapshot_hash")

    if determinism:
        # Drop any keys not allowed by the schema so callers can pass a
        # superset without breaking validation.
        allowed = {"seed", "temperature", "top_p"}
        clean = {k: v for k, v in determinism.items() if k in allowed and v is not None}
        if clean:
            fields["determinism"] = clean
            populated.append("determinism")

    sandbox_ref = derive_sandbox_image_ref(repo_path, sha=sandbox_sha)
    if sandbox_ref is not None:
        fields["sandbox_image_ref"] = sandbox_ref
        populated.append("sandbox_image_ref")

    summary = aggregate_gate_results(gate_events)
    if summary is not None:
        fields["gate_results_summary"] = summary
        populated.append("gate_results_summary")

    return RunEvidenceFields(fields=fields, populated=populated)


def aggregate_gate_results(
    gate_events: Iterable[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Aggregate ``gate.check.passed`` / ``gate.check.failed`` events.

    Returns ``None`` if the iterable carries no gate-check events so
    the caller can omit ``gate_results_summary`` for runs that ran zero
    gates.
    """
    passed: list[str] = []
    failed: list[str] = []
    seen_any = False
    for event in gate_events:
        event_type = event.get("type", "")
        if not isinstance(event_type, str) or not event_type.startswith(
            "gate.check."
        ):
            continue
        seen_any = True
        payload = event.get("payload") or {}
        name = payload.get("gate_name") if isinstance(payload, Mapping) else None
        if not isinstance(name, str) or not name:
            name = event_type
        if event_type == "gate.check.passed":
            passed.append(name)
        elif event_type == "gate.check.failed":
            failed.append(name)
    if not seen_any:
        return None
    return {
        "gates_passed": passed,
        "gates_failed": failed,
        "all_passed": not failed,
    }


# ----------------------------------------------------------------- prompt loader


def load_prompt_files(prompts_dir: Path) -> tuple[str, str, str]:
    """Read the three RAG prompt files; missing files collapse to empty.

    Returns ``(extraction_prompt, answer_prompt, refusal_prompt)`` in
    the same order :func:`canonicalize_prompt` expects. The
    extraction-prompt slot maps to ``planner.md`` so the same module
    can serve a richer planning pipeline later without changing the
    canonicalization shape.
    """
    extraction = _read_or_empty(prompts_dir / "planner.md")
    answer = _read_or_empty(prompts_dir / "answerer.md")
    refusal = _read_or_empty(prompts_dir / "refusal.md")
    return extraction, answer, refusal


def _read_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""
