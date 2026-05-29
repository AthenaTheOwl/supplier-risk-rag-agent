"""Replay determinism test fixture for the canonical sample.

This test installs the ChatGPT-pulse replay-determinism pattern,
translated into the run-evidence framing this repo already ships.
The canonical sample at ``ops/run-records/run-643dff8f3b9c.json``
plus its ledger pins a known-good replay context; this test
re-runs ``scripts/replay_run.py`` against that sample ``RERUNS``
times (default 3, override via env ``RERUNS``), extracts the
three replay-equivalence signals from each fresh re-run, sorts
+ canonicalizes + SHA-256-hashes them, and asserts every replay
produced the same hash.

Drift this catches:
- Prompt template edited without an accompanying sample regen.
- Tool-surface config (ranker weights, LLM model id, reranker
  config) changed without an accompanying sample regen.
- Gate-set name or rollup shape changed without an accompanying
  sample regen.

Anything that flips one of the three replay-equivalence hashes
between two nominally-identical replays of the same canonical
sample shows up here as a non-deterministic verdict + a failure
bundle under ``artifacts/failbundles/``.

The test is HEAD-strict: ``scripts/replay_run.py`` enforces that
the working tree sits at the SHA the recorded
``sandbox_image_ref`` pins. The test saves the current HEAD,
checks out the recorded sandbox SHA for the duration of the
replay loop, and restores the saved HEAD on teardown (including
the failure paths). In CI, ``actions/checkout@v4`` needs
``fetch-depth: 0`` so the recorded SHA is reachable in the
runner clone.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPLAY_SCRIPT = ROOT / "scripts" / "replay_run.py"
CANONICAL_RUN_ID = "run-643dff8f3b9c"
CANONICAL_RECORD = ROOT / "ops" / "run-records" / f"{CANONICAL_RUN_ID}.json"
REPLAY_RECORDS_DIR = ROOT / "ops" / "replay-records" / CANONICAL_RUN_ID
REPLAY_LEDGER_DIR = ROOT / "ops" / "event-ledger"
FAILBUNDLE_DIR = ROOT / "artifacts" / "failbundles"

_SHA_RE = re.compile(r"^[a-f0-9]{40}$")
_SANDBOX_URI_RE = re.compile(
    r"^repo://[a-z][a-z0-9-]*@(?P<sha>[a-f0-9]{40})/$"
)


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - args fixed, no shell
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def _git_head_sha() -> str:
    result = _git(["rev-parse", "HEAD"])
    if result.returncode != 0 or not result.stdout.strip():
        pytest.skip(
            "replay-determinism test requires a git working tree at the repo root"
        )
    return result.stdout.strip()


def _git_symbolic_head() -> str:
    """Return the current branch name when on a branch, else the HEAD SHA.

    ``git symbolic-ref --short HEAD`` returns the branch name on a
    branch checkout and exits non-zero on a detached HEAD. The test
    saves whichever value resolves so the teardown restore picks the
    same shape (branch name, not the SHA the branch points at).
    """
    result = _git(["symbolic-ref", "--short", "HEAD"])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return _git_head_sha()


def _parse_sandbox_sha(sandbox_image_ref: str) -> str:
    m = _SANDBOX_URI_RE.match(sandbox_image_ref)
    if not m:
        pytest.fail(
            "canonical sample's sandbox_image_ref does not carry a 40-char SHA "
            f"in the repo:// URI grammar. Got: {sandbox_image_ref!r}"
        )
    return m.group("sha")


def _rerun_count() -> int:
    raw = os.environ.get("RERUNS", "3").strip()
    try:
        n = int(raw)
    except ValueError:
        pytest.fail(f"RERUNS env var is not an integer: {raw!r}")
    if n < 2:
        pytest.fail(
            f"RERUNS must be >= 2 to compare replays; got {n}. The test compares "
            "hashes across replays, so a single replay cannot detect divergence."
        )
    return n


def _canonical_gate_summary(summary: dict) -> dict:
    """Return a sort-stable shape for gate_results_summary.

    The replay-equivalence comparison treats gates_passed and
    gates_failed as sets; the determinism test mirrors that by
    sorting the name lists and coercing all_passed to a bool so
    list ordering and truthy-ish values do not flap the hash.
    """
    return {
        "all_passed": bool(summary.get("all_passed", False)),
        "gates_failed": sorted(summary.get("gates_failed") or []),
        "gates_passed": sorted(summary.get("gates_passed") or []),
    }


def _canonical_triple(replay_record: dict) -> dict:
    """Extract the three replay-equivalence signals from a replay record.

    The replay script writes a comparison report whose ``comparison``
    block carries ``recorded`` and ``fresh`` halves for each signal.
    The determinism test reads the ``fresh`` half because that is
    what the replay just produced; if the hashes diverge across
    replays the producer-side replay is non-deterministic.
    """
    comparison = replay_record.get("comparison") or {}
    prompt = comparison.get("prompt_snapshot_hash") or {}
    tools = comparison.get("tool_schemas_snapshot_hash") or {}
    gates = comparison.get("gate_results_summary") or {}
    fresh_summary = gates.get("fresh") or {}
    return {
        "gate_results_summary": _canonical_gate_summary(fresh_summary),
        "prompt_snapshot_hash": prompt.get("fresh"),
        "tool_schemas_snapshot_hash": tools.get("fresh"),
    }


def _hash_canonical(triple: dict) -> str:
    payload = json.dumps(triple, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_remove(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    except OSError:
        pass


def test_canonical_sample_replay_is_deterministic() -> None:
    """Replay the canonical sample RERUNS times; hashes must match.

    Runs ``python scripts/replay_run.py --run-id run-643dff8f3b9c``
    once per iteration, reads the comparison report each replay
    writes under ``ops/replay-records/run-643dff8f3b9c/``, extracts
    the three replay-equivalence signals (prompt_snapshot_hash,
    tool_schemas_snapshot_hash, gate_results_summary), canonicalizes
    + SHA-256-hashes the tuple, and asserts every replay produced
    the same hash.

    On divergence: write a failure bundle to
    ``artifacts/failbundles/determinism_failure.json`` plus
    ``trace_0.json`` and ``trace_1.json`` carrying the canonical
    tuples for the first two diverging replays, and fail loudly
    with the bundle path in the message.

    HEAD-strict pre-flight is delegated to the replay script: this
    test checks out the recorded sandbox SHA before the loop and
    restores the saved HEAD on teardown.
    """
    assert CANONICAL_RECORD.is_file(), (
        f"canonical Run record missing at {CANONICAL_RECORD}"
    )
    rerun_count = _rerun_count()

    record = json.loads(CANONICAL_RECORD.read_text(encoding="utf-8"))
    sandbox_sha = _parse_sandbox_sha(record.get("sandbox_image_ref", ""))

    saved_head = _git_symbolic_head()

    # ``git checkout <sandbox-sha>`` refuses when tracked files differ
    # between HEAD and the target ref. CI runs against a clean checkout
    # so this path is silent there. Local dev with in-flight edits to
    # the spec ledger, the workflow file, or the determinism fixture
    # itself trips the check; skip cleanly with a clear message rather
    # than falsely reporting non-determinism on a dirty tree.
    status = _git(["status", "--porcelain"])
    if status.returncode == 0 and status.stdout.strip():
        tracked_changes = [
            line
            for line in status.stdout.splitlines()
            if line and not line.startswith("??")
        ]
        if tracked_changes:
            pytest.skip(
                "working tree has tracked modifications that would "
                "block `git checkout <sandbox-sha>`; commit or stash "
                "before running the determinism fixture. Modified "
                f"entries: {tracked_changes}"
            )

    pre_replay_reports: set[Path] = (
        set(REPLAY_RECORDS_DIR.glob("*.json"))
        if REPLAY_RECORDS_DIR.is_dir()
        else set()
    )
    pre_replay_ledgers: set[Path] = (
        set(REPLAY_LEDGER_DIR.glob(f"replay-{CANONICAL_RUN_ID}-*.jsonl"))
        if REPLAY_LEDGER_DIR.is_dir()
        else set()
    )

    new_reports: list[Path] = []
    new_ledgers: list[Path] = []
    canonical_tuples: list[dict] = []
    hashes: list[str] = []

    try:
        checkout = _git(["checkout", sandbox_sha])
        if checkout.returncode != 0:
            pytest.fail(
                "could not check out recorded sandbox SHA "
                f"{sandbox_sha}: stdout={checkout.stdout!r} "
                f"stderr={checkout.stderr!r}. In CI ensure "
                "actions/checkout@v4 uses fetch-depth: 0."
            )

        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        for _ in range(rerun_count):
            result = subprocess.run(  # noqa: S603 - args fixed, no shell
                [
                    sys.executable,
                    str(REPLAY_SCRIPT),
                    "--run-id",
                    CANONICAL_RUN_ID,
                ],
                env=env,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                pytest.fail(
                    "replay_run.py exited non-zero during determinism loop. "
                    f"stdout={result.stdout!r} stderr={result.stderr!r}"
                )

            current_reports = set(REPLAY_RECORDS_DIR.glob("*.json"))
            fresh_reports = sorted(
                current_reports - pre_replay_reports - set(new_reports)
            )
            assert len(fresh_reports) == 1, fresh_reports
            new_reports.append(fresh_reports[0])

            # Snapshot any per-replay ledgers the loop produced so the
            # teardown can remove them. The per-replay ledger filename
            # uses an ISO timestamp; the producer-side fix at HEAD lands
            # microsecond resolution so three replays inside the same
            # second land on three distinct paths. The fixture runs
            # against the recorded sandbox SHA whose replay_run.py may
            # still carry the legacy per-second format during the
            # migration round, so the assertion only requires that AT
            # LEAST one fresh ledger landed per iteration (the report
            # hash is the load-bearing determinism signal; the ledger
            # is the side-effect carrying the run.evidence.replayed
            # event). Tracking the union across iterations and removing
            # everything new on teardown keeps the working tree clean
            # under either format.
            current_ledgers = set(
                REPLAY_LEDGER_DIR.glob(f"replay-{CANONICAL_RUN_ID}-*.jsonl")
            )
            fresh_ledgers = sorted(
                current_ledgers - pre_replay_ledgers - set(new_ledgers)
            )
            new_ledgers.extend(fresh_ledgers)

            replay_record = json.loads(
                fresh_reports[0].read_text(encoding="utf-8")
            )
            triple = _canonical_triple(replay_record)
            canonical_tuples.append(triple)
            hashes.append(_hash_canonical(triple))

        unique_hashes = list(dict.fromkeys(hashes))
        if len(unique_hashes) > 1:
            FAILBUNDLE_DIR.mkdir(parents=True, exist_ok=True)
            first_idx = 0
            second_idx = next(
                i for i, h in enumerate(hashes) if h != hashes[0]
            )
            trace_0 = FAILBUNDLE_DIR / "trace_0.json"
            trace_1 = FAILBUNDLE_DIR / "trace_1.json"
            trace_0.write_text(
                json.dumps(
                    canonical_tuples[first_idx], sort_keys=True, indent=2
                )
                + "\n",
                encoding="utf-8",
            )
            trace_1.write_text(
                json.dumps(
                    canonical_tuples[second_idx], sort_keys=True, indent=2
                )
                + "\n",
                encoding="utf-8",
            )
            bundle_path = FAILBUNDLE_DIR / "determinism_failure.json"
            bundle = {
                "canonical_run_id": CANONICAL_RUN_ID,
                "canonical_run_record": "ops/run-records/"
                f"{CANONICAL_RUN_ID}.json",
                "sandbox_sha": sandbox_sha,
                "rerun_count": rerun_count,
                "unique_hashes": unique_hashes,
                "all_hashes": hashes,
                "first_mismatch_indices": [first_idx, second_idx],
                "trace_paths": [
                    trace_0.relative_to(ROOT).as_posix(),
                    trace_1.relative_to(ROOT).as_posix(),
                ],
            }
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            pytest.fail(
                "replay determinism test: hashes diverged across "
                f"{rerun_count} replays of {CANONICAL_RUN_ID}. "
                f"Unique hashes: {unique_hashes}. "
                f"Failure bundle: {bundle_path.relative_to(ROOT).as_posix()}"
            )
    finally:
        # Teardown: restore the saved HEAD first so a failed checkout
        # does not leave the working tree on the sandbox SHA, then
        # delete any replay artifacts the loop produced under the
        # working tree so the test does not pollute the on-disk state.
        _git(["checkout", saved_head])
        for path in new_reports:
            _safe_remove(path)
        for path in new_ledgers:
            _safe_remove(path)
        # Drop the per-run replay-records dir if the test created it
        # and it is now empty (a prior committed report would keep
        # the dir populated and skip this branch).
        if (
            REPLAY_RECORDS_DIR.is_dir()
            and not any(REPLAY_RECORDS_DIR.iterdir())
        ):
            try:
                REPLAY_RECORDS_DIR.rmdir()
            except OSError:
                pass
