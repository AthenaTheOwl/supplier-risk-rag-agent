"""Validate run-evidence artifacts emitted by the eval-suite runner.

Walks two directories and validates each record against the cross-repo
schemas mirrored in ``ops/schemas-cache/``:

- ``ops/event-ledger/<run-id>.jsonl`` — append-only event ledger files;
  each line must be a JSON object conforming to ``event.schema.json``.
- ``ops/run-records/<run-id>.json`` — final Run records; each file
  must conform to the amended ``run.schema.json`` carrying the six
  replay-equivalence fields.

Cross-check: every ``run_id`` referenced by an event in the ledger
must either have a matching Run record file or be flagged as
in-progress (distinct from absent — an in-progress run is one whose
ledger lacks a ``pipeline.done`` or ``gate.run.evidence_recorded``
terminal event).

Round 3 added Run-level required-for-done enforcement plus four
cross-checks that pair the Run record against its ledger:

1. ``Run.prompt_snapshot_hash`` matches the ``pipeline.start`` event's
   payload ``prompt_snapshot_hash``.
2. ``Run.tool_schemas_snapshot_hash`` matches the ``pipeline.start``
   event's payload ``tool_schemas_snapshot_hash``.
3. ``gate.run.evidence_recorded.payload.fields_populated`` matches the
   set of replay-equivalence fields actually populated on the Run.
4. ``Run.gate_results_summary`` matches the rollup of
   ``gate.check.passed`` / ``gate.check.failed`` event names.

A Run whose ``status == "done"`` MUST also carry
``prompt_snapshot_hash``, ``tool_schemas_snapshot_hash``,
``sandbox_image_ref``, and ``gate_results_summary`` populated. Done
Runs without a terminal ``gate.run.evidence_recorded`` event in the
ledger also fail.

Exit codes: ``0`` OK, ``1`` violations found. Violation detail is
written to stderr in the same shape as ``scripts/validate_decisions.py``.

This validator follows the offline-first pattern used by the other
``validate_*.py`` scripts: it loads the cached schema, never talks to
the network, and treats a missing schema cache file as a hard error.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Portable URI grammar from athena-site DEC-CDCP-014. Run-evidence
# refs may carry one of two URI schemes (repo:// for file references
# at a pinned SHA, artifact:// for logical artifact references) or a
# legacy local path (kept accepted during the migration round).
_REPO_URI_RE = re.compile(
    r"^repo://(?P<repo>[a-z][a-z0-9-]*)@(?P<sha>[a-f0-9]{40}|PENDING)/(?P<path>.*)$"
)
_ARTIFACT_URI_RE = re.compile(
    r"^artifact://(?P<repo>[a-z][a-z0-9-]*)/(?P<id>.+)$"
)


def resolve_uri(
    uri: str, portfolio_root: Path | None = None
) -> Path | None:
    """Resolve a ``repo://`` URI to a local path or pass legacy paths through.

    Returns ``None`` for ``artifact://`` URIs (artifact refs are
    logical ids, not file paths). Returns the URI as a ``Path``
    when the input does not match either scheme, which is the
    legacy-local-path branch the interop clause in DEC-CDCP-014
    keeps accepting during the migration round.

    ``portfolio_root`` defaults to ``e:/claude_code/random-apps`` so
    the validator can resolve a sibling repo's URI without
    consulting the producer's local layout.
    """
    if portfolio_root is None:
        portfolio_root = Path("e:/claude_code/random-apps")
    m = _REPO_URI_RE.match(uri)
    if m:
        return portfolio_root / m["repo"] / m["path"]
    m = _ARTIFACT_URI_RE.match(uri)
    if m:
        return None  # artifact refs are not file paths
    return Path(uri)
CACHE_DIR = ROOT / "ops" / "schemas-cache"
EVENT_LEDGER_DIR = ROOT / "ops" / "event-ledger"
RUN_RECORDS_DIR = ROOT / "ops" / "run-records"

EVENT_SCHEMA_PATH = CACHE_DIR / "event.schema.json"
RUN_SCHEMA_PATH = CACHE_DIR / "run.schema.json"

# Terminal event types: presence in a ledger means the run is no
# longer in-progress. A missing Run record alongside any of these
# types is a violation.
TERMINAL_EVENT_TYPES = frozenset(
    {"gate.run.evidence_recorded", "pipeline.done"}
)


def _load_schema(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(
            f"validate_run_evidence: cached schema missing at "
            f"{path.relative_to(ROOT).as_posix()}. Re-cache from athena-site."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _validator_for(schema: dict[str, Any]) -> Any:
    try:
        import jsonschema  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "validate_run_evidence: jsonschema is required. "
            "Install with `pip install jsonschema>=4.21`."
        ) from exc
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def _format_errors(prefix: str, errors: list[Any]) -> list[str]:
    formatted: list[str] = []
    for err in errors:
        location = "/".join(str(part) for part in err.path) or "<root>"
        formatted.append(f"{prefix}: {location}: {err.message}")
    return formatted


def _safe_rel(path: Path) -> str:
    """Return ``path`` relative to ROOT when possible, else the absolute form."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


# Round 3: required-for-done fields on the Run record. Absence (or
# empty value) for any of these on a Run whose ``status == "done"``
# is a validation failure.
REQUIRED_FIELDS_FOR_DONE = (
    "prompt_snapshot_hash",
    "tool_schemas_snapshot_hash",
    "sandbox_image_ref",
    "gate_results_summary",
)

# Round 3: the set of replay-equivalence field names the
# ``gate.run.evidence_recorded`` payload ``fields_populated`` can
# carry. Must mirror the enum in event.schema.json.
REPLAY_EQUIVALENCE_FIELDS = frozenset(
    {
        "prompt_snapshot_hash",
        "tool_schemas_snapshot_hash",
        "determinism",
        "checkpoint_ref",
        "sandbox_image_ref",
        "gate_results_summary",
    }
)


def validate_event_ledger(
    validator: Any,
) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
    """Walk every JSONL ledger file and validate every line.

    Returns ``(violations, run_to_events)`` where ``run_to_events``
    maps each referenced run_id to the list of parsed event dicts in
    file order. Events whose ``run_id`` cannot be parsed are skipped
    from the map but still validated.
    """
    violations: list[str] = []
    run_to_events: dict[str, list[dict[str, Any]]] = {}
    if not EVENT_LEDGER_DIR.is_dir():
        return violations, run_to_events
    for ledger in sorted(EVENT_LEDGER_DIR.glob("*.jsonl")):
        rel = _safe_rel(ledger)
        text = ledger.read_text(encoding="utf-8")
        for line_no, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError as exc:
                violations.append(f"{rel}:{line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(event, dict):
                violations.append(
                    f"{rel}:{line_no}: top-level value must be a JSON object"
                )
                continue
            errs = sorted(
                validator.iter_errors(event), key=lambda e: e.path
            )
            violations.extend(_format_errors(f"{rel}:{line_no}", errs))
            run_id = event.get("run_id")
            if isinstance(run_id, str) and run_id:
                run_to_events.setdefault(run_id, []).append(event)
    return violations, run_to_events


def validate_run_records(
    validator: Any,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Walk every Run record file and validate the JSON body.

    Returns ``(violations, run_id_to_record)`` so cross-checks can read
    the Run record without re-loading the file.
    """
    violations: list[str] = []
    recorded: dict[str, dict[str, Any]] = {}
    if not RUN_RECORDS_DIR.is_dir():
        return violations, recorded
    for record in sorted(RUN_RECORDS_DIR.glob("*.json")):
        rel = _safe_rel(record)
        try:
            run = json.loads(record.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            violations.append(f"{rel}: invalid JSON: {exc}")
            continue
        if not isinstance(run, dict):
            violations.append(f"{rel}: top-level value must be a JSON object")
            continue
        errs = sorted(validator.iter_errors(run), key=lambda e: e.path)
        violations.extend(_format_errors(rel, errs))
        run_id = run.get("id")
        if isinstance(run_id, str) and run_id:
            recorded[run_id] = run
    return violations, recorded


def _replay_fields_populated_on_run(run: dict[str, Any]) -> list[str]:
    """Return the sorted list of replay-equivalence fields present on a Run.

    A field counts as populated when the key is on the Run record and
    the value is truthy (a non-empty string, a non-empty mapping, or a
    non-empty list). This matches the producer's `RunEvidenceFields`
    semantics in `src/evals/run_evidence.py`.
    """
    populated: list[str] = []
    for name in REPLAY_EQUIVALENCE_FIELDS:
        value = run.get(name)
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        populated.append(name)
    return sorted(populated)


def _aggregate_gate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a gate_results_summary from gate.check.* events in a ledger."""
    passed: list[str] = []
    failed: list[str] = []
    for event in events:
        event_type = event.get("type", "")
        if not isinstance(event_type, str):
            continue
        if event_type not in {"gate.check.passed", "gate.check.failed"}:
            continue
        payload = event.get("payload") or {}
        name = payload.get("gate_name") if isinstance(payload, dict) else None
        if not isinstance(name, str) or not name:
            continue
        if event_type == "gate.check.passed":
            passed.append(name)
        else:
            failed.append(name)
    return {
        "gates_passed": sorted(passed),
        "gates_failed": sorted(failed),
        "all_passed": len(failed) == 0,
    }


def _normalize_summary(summary: Any) -> dict[str, Any] | None:
    """Return a gate_results_summary normalised for set-equality comparison.

    Both Round-3 cross-check sides sort the gate-name lists so the
    comparison stays insensitive to emission order.
    """
    if not isinstance(summary, dict):
        return None
    passed = summary.get("gates_passed") or []
    failed = summary.get("gates_failed") or []
    if not isinstance(passed, list) or not isinstance(failed, list):
        return None
    return {
        "gates_passed": sorted(str(n) for n in passed),
        "gates_failed": sorted(str(n) for n in failed),
        "all_passed": bool(summary.get("all_passed", len(failed) == 0)),
    }


def cross_check(
    run_to_events: dict[str, list[dict[str, Any]]],
    recorded: dict[str, dict[str, Any]],
) -> list[str]:
    """Cross-check Run records against their event ledger.

    Enforces:

    - terminal-event-present-but-no-record (legacy round-2 check),
    - required-for-done fields populated on a Run whose ``status``
      is ``"done"``,
    - presence of at least one ``gate.run.evidence_recorded`` event
      for a done Run,
    - the four Round-3 cross-checks tying ``pipeline.start``,
      ``gate.run.evidence_recorded``, and ``gate.check.*`` events back
      to the Run record's replay-equivalence fields.
    """
    violations: list[str] = []
    run_ids_in_events = set(run_to_events.keys())

    # Legacy round-2 cross-check: terminal-event-no-record.
    for run_id in sorted(run_ids_in_events):
        types = {e.get("type", "") for e in run_to_events.get(run_id, [])}
        has_terminal = bool(types & TERMINAL_EVENT_TYPES)
        if has_terminal and run_id not in recorded:
            violations.append(
                f"run_id {run_id!r}: ledger carries terminal event "
                f"({sorted(types & TERMINAL_EVENT_TYPES)}) but no matching "
                f"ops/run-records/{run_id}.json"
            )

    # Round-3 cross-checks. Iterate the union so a Run record without a
    # ledger also fails loudly.
    all_run_ids = run_ids_in_events | set(recorded.keys())
    for run_id in sorted(all_run_ids):
        run = recorded.get(run_id)
        events = run_to_events.get(run_id, [])
        if run is None:
            # A run referenced from the ledger without a record is
            # already flagged above when a terminal event is present.
            continue

        status = run.get("status")
        is_done = status == "done"

        # Required-for-done fields.
        if is_done:
            for field in REQUIRED_FIELDS_FOR_DONE:
                value = run.get(field)
                if value is None:
                    violations.append(
                        f"run_id {run_id!r}: status=done but required field "
                        f"{field!r} is missing"
                    )
                    continue
                if isinstance(value, str) and not value:
                    violations.append(
                        f"run_id {run_id!r}: status=done but required field "
                        f"{field!r} is empty"
                    )
                elif isinstance(value, (list, dict)) and not value:
                    violations.append(
                        f"run_id {run_id!r}: status=done but required field "
                        f"{field!r} is empty"
                    )

        # Required terminal event for done Runs.
        evidence_events = [
            e for e in events if e.get("type") == "gate.run.evidence_recorded"
        ]
        if is_done and not evidence_events:
            violations.append(
                f"run_id {run_id!r}: status=done but no "
                f"gate.run.evidence_recorded event in the ledger"
            )

        # Cross-check #1 + #2: pipeline.start hashes match Run.
        start_events = [e for e in events if e.get("type") == "pipeline.start"]
        if start_events:
            start_payload = start_events[0].get("payload") or {}
            run_prompt = run.get("prompt_snapshot_hash")
            start_prompt = start_payload.get("prompt_snapshot_hash") if isinstance(start_payload, dict) else None
            if run_prompt is not None and start_prompt is not None and run_prompt != start_prompt:
                violations.append(
                    f"run_id {run_id!r}: prompt_snapshot_hash mismatch "
                    f"(Run={run_prompt!r} != pipeline.start={start_prompt!r})"
                )
            run_tools = run.get("tool_schemas_snapshot_hash")
            start_tools = start_payload.get("tool_schemas_snapshot_hash") if isinstance(start_payload, dict) else None
            if run_tools is not None and start_tools is not None and run_tools != start_tools:
                violations.append(
                    f"run_id {run_id!r}: tool_schemas_snapshot_hash mismatch "
                    f"(Run={run_tools!r} != pipeline.start={start_tools!r})"
                )

        # Cross-check #3: gate.run.evidence_recorded.fields_populated
        # equals the set of replay-equivalence fields populated on the
        # Run. Compare as sorted sets.
        for evidence in evidence_events:
            payload = evidence.get("payload") or {}
            if not isinstance(payload, dict):
                continue
            declared = payload.get("fields_populated")
            if not isinstance(declared, list):
                continue
            declared_sorted = sorted(str(name) for name in declared)
            actual_sorted = _replay_fields_populated_on_run(run)
            if declared_sorted != actual_sorted:
                violations.append(
                    f"run_id {run_id!r}: gate.run.evidence_recorded "
                    f"fields_populated {declared_sorted!r} does not match "
                    f"replay-equivalence fields populated on Run "
                    f"{actual_sorted!r}"
                )

        # Cross-check #4: Run.gate_results_summary matches the
        # rollup of gate.check.* events.
        run_summary = _normalize_summary(run.get("gate_results_summary"))
        if run_summary is not None:
            event_summary = _aggregate_gate_events(events)
            if run_summary != event_summary:
                violations.append(
                    f"run_id {run_id!r}: gate_results_summary mismatch "
                    f"(Run={run_summary!r} != events={event_summary!r})"
                )

    return violations


def main() -> int:
    event_schema = _load_schema(EVENT_SCHEMA_PATH)
    run_schema = _load_schema(RUN_SCHEMA_PATH)
    event_validator = _validator_for(event_schema)
    run_validator = _validator_for(run_schema)

    event_violations, run_to_events = validate_event_ledger(event_validator)
    record_violations, recorded = validate_run_records(run_validator)
    cross_violations = cross_check(run_to_events, recorded)

    all_violations = event_violations + record_violations + cross_violations
    if all_violations:
        for line in all_violations:
            print(line, file=sys.stderr)
        print(
            f"validate_run_evidence: {len(all_violations)} violation(s) found",
            file=sys.stderr,
        )
        return 1

    n_events = sum(len(v) for v in run_to_events.values())
    print(
        f"validate_run_evidence OK ("
        f"{n_events} event(s), "
        f"{len(recorded)} run record(s), "
        f"{len(run_to_events)} run_id(s) referenced)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
