"""End-to-end runner -> ledger + Run record -> validator tests.

These tests drive ``src/evals/runner.py`` as a subprocess against the
checked-in sample corpus, redirect the ledger and record dirs into
``tmp_path`` via env vars, and verify the produced artifacts pass the
validator. Unit tests for the emitter helpers live in
``tests/test_run_evidence.py``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_suite(tmp_path: Path, suite: str) -> tuple[Path, Path]:
    """Drive the runner once; return ``(ledger_dir, records_dir)``."""
    ledger_dir = tmp_path / "event-ledger"
    records_dir = tmp_path / "run-records"
    env = os.environ.copy()
    env["SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"] = str(ledger_dir)
    env["SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"] = str(records_dir)
    result = subprocess.run(
        [sys.executable, "-m", "src.evals.runner", "--suite", suite],
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"runner failed for suite {suite}: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    return ledger_dir, records_dir


def test_runner_emits_record_and_ledger_for_one_suite(tmp_path: Path) -> None:
    ledger_dir, records_dir = _run_suite(tmp_path, "refusal_cases")

    ledger_files = sorted(ledger_dir.glob("*.jsonl"))
    record_files = sorted(records_dir.glob("*.json"))
    assert len(ledger_files) == 1, ledger_files
    assert len(record_files) == 1, record_files

    run_record = json.loads(record_files[0].read_text(encoding="utf-8"))
    assert run_record["runtime"] == "supplier-risk-rag-agent-evals"
    assert run_record["spec_id"] == "eval_suites/refusal_cases.yaml"
    assert "prompt_snapshot_hash" in run_record
    assert "tool_schemas_snapshot_hash" in run_record
    assert "sandbox_image_ref" in run_record
    assert "gate_results_summary" in run_record

    ledger_lines = ledger_files[0].read_text(encoding="utf-8").splitlines()
    event_types = [json.loads(line)["type"] for line in ledger_lines]
    assert "pipeline.start" in event_types
    assert "gate.run.evidence_recorded" in event_types
    assert any(t.startswith("gate.check.") for t in event_types)


def test_runner_no_emit_evidence_skips_emission(tmp_path: Path) -> None:
    """The --no-emit-evidence flag preserves the existing behavior.

    A reviewer running an ad-hoc eval pass should still be able to
    skip the ledger write. The flag is the documented opt-out per
    DEC-EVL-006.
    """
    ledger_dir = tmp_path / "event-ledger"
    records_dir = tmp_path / "run-records"
    env = os.environ.copy()
    env["SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"] = str(ledger_dir)
    env["SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"] = str(records_dir)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.evals.runner",
            "--suite",
            "refusal_cases",
            "--no-emit-evidence",
        ],
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not ledger_dir.exists() or not any(ledger_dir.glob("*.jsonl"))
    assert not records_dir.exists() or not any(records_dir.glob("*.json"))


def test_validate_run_evidence_accepts_runner_output(tmp_path: Path) -> None:
    """The validator script accepts the runner's output as conformant."""
    ledger_dir, records_dir = _run_suite(tmp_path, "refusal_cases")

    synthetic_root = tmp_path / "synth"
    synthetic_root.mkdir()
    (synthetic_root / "ops").mkdir()
    shutil.copytree(
        ROOT / "ops" / "schemas-cache", synthetic_root / "ops" / "schemas-cache"
    )
    shutil.copytree(ledger_dir, synthetic_root / "ops" / "event-ledger")
    shutil.copytree(records_dir, synthetic_root / "ops" / "run-records")
    shutil.copytree(ROOT / "scripts", synthetic_root / "scripts")

    validator_path = synthetic_root / "scripts" / "validate_run_evidence.py"
    validate_result = subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=str(synthetic_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate_result.returncode == 0, (
        f"validator failed: stdout={validate_result.stdout!r} "
        f"stderr={validate_result.stderr!r}"
    )
