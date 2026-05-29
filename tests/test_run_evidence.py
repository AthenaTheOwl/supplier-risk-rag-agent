"""Unit and integration tests for the run-evidence emitter.

The unit tests cover the emitter helpers in isolation. The integration
test drives ``src/evals/runner.py`` end-to-end against the checked-in
sample corpus and verifies that one suite execution produces one Run
record plus a matching JSONL ledger that the validator accepts.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from src.evals.run_evidence import (
    PENDING_SHA_TOKEN,
    REPO_NAME,
    aggregate_gate_results,
    artifact_uri,
    build_run_evidence_fields,
    canonicalize_prompt,
    canonicalize_tool_surface,
    compute_sha256,
    derive_sandbox_image_ref,
    emit_event,
    emit_run,
    load_prompt_files,
    make_event,
    new_run_id,
    repo_relative,
    repo_uri,
)

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------- helpers


def _retrieval_config() -> dict[str, object]:
    return {
        "ranker": "hybrid",
        "bm25_weight": 0.60,
        "vector_weight": 0.25,
        "overlap_weight": 0.15,
        "top_k": 5,
    }


# --------------------------------------------------------------------- canonical


def test_canonicalize_prompt_is_stable_across_calls() -> None:
    a = canonicalize_prompt("plan", "answer", "refuse")
    b = canonicalize_prompt("plan", "answer", "refuse")
    assert a == b


def test_canonicalize_prompt_payload_shape() -> None:
    body = canonicalize_prompt("plan", "answer", "refuse")
    parsed = json.loads(body)
    assert parsed == {
        "extraction_prompt": "plan",
        "answer_prompt": "answer",
        "refusal_prompt": "refuse",
    }


def test_canonicalize_prompt_distinguishes_inputs() -> None:
    a = canonicalize_prompt("one", "x", "y")
    b = canonicalize_prompt("two", "x", "y")
    assert a != b


def test_canonicalize_tool_surface_is_order_insensitive() -> None:
    a = canonicalize_tool_surface(
        {"ranker": "hybrid", "top_k": 5, "bm25_weight": 0.6},
        "anthropic",
        "claude-sonnet-4-6",
        "hashing",
        None,
    )
    b = canonicalize_tool_surface(
        {"bm25_weight": 0.6, "top_k": 5, "ranker": "hybrid"},
        "anthropic",
        "claude-sonnet-4-6",
        "hashing",
        None,
    )
    assert a == b


def test_canonicalize_tool_surface_distinguishes_reranker_presence() -> None:
    no_reranker = canonicalize_tool_surface(
        _retrieval_config(), "anthropic", "claude-sonnet-4-6", "hashing", None
    )
    with_reranker = canonicalize_tool_surface(
        _retrieval_config(),
        "anthropic",
        "claude-sonnet-4-6",
        "hashing",
        {"model": "cross-encoder/ms-marco-MiniLM-L-6-v2", "candidate_pool": 50},
    )
    assert no_reranker != with_reranker


def test_compute_sha256_returns_64_lowercase_hex() -> None:
    digest = compute_sha256("anything")
    assert re.match(r"^[a-f0-9]{64}$", digest)


def test_compute_sha256_matches_known_vector() -> None:
    assert compute_sha256("") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


# --------------------------------------------------------------------- emitters


def test_emit_event_writes_valid_jsonl(tmp_path: Path) -> None:
    ledger = tmp_path / "run-abc.jsonl"
    event = make_event(
        event_type="tool.call.completed",
        actor_kind="role",
        actor_id="science.proof-gate-runner",
        payload={"tool_name": "ranker.search", "status": "ok", "n_results": 5},
        run_id="run-abc",
    )
    emit_event(event, ledger)
    text = ledger.read_text(encoding="utf-8")
    assert text.endswith("\n")
    parsed = json.loads(text.splitlines()[0])
    assert parsed["type"] == "tool.call.completed"
    assert parsed["payload"]["tool_name"] == "ranker.search"
    assert parsed["run_id"] == "run-abc"


def test_emit_event_appends_a_second_line(tmp_path: Path) -> None:
    ledger = tmp_path / "run-abc.jsonl"
    a = make_event(
        event_type="pipeline.start",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={
            "suite": "refusal_cases",
            "prompt_snapshot_hash": compute_sha256("plan|answer|refuse"),
            "tool_schemas_snapshot_hash": compute_sha256("toolset"),
        },
        run_id="run-abc",
    )
    b = make_event(
        event_type="gate.check.passed",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={"gate_name": "refusal_precision_threshold", "score": 0.9},
        run_id="run-abc",
        parent_event_id=a["event_id"],
    )
    emit_event(a, ledger)
    emit_event(b, ledger)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["parent_event_id"] == a["event_id"]


def test_emit_event_rejects_invalid_event(tmp_path: Path) -> None:
    ledger = tmp_path / "run-bad.jsonl"
    bad = {"type": "tool.call.started"}  # missing event_id, created_at, actor, payload
    with pytest.raises(ValueError):
        emit_event(bad, ledger)
    assert not ledger.exists()


def test_emit_run_writes_valid_record_with_replay_fields(tmp_path: Path) -> None:
    record_path = tmp_path / "run-xyz.json"
    run = {
        "id": "run-xyz",
        "spec_id": "eval_suites/refusal_cases.yaml",
        "agent_id": "anthropic:claude-sonnet-4-6",
        "runtime": "supplier-risk-rag-agent-evals",
        "workspace_id": REPO_NAME,
        "started_at": "2026-05-27T20:00:00Z",
        "finished_at": "2026-05-27T20:01:00Z",
        "status": "done",
        "inputs": [
            {
                "kind": "eval_suite",
                "ref": repo_uri("eval_suites/refusal_cases.yaml"),
            }
        ],
        "outputs": [],
        "prompt_snapshot_hash": compute_sha256("plan|answer|refuse"),
        "tool_schemas_snapshot_hash": compute_sha256("toolset"),
        "sandbox_image_ref": f"repo://{REPO_NAME}@{'d' * 40}/",
        "gate_results_summary": {
            "gates_passed": ["refusal_precision_threshold"],
            "gates_failed": [],
            "all_passed": True,
        },
    }
    emit_run(run, record_path)
    parsed = json.loads(record_path.read_text(encoding="utf-8"))
    assert parsed["id"] == "run-xyz"
    assert re.match(r"^[a-f0-9]{64}$", parsed["prompt_snapshot_hash"])
    assert parsed["gate_results_summary"]["all_passed"] is True
    assert parsed["sandbox_image_ref"].startswith(f"repo://{REPO_NAME}@")
    assert parsed["workspace_id"] == REPO_NAME
    assert parsed["inputs"][0]["ref"].startswith(f"repo://{REPO_NAME}@")


def test_emit_run_rejects_invalid_record(tmp_path: Path) -> None:
    record_path = tmp_path / "run-bad.json"
    bad_run = {"id": "run-bad"}  # missing required fields
    with pytest.raises(ValueError):
        emit_run(bad_run, record_path)
    assert not record_path.exists()


# --------------------------------------------------------------------- aggregator


def test_aggregate_gate_results_returns_none_when_no_gate_events() -> None:
    assert aggregate_gate_results([]) is None
    other = make_event(
        event_type="tool.call.completed",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={"tool_name": "ranker.search", "status": "ok"},
        run_id="run-1",
    )
    assert aggregate_gate_results([other]) is None


def test_aggregate_gate_results_splits_pass_and_fail() -> None:
    passed = make_event(
        event_type="gate.check.passed",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={"gate_name": "recall_at_5_threshold", "score": 1.0},
        run_id="run-1",
    )
    failed = make_event(
        event_type="gate.check.failed",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={"gate_name": "citation_faithfulness_threshold", "score": 0.93},
        run_id="run-1",
    )
    summary = aggregate_gate_results([passed, failed])
    assert summary == {
        "gates_passed": ["recall_at_5_threshold"],
        "gates_failed": ["citation_faithfulness_threshold"],
        "all_passed": False,
    }


def test_aggregate_gate_results_all_passed_when_no_failures() -> None:
    passed = make_event(
        event_type="gate.check.passed",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={"gate_name": "refusal_precision_threshold", "score": 0.9},
        run_id="run-1",
    )
    summary = aggregate_gate_results([passed])
    assert summary is not None
    assert summary["all_passed"] is True
    assert summary["gates_failed"] == []


# --------------------------------------------------------------------- replay fields


def test_build_run_evidence_fields_populates_two_hashes_minimum() -> None:
    result = build_run_evidence_fields(
        extraction_prompt="plan",
        answer_prompt="answer",
        refusal_prompt="refuse",
        retrieval_config=_retrieval_config(),
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        embedding_model="hashing",
        reranker_config=None,
        repo_path=None,
        gate_events=[],
    )
    assert "prompt_snapshot_hash" in result.fields
    assert "tool_schemas_snapshot_hash" in result.fields
    assert "sandbox_image_ref" not in result.fields
    assert "gate_results_summary" not in result.fields
    assert "determinism" not in result.fields
    assert set(result.populated) == {
        "prompt_snapshot_hash",
        "tool_schemas_snapshot_hash",
    }


def test_build_run_evidence_fields_populates_determinism_when_given() -> None:
    result = build_run_evidence_fields(
        extraction_prompt="plan",
        answer_prompt="answer",
        refusal_prompt="refuse",
        retrieval_config=_retrieval_config(),
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        embedding_model="hashing",
        reranker_config=None,
        repo_path=None,
        gate_events=[],
        determinism={"temperature": 0.0, "seed": 42},
    )
    assert result.fields["determinism"] == {"temperature": 0.0, "seed": 42}
    assert "determinism" in result.populated


def test_build_run_evidence_fields_omits_empty_determinism() -> None:
    result = build_run_evidence_fields(
        extraction_prompt="plan",
        answer_prompt="answer",
        refusal_prompt="refuse",
        retrieval_config=_retrieval_config(),
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        embedding_model="hashing",
        reranker_config=None,
        repo_path=None,
        gate_events=[],
        determinism={},
    )
    assert "determinism" not in result.fields


def test_build_run_evidence_fields_populates_gate_summary() -> None:
    passed = make_event(
        event_type="gate.check.passed",
        actor_kind="system",
        actor_id="supplier-risk-rag-agent-evals",
        payload={"gate_name": "recall_at_5_threshold", "score": 1.0},
        run_id="run-1",
    )
    result = build_run_evidence_fields(
        extraction_prompt="plan",
        answer_prompt="answer",
        refusal_prompt="refuse",
        retrieval_config=_retrieval_config(),
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        embedding_model="hashing",
        reranker_config=None,
        repo_path=None,
        gate_events=[passed],
    )
    assert "gate_results_summary" in result.fields
    assert result.fields["gate_results_summary"]["all_passed"] is True
    assert "gate_results_summary" in result.populated


def test_derive_sandbox_image_ref_returns_none_for_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    assert derive_sandbox_image_ref(missing) is None
    assert derive_sandbox_image_ref(None) is None


def test_derive_sandbox_image_ref_defaults_to_pending_token(
    tmp_path: Path,
) -> None:
    """Without an explicit SHA the emitter records the PENDING placeholder.

    The two-pass emission pattern (the runner emits PENDING and a
    post-commit step rewrites the value) means the default path
    must produce the placeholder, not the working-tree HEAD.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    ref = derive_sandbox_image_ref(repo)
    assert ref == f"repo://{REPO_NAME}@{PENDING_SHA_TOKEN}/"


def test_derive_sandbox_image_ref_uses_explicit_sha_when_passed(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    sha = "a" * 40
    ref = derive_sandbox_image_ref(repo, sha=sha)
    assert ref == f"repo://{REPO_NAME}@{sha}/"


# --------------------------------------------------------------------- portable URIs


def test_repo_uri_default_sha_is_pending() -> None:
    uri = repo_uri("eval_suites/refusal_cases.yaml")
    assert uri == (
        f"repo://{REPO_NAME}@{PENDING_SHA_TOKEN}/"
        "eval_suites/refusal_cases.yaml"
    )


def test_repo_uri_with_explicit_sha() -> None:
    sha = "f" * 40
    uri = repo_uri("eval_suites/refusal_cases.yaml", sha=sha)
    assert uri == (
        f"repo://{REPO_NAME}@{sha}/eval_suites/refusal_cases.yaml"
    )


def test_repo_uri_strips_windows_backslashes() -> None:
    uri = repo_uri("eval_suites\\refusal_cases.yaml", sha="0" * 40)
    assert "\\" not in uri
    assert uri.endswith("/eval_suites/refusal_cases.yaml")


def test_artifact_uri_shape() -> None:
    uri = artifact_uri("watchlist-packet@run-abc")
    assert uri == f"artifact://{REPO_NAME}/watchlist-packet@run-abc"


def test_repo_relative_strips_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    sub = repo / "eval_suites"
    sub.mkdir(parents=True)
    target = sub / "refusal_cases.yaml"
    target.write_text("cases: []\n", encoding="utf-8")
    rel = repo_relative(target, repo)
    assert rel == "eval_suites/refusal_cases.yaml"


# --------------------------------------------------------------------- resolve_uri


def _load_resolve_uri() -> object:
    """Import the validator's resolve_uri without a package layout.

    The ``scripts/`` directory is not a Python package; load the
    module via importlib so the helper test can call resolve_uri
    without inserting scripts/ on the global sys.path.
    """
    import importlib.util

    path = ROOT / "scripts" / "validate_run_evidence.py"
    spec = importlib.util.spec_from_file_location(
        "supplier_risk_rag_agent_validate_run_evidence", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_uri  # type: ignore[attr-defined]


def test_resolve_uri_repo_form_to_local_path(tmp_path: Path) -> None:
    resolve_uri = _load_resolve_uri()
    portfolio = tmp_path / "random-apps"
    uri = (
        f"repo://supplier-risk-rag-agent@{'a' * 40}/"
        "eval_suites/refusal_cases.yaml"
    )
    resolved = resolve_uri(uri, portfolio_root=portfolio)
    assert resolved == (
        portfolio
        / "supplier-risk-rag-agent"
        / "eval_suites"
        / "refusal_cases.yaml"
    )


def test_resolve_uri_artifact_form_returns_none() -> None:
    resolve_uri = _load_resolve_uri()
    uri = "artifact://supplier-risk-rag-agent/watchlist-packet@run-abc"
    assert resolve_uri(uri) is None


def test_resolve_uri_legacy_path_passes_through() -> None:
    resolve_uri = _load_resolve_uri()
    legacy = "/abs/path/to/repo/eval_suites/refusal_cases.yaml"
    assert resolve_uri(legacy) == Path(legacy)


def test_resolve_uri_malformed_uri_treated_as_legacy_path() -> None:
    resolve_uri = _load_resolve_uri()
    # Missing SHA segment; the regex does not match so the value
    # falls through to the legacy-path branch and is returned as a
    # plain Path.
    weird = "repo://supplier-risk-rag-agent/eval_suites/refusal_cases.yaml"
    assert resolve_uri(weird) == Path(weird)


def test_new_run_id_shape() -> None:
    rid = new_run_id()
    assert rid.startswith("run-")
    assert re.match(r"^run-[0-9a-f]{12}$", rid)


def test_load_prompt_files_returns_three_strings() -> None:
    prompts_dir = ROOT / "src" / "agent" / "prompts"
    extraction, answer, refusal = load_prompt_files(prompts_dir)
    assert isinstance(extraction, str)
    assert isinstance(answer, str)
    assert isinstance(refusal, str)
    # The shipped prompts are non-empty; this guards against an
    # accidental rename or move of the prompt directory.
    assert answer.strip()
    assert refusal.strip()


def test_load_prompt_files_handles_missing_directory(tmp_path: Path) -> None:
    extraction, answer, refusal = load_prompt_files(tmp_path / "nope")
    assert extraction == ""
    assert answer == ""
    assert refusal == ""


# --------------------------------------------------------------------- validator
# Round 3: positive + negative cross-check tests for
# scripts/validate_run_evidence.py. Each test stages a synthetic
# ops/event-ledger + ops/run-records pair under tmp_path and drives
# the validator as a subprocess, mirroring how the gates.yml workflow
# invokes it.


def _validator_path() -> Path:
    return ROOT / "scripts" / "validate_run_evidence.py"


def _seed_schemas_cache(synthetic_root: Path) -> None:
    """Copy the cached schemas into a synthetic repo root."""
    import shutil

    (synthetic_root / "ops").mkdir(exist_ok=True)
    shutil.copytree(
        ROOT / "ops" / "schemas-cache",
        synthetic_root / "ops" / "schemas-cache",
    )
    shutil.copytree(ROOT / "scripts", synthetic_root / "scripts")


def _write_artifacts(
    synthetic_root: Path,
    run_id: str,
    *,
    events: list[dict[str, object]],
    run_record: dict[str, object],
) -> None:
    ledger_dir = synthetic_root / "ops" / "event-ledger"
    record_dir = synthetic_root / "ops" / "run-records"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    record_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / f"{run_id}.jsonl"
    with ledger_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True))
            handle.write("\n")
    record_path = record_dir / f"{run_id}.json"
    record_path.write_text(
        json.dumps(run_record, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _well_formed_pair(run_id: str = "run-positive001") -> tuple[
    list[dict[str, object]], dict[str, object]
]:
    """Produce a positive (validator-passing) ledger + Run pair.

    Hash values are stable so the cross-check sees equality between
    Run record and pipeline.start payload.
    """
    prompt_hash = compute_sha256("plan|answer|refuse")
    tools_hash = compute_sha256("toolset")
    start_id = "00000000-0000-4000-8000-000000000001"
    tool_id = "00000000-0000-4000-8000-000000000002"
    gate_id = "00000000-0000-4000-8000-000000000003"
    done_id = "00000000-0000-4000-8000-000000000004"
    evidence_id = "00000000-0000-4000-8000-000000000005"
    started_at = "2026-05-28T12:00:00Z"
    finished_at = "2026-05-28T12:01:00Z"

    events: list[dict[str, object]] = [
        {
            "event_id": start_id,
            "type": "pipeline.start",
            "created_at": started_at,
            "actor": {"kind": "system", "id": "supplier-risk-rag-agent-evals"},
            "payload": {
                "suite": "refusal_cases",
                "prompt_snapshot_hash": prompt_hash,
                "tool_schemas_snapshot_hash": tools_hash,
            },
            "run_id": run_id,
        },
        {
            "event_id": tool_id,
            "type": "tool.call.completed",
            "created_at": started_at,
            "actor": {"kind": "system", "id": "supplier-risk-rag-agent-evals"},
            "payload": {"tool_name": "agent.answer+refusal.decision"},
            "run_id": run_id,
            "parent_event_id": start_id,
        },
        {
            "event_id": gate_id,
            "type": "gate.check.passed",
            "created_at": started_at,
            "actor": {"kind": "system", "id": "supplier-risk-rag-agent-evals"},
            "payload": {"gate_name": "refusal_precision_threshold"},
            "run_id": run_id,
            "parent_event_id": tool_id,
        },
        {
            "event_id": done_id,
            "type": "pipeline.done",
            "created_at": finished_at,
            "actor": {"kind": "system", "id": "supplier-risk-rag-agent-evals"},
            "payload": {
                "status": "done",
                "gate_results_summary": {
                    "gates_passed": ["refusal_precision_threshold"],
                    "gates_failed": [],
                    "all_passed": True,
                },
            },
            "run_id": run_id,
            "parent_event_id": gate_id,
        },
        {
            "event_id": evidence_id,
            "type": "gate.run.evidence_recorded",
            "created_at": finished_at,
            "actor": {"kind": "system", "id": "supplier-risk-rag-agent-evals"},
            "payload": {
                "run_id": run_id,
                "fields_populated": [
                    "gate_results_summary",
                    "prompt_snapshot_hash",
                    "sandbox_image_ref",
                    "tool_schemas_snapshot_hash",
                ],
            },
            "run_id": run_id,
            "parent_event_id": done_id,
        },
    ]

    run_record: dict[str, object] = {
        "id": run_id,
        "spec_id": "eval_suites/refusal_cases.yaml",
        "agent_id": "anthropic:claude-sonnet-4-6",
        "runtime": "supplier-risk-rag-agent-evals",
        "workspace_id": REPO_NAME,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": "done",
        "inputs": [
            {
                "kind": "eval_suite",
                "ref": (
                    f"repo://{REPO_NAME}@{'d' * 40}/"
                    "eval_suites/refusal_cases.yaml"
                ),
            }
        ],
        "outputs": [],
        "prompt_snapshot_hash": prompt_hash,
        "tool_schemas_snapshot_hash": tools_hash,
        "sandbox_image_ref": f"repo://{REPO_NAME}@{'d' * 40}/",
        "gate_results_summary": {
            "gates_passed": ["refusal_precision_threshold"],
            "gates_failed": [],
            "all_passed": True,
        },
    }
    return events, run_record


def _drive_validator(synthetic_root: Path) -> subprocess.CompletedProcess[str]:
    validator = synthetic_root / "scripts" / "validate_run_evidence.py"
    return subprocess.run(
        [sys.executable, str(validator)],
        cwd=str(synthetic_root),
        capture_output=True,
        text=True,
        check=False,
    )


# Import sys for the subprocess driver above. Kept local to the
# validator tests so the rest of the module's unit tests stay
# import-only.
import sys  # noqa: E402


def test_validator_passes_on_well_formed_pair(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair()
    _write_artifacts(tmp_path, "run-positive001", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 0, (
        f"validator unexpectedly failed: stderr={result.stderr!r}"
    )


def test_validator_fails_when_done_missing_required_field(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair("run-negative001")
    # Drop sandbox_image_ref on a done Run.
    del run["sandbox_image_ref"]
    # Keep the evidence event payload consistent with the new
    # populated-fields set so this test isolates the
    # required-for-done failure.
    for event in events:
        if event["type"] == "gate.run.evidence_recorded":
            event["payload"]["fields_populated"] = [
                "gate_results_summary",
                "prompt_snapshot_hash",
                "tool_schemas_snapshot_hash",
            ]
    _write_artifacts(tmp_path, "run-negative001", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 1
    assert "sandbox_image_ref" in result.stderr
    assert "status=done" in result.stderr


def test_validator_fails_on_prompt_hash_mismatch(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair("run-negative002")
    run["prompt_snapshot_hash"] = compute_sha256("a-different-prompt")
    _write_artifacts(tmp_path, "run-negative002", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 1
    assert "prompt_snapshot_hash mismatch" in result.stderr


def test_validator_fails_on_tool_schemas_hash_mismatch(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair("run-negative003")
    run["tool_schemas_snapshot_hash"] = compute_sha256("a-different-toolset")
    _write_artifacts(tmp_path, "run-negative003", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 1
    assert "tool_schemas_snapshot_hash mismatch" in result.stderr


def test_validator_fails_on_fields_populated_mismatch(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair("run-negative004")
    # Drop determinism + claim it in the evidence payload.
    for event in events:
        if event["type"] == "gate.run.evidence_recorded":
            event["payload"]["fields_populated"] = [
                "determinism",
                "gate_results_summary",
                "prompt_snapshot_hash",
                "sandbox_image_ref",
                "tool_schemas_snapshot_hash",
            ]
    _write_artifacts(tmp_path, "run-negative004", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 1
    assert "fields_populated" in result.stderr


def test_validator_fails_on_gate_summary_mismatch(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair("run-negative005")
    # Run says one gate passed; ledger event-stream is empty of
    # gate.check.* events.
    events = [e for e in events if e["type"] != "gate.check.passed"]
    _write_artifacts(tmp_path, "run-negative005", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 1
    assert "gate_results_summary mismatch" in result.stderr


def test_validator_fails_when_done_missing_evidence_event(tmp_path: Path) -> None:
    _seed_schemas_cache(tmp_path)
    events, run = _well_formed_pair("run-negative006")
    events = [e for e in events if e["type"] != "gate.run.evidence_recorded"]
    _write_artifacts(tmp_path, "run-negative006", events=events, run_record=run)
    result = _drive_validator(tmp_path)
    assert result.returncode == 1
    assert "no gate.run.evidence_recorded" in result.stderr


# End of unit tests. The runner integration tests live in
# tests/test_run_evidence_integration.py so this file stays
# import-only and never shells out.
