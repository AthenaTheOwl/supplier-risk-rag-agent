"""Tests for ``scripts/replay_run.py``.

These tests redirect the canonical ops dirs into ``tmp_path`` via the
``SUPPLIER_RISK_RAG_*_DIR`` env vars the replay script honors. That
keeps the test artifacts off the checked-in tree while still letting
the script resolve ``git rev-parse HEAD`` against the real repo (so
the HEAD-strict pre-flight matches a freshly generated sample).

Positive path: generate a sample at the current HEAD, replay, assert
equivalent. Three negative paths drive the documented failure modes:

- HEAD mismatch: mutate ``sandbox_image_ref`` to a fake SHA.
- Missing Run record: pass a run_id that does not match any file.
- Prompt drift: mutate ``prompt_snapshot_hash`` so the recorded value
  no longer matches what the fresh re-run computes.
- Rubric drift: mutate ``gate_results_summary`` so the recorded
  rollup no longer matches what the fresh re-run computes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPLAY_SCRIPT = ROOT / "scripts" / "replay_run.py"
FINALIZE_SCRIPT = ROOT / "scripts" / "finalize_sandbox_ref.py"


def _finalize_sandbox_ref(run_id: str, env: dict[str, str], sha: str) -> None:
    """Drive ``scripts/finalize_sandbox_ref.py`` against a fresh sample.

    The emitter writes ``sandbox_image_ref`` with a ``PENDING``
    placeholder per the two-pass pattern from Round 6 (DEC-EVL-009).
    The replay command is HEAD-strict, so the test must finalize the
    placeholder to the current HEAD SHA before invoking replay.
    """
    result = subprocess.run(  # noqa: S603 - args fixed, no shell
        [
            sys.executable,
            str(FINALIZE_SCRIPT),
            "--run-id",
            run_id,
            "--sha",
            sha,
        ],
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        f"finalize_sandbox_ref failed: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )


# --------------------------------------------------------------------- helpers


def _git_head_sha() -> str:
    result = subprocess.run(  # noqa: S603 - args fixed, no shell
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    sha = result.stdout.strip()
    if result.returncode != 0 or not sha:
        pytest.skip("replay tests require a git working tree at the repo root")
    return sha


def _redirected_env(
    records_dir: Path,
    ledger_dir: Path,
    replay_dir: Path,
) -> dict[str, str]:
    """Return an env mapping that redirects the three ops dirs.

    Same env-var names the runner already honors plus the new
    ``SUPPLIER_RISK_RAG_REPLAY_RECORDS_DIR`` knob the replay script
    introduced. The replay-run subprocess forwards these into its
    own nested runner subprocess, so a single redirection covers
    both the script's writes and the inner re-run's writes.
    """
    env = os.environ.copy()
    env["SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"] = str(records_dir)
    env["SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"] = str(ledger_dir)
    env["SUPPLIER_RISK_RAG_REPLAY_RECORDS_DIR"] = str(replay_dir)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _generate_sample(env: dict[str, str]) -> tuple[str, Path, Path]:
    """Run the eval runner once with the redirected env; return paths.

    The runner writes its Run record + ledger into the ops dirs the
    env vars point at. We discover the freshly emitted files there
    so the test can identify the new run_id.
    """
    records_dir = Path(env["SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"])
    ledger_dir = Path(env["SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"])
    records_dir.mkdir(parents=True, exist_ok=True)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    pre_records = set(records_dir.glob("*.json"))
    pre_ledgers = set(ledger_dir.glob("*.jsonl"))

    result = subprocess.run(  # noqa: S603 - args fixed, no shell
        [sys.executable, "-m", "src.evals.runner", "--suite", "refusal_cases"],
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        f"sample generation failed: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    new_records = sorted(set(records_dir.glob("*.json")) - pre_records)
    new_ledgers = sorted(set(ledger_dir.glob("*.jsonl")) - pre_ledgers)
    assert len(new_records) == 1, new_records
    assert len(new_ledgers) == 1, new_ledgers
    run_id = new_records[0].stem
    return run_id, new_records[0], new_ledgers[0]


def _invoke_replay(
    run_id: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the replay script as a subprocess against the redirected ops dirs."""
    return subprocess.run(  # noqa: S603 - args fixed, no shell
        [sys.executable, str(REPLAY_SCRIPT), "--run-id", run_id],
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def _redirected_layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    records_dir = tmp_path / "ops" / "run-records"
    ledger_dir = tmp_path / "ops" / "event-ledger"
    replay_dir = tmp_path / "ops" / "replay-records"
    records_dir.mkdir(parents=True, exist_ok=True)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)
    return records_dir, ledger_dir, replay_dir


# --------------------------------------------------------------------- positive


def test_replay_equivalent_against_freshly_generated_sample(tmp_path: Path) -> None:
    """The full positive path: fresh sample -> replay -> equivalent.

    Generating the sample at the current HEAD guarantees the
    HEAD-strict pre-flight passes without checking out a different
    SHA. The replay must report equivalent on all three signals and
    exit zero, and must write a ``run.evidence.replayed`` event into
    a per-replay ledger plus a detailed comparison report under
    ``ops/replay-records/<run-id>/``.
    """
    head = _git_head_sha()
    records_dir, ledger_dir, replay_dir = _redirected_layout(tmp_path)
    env = _redirected_env(records_dir, ledger_dir, replay_dir)

    run_id, record_path, _ledger_path = _generate_sample(env)
    staged = json.loads(record_path.read_text(encoding="utf-8"))
    assert staged["sandbox_image_ref"].endswith("@PENDING/"), staged[
        "sandbox_image_ref"
    ]
    _finalize_sandbox_ref(run_id, env, head)
    staged = json.loads(record_path.read_text(encoding="utf-8"))
    assert staged["sandbox_image_ref"] == (
        f"repo://supplier-risk-rag-agent@{head}/"
    ), staged["sandbox_image_ref"]

    result = _invoke_replay(run_id, env)
    assert result.returncode == 0, (
        f"replay failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "equivalent" in result.stdout

    replay_ledgers = sorted(ledger_dir.glob(f"replay-{run_id}-*.jsonl"))
    assert len(replay_ledgers) == 1, replay_ledgers
    reports = sorted((replay_dir / run_id).glob("*.json"))
    assert len(reports) == 1, reports

    event = json.loads(replay_ledgers[0].read_text(encoding="utf-8").strip())
    assert event["type"] == "run.evidence.replayed"
    assert event["payload"]["replay_equivalent"] is True
    assert event["payload"]["replay_method"] == "equivalence"
    assert event["payload"]["run_id"] == run_id

    report = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report["replay_equivalent"] is True
    assert report["replay_method"] == "equivalence"
    assert report["source_run_id"] == run_id
    for key in (
        "prompt_snapshot_hash",
        "tool_schemas_snapshot_hash",
        "gate_results_summary",
    ):
        assert report["comparison"][key]["match"] is True


def test_replay_treats_pending_sandbox_ref_as_implicit_head(
    tmp_path: Path,
) -> None:
    """A PENDING placeholder ref auto-resolves to current HEAD on replay.

    The two-pass emission pattern from DEC-EVL-009 lands the Run
    record with a ``repo://supplier-risk-rag-agent@PENDING/``
    sentinel before ``scripts/finalize_sandbox_ref.py`` rewrites
    the SHA. Replay must tolerate the placeholder so an operator
    can verify a freshly regenerated sample against the same
    commit without an intervening finalize step.
    """
    records_dir, ledger_dir, replay_dir = _redirected_layout(tmp_path)
    env = _redirected_env(records_dir, ledger_dir, replay_dir)
    run_id, record_path, _ = _generate_sample(env)

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["sandbox_image_ref"].endswith("@PENDING/")

    result = _invoke_replay(run_id, env)
    assert result.returncode == 0, (
        f"replay should accept PENDING sentinel: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "equivalent" in result.stdout


# --------------------------------------------------------------------- negative


def test_replay_head_mismatch_exits_one_with_checkout_hint(
    tmp_path: Path,
) -> None:
    """HEAD != recorded sandbox SHA exits 1 with a ``git checkout`` hint."""
    records_dir, ledger_dir, replay_dir = _redirected_layout(tmp_path)
    env = _redirected_env(records_dir, ledger_dir, replay_dir)
    run_id, record_path, _ = _generate_sample(env)

    # Rewrite sandbox_image_ref to encode a SHA the working tree will
    # never match. The fake SHA is a syntactically valid 40-char hex
    # string so the parsing path stays on the happy line and the
    # check fires on the comparison itself. Uses the new portable
    # repo:// URI shape from DEC-CDCP-014.
    fake_sha = "0" * 40
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["sandbox_image_ref"] = f"repo://supplier-risk-rag-agent@{fake_sha}/"
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    result = _invoke_replay(run_id, env)
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "HEAD mismatch" in combined
    assert "git checkout" in combined
    assert fake_sha in combined


def test_replay_missing_run_record_exits_one(tmp_path: Path) -> None:
    """A run_id with no Run record file exits 1 with a clear message."""
    records_dir, ledger_dir, replay_dir = _redirected_layout(tmp_path)
    env = _redirected_env(records_dir, ledger_dir, replay_dir)
    result = _invoke_replay("run-doesnotexist", env)
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "Run record not found" in combined
    assert "run-doesnotexist" in combined


def test_replay_detects_prompt_drift(tmp_path: Path) -> None:
    """A mutated ``prompt_snapshot_hash`` on the Run trips divergence.

    Editing the recorded hash so it disagrees with what the fresh
    re-run computes means the comparison must report divergence and
    exit 1, naming the diverging signal in the printed summary plus
    in the written report.
    """
    head = _git_head_sha()
    records_dir, ledger_dir, replay_dir = _redirected_layout(tmp_path)
    env = _redirected_env(records_dir, ledger_dir, replay_dir)
    run_id, record_path, _ = _generate_sample(env)
    _finalize_sandbox_ref(run_id, env, head)

    record = json.loads(record_path.read_text(encoding="utf-8"))
    original = record["prompt_snapshot_hash"]
    # Flip one hex character so the value stays schema-valid
    # (^[a-f0-9]{64}$) but no longer matches the fresh hash.
    mutated = ("a" if original[0] != "a" else "b") + original[1:]
    record["prompt_snapshot_hash"] = mutated
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    result = _invoke_replay(run_id, env)
    assert result.returncode == 1
    assert "DIVERGENT" in result.stdout
    assert "prompt_snapshot_hash: MISMATCH" in result.stdout

    reports = sorted((replay_dir / run_id).glob("*.json"))
    assert len(reports) == 1, reports
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report["replay_equivalent"] is False
    assert report["comparison"]["prompt_snapshot_hash"]["match"] is False


def test_replay_detects_gate_rollup_drift(tmp_path: Path) -> None:
    """A mutated ``gate_results_summary`` on the Run trips divergence.

    Moving the passed gate into the failed list on the recorded Run
    means the fresh re-run's rollup (still a pass) no longer matches.
    The script must report the divergence and exit 1, calling out
    the gate-rollup signal specifically.
    """
    head = _git_head_sha()
    records_dir, ledger_dir, replay_dir = _redirected_layout(tmp_path)
    env = _redirected_env(records_dir, ledger_dir, replay_dir)
    run_id, record_path, _ = _generate_sample(env)
    _finalize_sandbox_ref(run_id, env, head)

    record = json.loads(record_path.read_text(encoding="utf-8"))
    summary = record["gate_results_summary"]
    passed = list(summary.get("gates_passed", []))
    summary["gates_failed"] = passed
    summary["gates_passed"] = []
    summary["all_passed"] = False
    record["gate_results_summary"] = summary
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    result = _invoke_replay(run_id, env)
    assert result.returncode == 1
    assert "gate_results_summary: MISMATCH" in result.stdout

    reports = sorted((replay_dir / run_id).glob("*.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report["comparison"]["gate_results_summary"]["match"] is False
