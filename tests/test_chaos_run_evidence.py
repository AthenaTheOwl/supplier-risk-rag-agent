"""Chaos test suite for ``scripts/validate_run_evidence.py``.

The validator carries three layers of enforcement against an emitted
Run record + event ledger pair: typed event payload validation via the
``oneOf`` discriminator in the cached ``event.schema.json``, four
cross-checks tying the Run record back to the matching ledger, and a
required-for-done block that rejects a done Run missing any of the
four replay-equivalence fields plus the terminal evidence event.

A silent regression in any of those rules would cost the run-evidence
chain its contract value: the validator would still exit zero on a
corrupt sample and downstream consumers would treat the mutation as
ground truth. The chaos suite below installs the closing-pass
discipline check the rest of the chain depends on. Each test copies
the canonical sample (``run-643dff8f3b9c``) into a synthetic root,
applies one mutation class, and asserts the validator exits non-zero
with an error message naming the broken rule.

Seven mutation classes cover the validator's three layers:

- M1 prompt_snapshot_hash drift on the Run (cross-check 1).
- M2 tool_schemas_snapshot_hash drift on the Run (cross-check 2).
- M3 phantom gate name added to gates_passed (cross-check 4).
- M4 terminal gate.run.evidence_recorded event removed (required-event
  check on done Runs).
- M5 prompt_snapshot_hash dropped from the pipeline.start payload
  (typed-event-payload validation via the schema's oneOf
  discriminator).
- M6 gate.run.evidence_recorded.payload.fields_populated claims a
  field absent on the Run (cross-check 3).
- M7 Run.status == "done" but sandbox_image_ref removed
  (required-for-done block).

If the validator exits 0 against any mutation the suite fails loudly
because that signals a real validator gap, not a flaky test. Each
test also peeks at the validator's stderr to confirm the message names
the broken rule so a future regression that drops the diagnostic
string also turns the gate red.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN_ID = "run-643dff8f3b9c"
CANONICAL_RUN_RECORD = (
    ROOT / "ops" / "run-records" / f"{CANONICAL_RUN_ID}.json"
)
CANONICAL_LEDGER = (
    ROOT / "ops" / "event-ledger" / f"{CANONICAL_RUN_ID}.jsonl"
)


def _build_synthetic_root(tmp_path: Path) -> Path:
    """Copy the canonical sample + schema cache + scripts into ``tmp_path``.

    The validator resolves paths relative to its own location, so the
    test ships a synthetic root carrying the same on-disk shape as the
    repo. The canonical sample at ``ops/`` is left untouched on disk;
    every mutation lands inside ``tmp_path``.
    """
    synthetic_root = tmp_path / "synth"
    (synthetic_root / "ops").mkdir(parents=True)
    shutil.copytree(
        ROOT / "ops" / "schemas-cache",
        synthetic_root / "ops" / "schemas-cache",
    )
    (synthetic_root / "ops" / "event-ledger").mkdir()
    (synthetic_root / "ops" / "run-records").mkdir()
    shutil.copy2(
        CANONICAL_RUN_RECORD,
        synthetic_root / "ops" / "run-records" / f"{CANONICAL_RUN_ID}.json",
    )
    shutil.copy2(
        CANONICAL_LEDGER,
        synthetic_root / "ops" / "event-ledger" / f"{CANONICAL_RUN_ID}.jsonl",
    )
    shutil.copytree(ROOT / "scripts", synthetic_root / "scripts")
    return synthetic_root


def _run_record_path(synthetic_root: Path) -> Path:
    return synthetic_root / "ops" / "run-records" / f"{CANONICAL_RUN_ID}.json"


def _ledger_path(synthetic_root: Path) -> Path:
    return synthetic_root / "ops" / "event-ledger" / f"{CANONICAL_RUN_ID}.jsonl"


def _load_run(synthetic_root: Path) -> dict[str, Any]:
    return json.loads(_run_record_path(synthetic_root).read_text(encoding="utf-8"))


def _write_run(synthetic_root: Path, run: dict[str, Any]) -> None:
    _run_record_path(synthetic_root).write_text(
        json.dumps(run, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _load_ledger(synthetic_root: Path) -> list[dict[str, Any]]:
    text = _ledger_path(synthetic_root).read_text(encoding="utf-8")
    return [
        json.loads(line) for line in text.splitlines() if line.strip()
    ]


def _write_ledger(synthetic_root: Path, events: list[dict[str, Any]]) -> None:
    lines = [json.dumps(event, sort_keys=True) for event in events]
    _ledger_path(synthetic_root).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _run_validator(synthetic_root: Path) -> subprocess.CompletedProcess[str]:
    validator = synthetic_root / "scripts" / "validate_run_evidence.py"
    return subprocess.run(
        [sys.executable, str(validator)],
        cwd=str(synthetic_root),
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_validator_rejects(
    result: subprocess.CompletedProcess[str],
    expected_message_fragment: str,
    mutation_label: str,
) -> None:
    """Assert the validator exited non-zero and stderr names the broken rule."""
    assert result.returncode != 0, (
        f"{mutation_label}: validator returned exit code 0 against a "
        f"mutated sample. This is a real validator gap. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert expected_message_fragment in result.stderr, (
        f"{mutation_label}: validator exited non-zero but the stderr "
        f"did not name the broken rule. Looked for "
        f"{expected_message_fragment!r}. "
        f"stderr={result.stderr!r}"
    )


def _baseline_passes(tmp_path: Path) -> None:
    """Sanity check: the untouched canonical sample passes the validator.

    Run as a quick guard against test-environment drift. A baseline
    failure would mask every mutation test below behind the same
    error, so the suite catches it first.
    """
    synthetic_root = _build_synthetic_root(tmp_path)
    result = _run_validator(synthetic_root)
    assert result.returncode == 0, (
        f"baseline canonical sample failed the validator. The chaos "
        f"suite cannot run meaningfully without a clean baseline. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_baseline_canonical_sample_passes(tmp_path: Path) -> None:
    """The unmutated canonical sample MUST pass the validator."""
    _baseline_passes(tmp_path)


# ---------------------------------------------------------------------------
# M1: mutate Run.prompt_snapshot_hash to a different valid-shaped hash.
# Cross-check 1 in scripts/validate_run_evidence.py should fail because
# the Run record's hash no longer matches the pipeline.start event's
# payload hash.
# ---------------------------------------------------------------------------
def test_m1_run_prompt_snapshot_hash_drift_caught(tmp_path: Path) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    run = _load_run(synthetic_root)
    original = run["prompt_snapshot_hash"]
    # Same shape (64 hex chars), different bytes. Swap the first char
    # for a different hex digit and keep the rest. The mutation must
    # still satisfy the schema's sha256-hex pattern so the failure
    # surfaces as a cross-check, not a schema error.
    swap = "f" if original[0] != "f" else "0"
    run["prompt_snapshot_hash"] = swap + original[1:]
    _write_run(synthetic_root, run)

    result = _run_validator(synthetic_root)
    _assert_validator_rejects(
        result, "prompt_snapshot_hash mismatch", "M1"
    )


# ---------------------------------------------------------------------------
# M2: mutate Run.tool_schemas_snapshot_hash to a different hash.
# Cross-check 2 should fail.
# ---------------------------------------------------------------------------
def test_m2_run_tool_schemas_snapshot_hash_drift_caught(
    tmp_path: Path,
) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    run = _load_run(synthetic_root)
    original = run["tool_schemas_snapshot_hash"]
    swap = "f" if original[0] != "f" else "0"
    run["tool_schemas_snapshot_hash"] = swap + original[1:]
    _write_run(synthetic_root, run)

    result = _run_validator(synthetic_root)
    _assert_validator_rejects(
        result, "tool_schemas_snapshot_hash mismatch", "M2"
    )


# ---------------------------------------------------------------------------
# M3: mutate Run.gate_results_summary.gates_passed to add a phantom
# gate name no gate.check.passed event fired. Cross-check 4 should
# fail because the Run-side rollup no longer matches the ledger-side
# aggregation.
# ---------------------------------------------------------------------------
def test_m3_run_gate_results_summary_phantom_gate_caught(
    tmp_path: Path,
) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    run = _load_run(synthetic_root)
    summary = run["gate_results_summary"]
    summary["gates_passed"] = sorted(
        list(summary.get("gates_passed", [])) + ["phantom_gate_does_not_exist"]
    )
    run["gate_results_summary"] = summary
    _write_run(synthetic_root, run)

    result = _run_validator(synthetic_root)
    _assert_validator_rejects(
        result, "gate_results_summary mismatch", "M3"
    )


# ---------------------------------------------------------------------------
# M4: remove the terminal gate.run.evidence_recorded event from the
# ledger. The required-event check for a done Run should fail.
# ---------------------------------------------------------------------------
def test_m4_missing_evidence_recorded_event_caught(tmp_path: Path) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    events = _load_ledger(synthetic_root)
    filtered = [
        e for e in events if e.get("type") != "gate.run.evidence_recorded"
    ]
    assert len(filtered) < len(events), (
        "M4 setup: canonical sample did not carry a "
        "gate.run.evidence_recorded event; cannot exercise the "
        "required-event branch"
    )
    _write_ledger(synthetic_root, filtered)

    result = _run_validator(synthetic_root)
    _assert_validator_rejects(
        result,
        "no gate.run.evidence_recorded event in the ledger",
        "M4",
    )


# ---------------------------------------------------------------------------
# M5: drop prompt_snapshot_hash from the pipeline.start event's
# payload. The cached event.schema.json declares
# prompt_snapshot_hash + tool_schemas_snapshot_hash as required on the
# pipeline.start branch of the oneOf discriminator, so the typed event
# payload validation should fail.
# ---------------------------------------------------------------------------
def test_m5_pipeline_start_missing_prompt_hash_caught(tmp_path: Path) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    events = _load_ledger(synthetic_root)
    mutated: list[dict[str, Any]] = []
    found_start = False
    for event in events:
        if event.get("type") == "pipeline.start":
            payload = dict(event.get("payload") or {})
            payload.pop("prompt_snapshot_hash", None)
            event = {**event, "payload": payload}
            found_start = True
        mutated.append(event)
    assert found_start, (
        "M5 setup: canonical sample did not carry a pipeline.start "
        "event; cannot exercise the typed payload validation branch"
    )
    _write_ledger(synthetic_root, mutated)

    result = _run_validator(synthetic_root)
    # The schema-level violation surfaces as a top-level oneOf
    # mismatch ("is not valid under any of the given schemas") on the
    # event whose pipeline.start payload no longer satisfies the
    # required-key contract. The bare oneOf message does not name the
    # missing key (jsonschema's oneOf reporting collapses every branch
    # mismatch into one envelope error) so the assertion looks for the
    # envelope phrase plus the event type that should have matched.
    assert result.returncode != 0, (
        f"M5: validator returned exit code 0 against a pipeline.start "
        f"event missing prompt_snapshot_hash. Validator gap. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "is not valid under any of the given schemas" in result.stderr, (
        f"M5: validator exited non-zero but stderr did not name "
        f"the oneOf rejection. stderr={result.stderr!r}"
    )
    assert "pipeline.start" in result.stderr, (
        f"M5: validator exited non-zero but stderr did not surface "
        f"the offending event type. stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# M6: mutate the gate.run.evidence_recorded.payload.fields_populated
# list to claim a replay-equivalence field the Run does NOT carry
# (e.g. ``determinism``, which the canonical sample does not populate).
# Cross-check 3 should fail because the declared set no longer matches
# the actually-populated set on the Run.
# ---------------------------------------------------------------------------
def test_m6_fields_populated_claims_absent_field_caught(
    tmp_path: Path,
) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    run = _load_run(synthetic_root)
    # Pick a replay-equivalence field that is NOT populated on the
    # canonical Run record. ``determinism`` and ``checkpoint_ref`` are
    # the two the canonical sample omits per the design.md notes.
    candidate = "determinism"
    assert candidate not in run or not run[candidate], (
        f"M6 setup: canonical sample carried {candidate!r} populated; "
        f"pick a different absent field to keep the mutation distinct "
        f"from the populated set."
    )

    events = _load_ledger(synthetic_root)
    mutated: list[dict[str, Any]] = []
    found_evidence = False
    for event in events:
        if event.get("type") == "gate.run.evidence_recorded":
            payload = dict(event.get("payload") or {})
            declared = list(payload.get("fields_populated") or [])
            declared = sorted(set(declared) | {candidate})
            payload["fields_populated"] = declared
            event = {**event, "payload": payload}
            found_evidence = True
        mutated.append(event)
    assert found_evidence, (
        "M6 setup: canonical sample did not carry a "
        "gate.run.evidence_recorded event; cannot exercise "
        "cross-check 3"
    )
    _write_ledger(synthetic_root, mutated)

    result = _run_validator(synthetic_root)
    _assert_validator_rejects(
        result,
        "does not match replay-equivalence fields populated on Run",
        "M6",
    )


# ---------------------------------------------------------------------------
# M7: keep Run.status == "done" but remove sandbox_image_ref. The
# required-for-done block in the validator should fail because
# sandbox_image_ref is one of the four required-for-done fields.
# ---------------------------------------------------------------------------
def test_m7_done_run_missing_sandbox_image_ref_caught(
    tmp_path: Path,
) -> None:
    synthetic_root = _build_synthetic_root(tmp_path)
    run = _load_run(synthetic_root)
    assert run.get("status") == "done", (
        "M7 setup: canonical sample is not status=done; the "
        "required-for-done branch cannot fire"
    )
    run.pop("sandbox_image_ref", None)
    _write_run(synthetic_root, run)

    result = _run_validator(synthetic_root)
    # Either the schema's required-property branch surfaces the
    # missing key first, or the cross-check block names the field.
    # Both paths satisfy the contract; both name the field by name.
    assert result.returncode != 0, (
        f"M7: validator returned exit code 0 against a done Run "
        f"missing sandbox_image_ref. Validator gap. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "sandbox_image_ref" in result.stderr, (
        f"M7: validator exited non-zero but stderr did not name "
        f"sandbox_image_ref. stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Suite-level guard: count the mutations exercised. A future drop in
# coverage trips the guard so a reviewer cannot accidentally land a
# regression that quietly shrinks the chaos surface.
# ---------------------------------------------------------------------------
EXPECTED_MUTATION_TESTS = (
    "test_m1_run_prompt_snapshot_hash_drift_caught",
    "test_m2_run_tool_schemas_snapshot_hash_drift_caught",
    "test_m3_run_gate_results_summary_phantom_gate_caught",
    "test_m4_missing_evidence_recorded_event_caught",
    "test_m5_pipeline_start_missing_prompt_hash_caught",
    "test_m6_fields_populated_claims_absent_field_caught",
    "test_m7_done_run_missing_sandbox_image_ref_caught",
)


def test_chaos_suite_covers_seven_mutation_classes() -> None:
    """The suite covers all seven mutation classes named in DEC-EVL-013."""
    module = sys.modules[__name__]
    present = {
        name for name in EXPECTED_MUTATION_TESTS if hasattr(module, name)
    }
    assert present == set(EXPECTED_MUTATION_TESTS), (
        f"missing mutation tests: "
        f"{set(EXPECTED_MUTATION_TESTS) - present}"
    )
    assert len(EXPECTED_MUTATION_TESTS) == 7
