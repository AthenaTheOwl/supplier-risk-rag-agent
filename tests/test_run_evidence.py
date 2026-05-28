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
    aggregate_gate_results,
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
        "workspace_id": str(ROOT.as_posix()),
        "started_at": "2026-05-27T20:00:00Z",
        "finished_at": "2026-05-27T20:01:00Z",
        "status": "done",
        "inputs": [{"kind": "eval_suite", "ref": "eval_suites/refusal_cases.yaml"}],
        "outputs": [],
        "prompt_snapshot_hash": compute_sha256("plan|answer|refuse"),
        "tool_schemas_snapshot_hash": compute_sha256("toolset"),
        "sandbox_image_ref": f"{ROOT.as_posix()}@deadbeefcafe",
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


def test_derive_sandbox_image_ref_includes_head_sha_for_real_repo(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "evals@test.local"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "evals-test"],
        capture_output=True,
        check=True,
    )
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"], capture_output=True, check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "seed"],
        capture_output=True,
        check=True,
    )
    ref = derive_sandbox_image_ref(repo)
    assert ref is not None
    assert ref.startswith(repo.as_posix() + "@")
    assert re.match(r".+@[0-9a-f]{40}$", ref)


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


# End of unit tests. The runner integration tests live in
# tests/test_run_evidence_integration.py so this file stays
# import-only and never shells out.
