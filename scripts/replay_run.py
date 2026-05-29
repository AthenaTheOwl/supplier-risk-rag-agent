"""Equivalence replay of a recorded eval-suite Run.

This script reads a Run record under ``ops/run-records/<run-id>.json``,
re-executes the eval suite the Run originated from against the
checked-in sample corpus, and compares the three replay-equivalence
signals (``prompt_snapshot_hash``, ``tool_schemas_snapshot_hash``,
``gate_results_summary``) between the recorded Run and the fresh
Run.

Replay framing: "equivalence", not byte-identical determinism. The
eval suites are deterministic against the sample corpus (no sampling,
hashing embedder, deterministic ranker), but the LLM provider and
model identity is folded into ``tool_schemas_snapshot_hash``. Same
suite + same corpus + same LLM identity means the conditions for an
identical run match, which is the strongest claim we can make without
byte-comparing model outputs.

The replay is HEAD-strict: ``Run.sandbox_image_ref`` is parsed for the
SHA the producing commit pinned, and the script exits 1 with a
``git checkout <sha>`` hint when the current HEAD does not match. This
forces the operator to either run the replay at the pinned commit or
to acknowledge that the comparison would be apples-to-oranges.

A successful replay appends a ``run.evidence.replayed`` event to a
fresh per-replay ledger at
``ops/event-ledger/replay-<run-id>-<iso-timestamp>.jsonl`` and writes
a detailed comparison report at
``ops/replay-records/<run-id>/<replay-event-id>.json``. The original
ledger and Run record are not modified.

Transient artifacts the runner produces under the redirected env-var
dirs (the fresh Run record and ledger from the re-execution) are
discarded — the only canonical replay artifacts are the per-replay
ledger and the comparison report.

Exit codes: ``0`` equivalent (all three signals match), ``1`` divergent
or pre-flight failure. The summary printed to stdout names each
mismatch so the operator can dispatch on the failing signal.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Portable URI grammar from athena-site DEC-CDCP-014, mirrored in
# scripts/validate_run_evidence.py. Replay parses
# ``Run.sandbox_image_ref`` for the SHA in either the new repo://
# form or the legacy ``<abs-path>@<sha>`` form. The duplicated
# regex avoids a sibling-script import in the replay path.
_REPO_URI_RE = re.compile(
    r"^repo://(?P<repo>[a-z][a-z0-9-]*)@(?P<sha>[a-f0-9]{40})/(?P<path>.*)$"
)
_ARTIFACT_URI_RE = re.compile(
    r"^artifact://(?P<repo>[a-z][a-z0-9-]*)/(?P<id>.+)$"
)


def resolve_uri(
    uri: str, portfolio_root: Path | None = None
) -> Path | None:
    """Resolve a ``repo://`` URI to a local path or pass legacy paths through.

    Mirrors :func:`scripts.validate_run_evidence.resolve_uri`.
    Kept as a near-duplicate to keep replay's import graph small;
    both copies stay aligned with the grammar in DEC-CDCP-014.
    """
    if portfolio_root is None:
        portfolio_root = Path("e:/claude_code/random-apps")
    m = _REPO_URI_RE.match(uri)
    if m:
        return portfolio_root / m["repo"] / m["path"]
    m = _ARTIFACT_URI_RE.match(uri)
    if m:
        return None
    return Path(uri)

# Ops directory env-var overrides. The defaults point at the
# canonical layout under the repo root; tests redirect via env vars
# to avoid touching the checked-in artifacts. The same pattern lives
# in ``src/evals/runner.py``.
RUN_RECORDS_ENV = "SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"
EVENT_LEDGER_ENV = "SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"
REPLAY_RECORDS_ENV = "SUPPLIER_RISK_RAG_REPLAY_RECORDS_DIR"


def _run_records_dir() -> Path:
    return Path(os.environ.get(RUN_RECORDS_ENV) or (ROOT / "ops" / "run-records"))


def _event_ledger_dir() -> Path:
    return Path(os.environ.get(EVENT_LEDGER_ENV) or (ROOT / "ops" / "event-ledger"))


def _replay_records_dir() -> Path:
    return Path(
        os.environ.get(REPLAY_RECORDS_ENV) or (ROOT / "ops" / "replay-records")
    )


# Ensure the package import resolves even when the script is invoked
# from outside the repo root. The import chain pulls
# ``src.evals.run_evidence`` for the emit + event-factory helpers;
# keeping the resolution explicit avoids a ``ModuleNotFoundError``
# when the operator runs ``python scripts/replay_run.py`` from a
# different cwd.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Replay-method label that lands in the report and the
# ``run.evidence.replayed`` event payload (when consumers extend the
# payload). The cross-repo event schema allows "deterministic" or
# "equivalence"; this repo always emits "equivalence" because the LLM
# identity is in the surface hash but byte-comparing model outputs is
# out of scope.
REPLAY_METHOD = "equivalence"

ACTOR_KIND = "system"
ACTOR_ID = "supplier-risk-rag-agent-evals"


# --------------------------------------------------------------------- utils


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_filename_iso() -> str:
    """ISO-ish timestamp safe for use in a filename (no colons)."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _safe_rel(path: Path) -> str:
    """Return ``path`` relative to ROOT when possible, else the absolute form."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _git_head_sha(repo: Path) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603 - args fixed, no shell
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    head = result.stdout.strip()
    if result.returncode != 0 or not head:
        return None
    return head


def _parse_sandbox_sha(sandbox_image_ref: str) -> str | None:
    """Pull the HEAD SHA out of a sandbox_image_ref.

    Accepts both the portable repo URI form
    (``repo://supplier-risk-rag-agent@<sha>/``) per DEC-CDCP-014 and
    the legacy ``<abs-path>@<sha>`` form from before the Round-6
    migration. The new form takes precedence: if the URI parser
    matches it returns the SHA group; otherwise the legacy split
    on the last ``@`` runs as the fallback.
    """
    if not sandbox_image_ref:
        return None
    m = _REPO_URI_RE.match(sandbox_image_ref)
    if m:
        return m.group("sha") or None
    if "@" not in sandbox_image_ref:
        return None
    sha = sandbox_image_ref.rsplit("@", 1)[1].strip()
    # Strip a trailing slash that a repo:// URI without a strict
    # match (e.g. the PENDING placeholder) might leave behind.
    sha = sha.rstrip("/")
    return sha or None


def _suite_name_from_spec_id(spec_id: str) -> str:
    """Derive the suite name from a ``eval_suites/<name>.yaml`` ref."""
    # The spec_id on a Run record is the suite YAML path; the runner's
    # --suite flag takes the bare name without the directory or
    # extension.
    base = spec_id.rsplit("/", 1)[-1]
    if base.endswith(".yaml"):
        base = base[: -len(".yaml")]
    return base


# --------------------------------------------------------------------- IO


def _load_run_record(run_id: str) -> dict[str, Any]:
    record_path = _run_records_dir() / f"{run_id}.json"
    if not record_path.is_file():
        raise SystemExit(
            f"replay_run: Run record not found at "
            f"{_safe_rel(record_path)}. "
            f"Pass a --run-id that matches a file under ops/run-records/."
        )
    return json.loads(record_path.read_text(encoding="utf-8"))


def _load_event_ledger(run_id: str) -> list[dict[str, Any]]:
    ledger_path = _event_ledger_dir() / f"{run_id}.jsonl"
    if not ledger_path.is_file():
        raise SystemExit(
            f"replay_run: event ledger not found at "
            f"{_safe_rel(ledger_path)}. "
            f"Expected one ledger file per Run record."
        )
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        ledger_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"replay_run: ledger line {line_no} is not JSON: {exc}"
            ) from exc
    return events


# --------------------------------------------------------------------- pre-flight


def _enforce_head(recorded_sha: str | None, current_sha: str | None) -> None:
    """Exit 1 with a checkout hint when HEAD does not match the recorded SHA."""
    if not recorded_sha:
        raise SystemExit(
            "replay_run: Run record's sandbox_image_ref does not carry a "
            "parseable HEAD SHA. The original record may have been emitted "
            "outside a git working tree; replay cannot pin the commit."
        )
    if not current_sha:
        raise SystemExit(
            "replay_run: could not resolve current HEAD via "
            "`git rev-parse HEAD`. Run replay from within the repo's "
            "working tree."
        )
    if current_sha != recorded_sha:
        raise SystemExit(
            "replay_run: HEAD mismatch.\n"
            f"  Recorded sandbox SHA: {recorded_sha}\n"
            f"  Current HEAD:         {current_sha}\n"
            f"Run `git checkout {recorded_sha}` and re-run."
        )


# --------------------------------------------------------------------- replay


def _run_fresh_suite(suite_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Drive ``src/evals/runner.py`` once against a temp output dir.

    Returns ``(fresh_run_record, fresh_ledger_events)`` from the
    transient artifacts the runner wrote. The temp dir is deleted
    after the records are loaded — the canonical replay artifacts are
    the per-replay ledger and the comparison report this script
    writes, not the runner's per-execution Run record (whose run_id
    is a fresh UUID anyway).
    """
    with tempfile.TemporaryDirectory(prefix="replay-") as tmp:
        tmp_path = Path(tmp)
        ledger_dir = tmp_path / "event-ledger"
        records_dir = tmp_path / "run-records"
        env = os.environ.copy()
        env["SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"] = str(ledger_dir)
        env["SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"] = str(records_dir)
        # PYTHONIOENCODING avoids a UnicodeEncodeError on Windows when
        # Rich prints the suite table through a non-UTF-8 console.
        env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(  # noqa: S603 - args fixed, no shell
            [
                sys.executable,
                "-m",
                "src.evals.runner",
                "--suite",
                suite_name,
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
            raise SystemExit(
                "replay_run: fresh suite execution failed.\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}"
            )

        record_files = sorted(records_dir.glob("*.json"))
        ledger_files = sorted(ledger_dir.glob("*.jsonl"))
        if len(record_files) != 1 or len(ledger_files) != 1:
            raise SystemExit(
                "replay_run: fresh suite execution did not produce exactly one "
                f"Run record and one ledger file. Got {len(record_files)} "
                f"record(s) and {len(ledger_files)} ledger(s)."
            )
        fresh_run = json.loads(record_files[0].read_text(encoding="utf-8"))
        fresh_events: list[dict[str, Any]] = []
        for line in ledger_files[0].read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                fresh_events.append(json.loads(line))
        return fresh_run, fresh_events


# --------------------------------------------------------------------- compare


def _compare_runs(
    recorded: dict[str, Any], fresh: dict[str, Any]
) -> dict[str, Any]:
    """Compare the three replay-equivalence signals.

    Returns a comparison dict carrying per-signal match flags plus an
    overall ``replay_equivalent`` boolean. Hashes are compared as
    strings. ``gate_results_summary`` is compared as sets for the two
    name lists plus the ``all_passed`` flag so list ordering does not
    flap the comparison.
    """
    prompt_match = recorded.get("prompt_snapshot_hash") == fresh.get(
        "prompt_snapshot_hash"
    )
    tool_match = recorded.get("tool_schemas_snapshot_hash") == fresh.get(
        "tool_schemas_snapshot_hash"
    )

    rec_gate = recorded.get("gate_results_summary") or {}
    fresh_gate = fresh.get("gate_results_summary") or {}
    gate_match = (
        sorted(rec_gate.get("gates_passed", []))
        == sorted(fresh_gate.get("gates_passed", []))
        and sorted(rec_gate.get("gates_failed", []))
        == sorted(fresh_gate.get("gates_failed", []))
        and bool(rec_gate.get("all_passed")) == bool(fresh_gate.get("all_passed"))
    )

    return {
        "prompt_snapshot_hash": {
            "match": prompt_match,
            "recorded": recorded.get("prompt_snapshot_hash"),
            "fresh": fresh.get("prompt_snapshot_hash"),
        },
        "tool_schemas_snapshot_hash": {
            "match": tool_match,
            "recorded": recorded.get("tool_schemas_snapshot_hash"),
            "fresh": fresh.get("tool_schemas_snapshot_hash"),
        },
        "gate_results_summary": {
            "match": gate_match,
            "recorded": rec_gate,
            "fresh": fresh_gate,
        },
        "replay_equivalent": prompt_match and tool_match and gate_match,
    }


# --------------------------------------------------------------------- emit


def _emit_replay_event(
    run_id: str,
    event_id: str,
    replay_equivalent: bool,
    packet_ref: str,
    ledger_path: Path,
) -> dict[str, Any]:
    """Append a ``run.evidence.replayed`` event; return the written event.

    Uses an explicit ``event_id`` allocated by the caller so the
    comparison report can be named after the event before the event
    is written. Validates the event against the cached
    ``event.schema.json`` via ``src.evals.run_evidence.emit_event`` so
    the replay event matches the same contract the producer emits.
    """
    # Import lazily so the script can still print a clean error
    # message if the package import fails (the import chain pulls in
    # heavy deps that may not be present in a strictly-pre-flight env).
    from src.evals.run_evidence import emit_event, now_iso

    event: dict[str, Any] = {
        "event_id": event_id,
        "type": "run.evidence.replayed",
        "created_at": now_iso(),
        "actor": {"kind": ACTOR_KIND, "id": ACTOR_ID},
        "payload": {
            "run_id": run_id,
            "packet_ref": packet_ref,
            "replay_equivalent": replay_equivalent,
            "replay_method": REPLAY_METHOD,
        },
        "run_id": run_id,
    }
    emit_event(event, ledger_path)
    return event


def _write_report(
    run_id: str,
    recorded: dict[str, Any],
    fresh: dict[str, Any],
    comparison: dict[str, Any],
    event_id: str,
    replay_ledger_path: Path,
) -> Path:
    """Write the detailed comparison report; return its path."""
    report_dir = _replay_records_dir() / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{event_id}.json"

    replay_ledger_ref = _safe_rel(replay_ledger_path)

    report = {
        "replay_event_id": event_id,
        "replay_method": REPLAY_METHOD,
        "replay_equivalent": comparison["replay_equivalent"],
        "replayed_at": _now_iso(),
        "source_run_id": run_id,
        "source_run_record": f"ops/run-records/{run_id}.json",
        "source_event_ledger": f"ops/event-ledger/{run_id}.jsonl",
        "replay_event_ledger": replay_ledger_ref,
        "fresh_run_id": fresh.get("id"),
        "fresh_run_status": fresh.get("status"),
        "recorded_run_status": recorded.get("status"),
        "comparison": comparison,
    }
    report_path.write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report_path


# --------------------------------------------------------------------- main


def _print_summary(
    run_id: str,
    comparison: dict[str, Any],
    report_path: Path,
    replay_ledger_path: Path,
) -> None:
    print(f"replay_run: source run_id = {run_id}")
    print(f"replay_run: method        = {REPLAY_METHOD}")
    equiv = "equivalent" if comparison["replay_equivalent"] else "DIVERGENT"
    print(f"replay_run: result        = {equiv}")
    for key in (
        "prompt_snapshot_hash",
        "tool_schemas_snapshot_hash",
        "gate_results_summary",
    ):
        entry = comparison[key]
        flag = "match" if entry["match"] else "MISMATCH"
        print(f"  {key}: {flag}")
        if not entry["match"]:
            print(f"    recorded: {entry['recorded']!r}")
            print(f"    fresh:    {entry['fresh']!r}")
    try:
        rel_report = report_path.relative_to(ROOT).as_posix()
    except ValueError:
        rel_report = report_path.as_posix()
    try:
        rel_ledger = replay_ledger_path.relative_to(ROOT).as_posix()
    except ValueError:
        rel_ledger = replay_ledger_path.as_posix()
    print(f"replay_run: report  -> {rel_report}")
    print(f"replay_run: ledger  -> {rel_ledger}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="replay_run",
        description=(
            "Equivalence replay of a recorded eval-suite Run. Re-runs the "
            "suite against the checked-in corpus and compares the three "
            "replay-equivalence signals (prompt + tool surface hashes and "
            "the gate-results rollup) to the recorded Run."
        ),
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help=(
            "Run ID to replay. Matches a file under ops/run-records/ "
            "(for example: run-2eab3c611b6a)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_id: str = args.run_id

    # 1) Load the recorded Run record and its ledger.
    recorded = _load_run_record(run_id)
    _ = _load_event_ledger(run_id)  # validates that the ledger exists + parses

    # 2) HEAD-strict pre-flight against sandbox_image_ref.
    recorded_sha = _parse_sandbox_sha(recorded.get("sandbox_image_ref", ""))
    current_sha = _git_head_sha(ROOT)
    _enforce_head(recorded_sha, current_sha)

    # 3) Re-run the suite the Run originated from.
    suite_name = _suite_name_from_spec_id(str(recorded.get("spec_id", "")))
    fresh_run, _fresh_events = _run_fresh_suite(suite_name)

    # 4) Compare the three replay-equivalence signals.
    comparison = _compare_runs(recorded, fresh_run)

    # 5) Allocate the replay event_id up-front; the comparison report
    # is named after this event_id, and the event's packet_ref points
    # at the report path. Allocating the id ourselves means the report
    # filename is known before any artifact lands.
    from src.evals.run_evidence import new_event_id

    event_id = new_event_id()
    replay_ledger_path = (
        _event_ledger_dir() / f"replay-{run_id}-{_now_filename_iso()}.jsonl"
    )
    final_report_path = _replay_records_dir() / run_id / f"{event_id}.json"
    packet_ref = _safe_rel(final_report_path)

    # 6) Write the comparison report first so the event's packet_ref
    # resolves immediately for any consumer that follows it.
    _write_report(
        run_id=run_id,
        recorded=recorded,
        fresh=fresh_run,
        comparison=comparison,
        event_id=event_id,
        replay_ledger_path=replay_ledger_path,
    )

    # 7) Append the run.evidence.replayed event to the new per-replay
    # ledger. The original ledger at ops/event-ledger/<run-id>.jsonl
    # is not touched.
    _emit_replay_event(
        run_id=run_id,
        event_id=event_id,
        replay_equivalent=comparison["replay_equivalent"],
        packet_ref=packet_ref,
        ledger_path=replay_ledger_path,
    )

    _print_summary(run_id, comparison, final_report_path, replay_ledger_path)
    return 0 if comparison["replay_equivalent"] else 1


# Suppress unused-import lints; ``shutil`` is kept for parity with the
# existing emit pipeline and for downstream extension (e.g. cleanup of
# the transient runner artifacts when debug mode is added later).
_ = shutil


if __name__ == "__main__":
    sys.exit(main())
