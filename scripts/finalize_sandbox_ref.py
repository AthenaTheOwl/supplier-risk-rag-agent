"""Rewrite the PENDING sandbox SHA token on a recorded Run record.

The eval-suite runner emits ``Run.sandbox_image_ref`` as
``repo://supplier-risk-rag-agent@PENDING/`` because the runner cannot
know the SHA of the commit that will ultimately contain the Run
record on disk. This script closes the loop: pass ``--run-id`` and
optionally ``--sha``, the script reads the recorded Run record JSON,
swaps the ``PENDING`` token for the resolved SHA, and writes the
file back in place. When ``--sha`` is omitted the script reads
``git rev-parse HEAD`` against the repo root.

This script exists to fix the systemic off-by-one bug Round 5
agents independently caught: a single-pass emitter that records
``git rev-parse HEAD`` at emit-time pins the parent commit (the
commit BEFORE the regenerate commit that writes the sample), not
the commit that ultimately contains the sample. The two-pass
emission pattern (emitter writes PENDING, this script rewrites
after the data commit lands) records the correct SHA without
making the emitter call git twice.

Usage:

    python scripts/finalize_sandbox_ref.py --run-id run-<id>
    python scripts/finalize_sandbox_ref.py --run-id run-<id> --sha <sha>

The script is idempotent: rewriting an already-finalized record with
the same SHA is a no-op. Rewriting with a different SHA is an error
unless ``--force`` is passed.

Exit codes: 0 OK, 1 violations or missing files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_NAME = "supplier-risk-rag-agent"

RUN_RECORDS_ENV = "SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"

_SANDBOX_RE = re.compile(
    r"^repo://(?P<repo>[a-z][a-z0-9-]*)@(?P<sha>[A-Za-z0-9]+)/$"
)


def _run_records_dir() -> Path:
    override = os.environ.get(RUN_RECORDS_ENV)
    if override:
        return Path(override)
    return ROOT / "ops" / "run-records"


def _git_head_sha(repo_path: Path) -> str | None:
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


def _is_valid_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{40}", value))


def finalize(
    run_id: str, *, sha: str | None = None, force: bool = False
) -> int:
    record_path = _run_records_dir() / f"{run_id}.json"
    if not record_path.is_file():
        print(
            f"finalize_sandbox_ref: Run record not found at "
            f"{record_path}. Pass --run-id matching a file under "
            f"ops/run-records/.",
            file=sys.stderr,
        )
        return 1

    if sha is None:
        sha = _git_head_sha(ROOT)
    if not sha or not _is_valid_sha(sha):
        print(
            f"finalize_sandbox_ref: could not resolve a valid 40-char hex "
            f"SHA (got {sha!r}). Pass --sha explicitly or run inside the "
            f"repo's git working tree.",
            file=sys.stderr,
        )
        return 1

    record = json.loads(record_path.read_text(encoding="utf-8"))
    current = record.get("sandbox_image_ref", "")
    match = _SANDBOX_RE.match(current) if isinstance(current, str) else None
    if not match:
        print(
            f"finalize_sandbox_ref: Run record's sandbox_image_ref does not "
            f"match the repo:// grammar (got {current!r}). Nothing to "
            f"rewrite.",
            file=sys.stderr,
        )
        return 1

    repo = match.group("repo")
    current_sha = match.group("sha")
    if repo != REPO_NAME:
        print(
            f"finalize_sandbox_ref: Run record references repo {repo!r}, "
            f"not {REPO_NAME!r}. Refusing to rewrite a cross-repo ref.",
            file=sys.stderr,
        )
        return 1

    if current_sha == sha:
        # Idempotent: already finalized to the same SHA.
        print(
            f"finalize_sandbox_ref: Run {run_id} already pins "
            f"{sha}; no change."
        )
        return 0
    if current_sha != "PENDING" and not force:
        print(
            f"finalize_sandbox_ref: Run {run_id} already pins SHA "
            f"{current_sha!r}; refusing to rewrite without --force.",
            file=sys.stderr,
        )
        return 1

    record["sandbox_image_ref"] = f"repo://{REPO_NAME}@{sha}/"
    # Preserve the existing serialization shape (sorted keys, 2-space
    # indent, trailing newline) so the rewritten file diffs cleanly
    # against the emitter's output.
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"finalize_sandbox_ref: Run {run_id} sandbox_image_ref rewritten "
        f"to repo://{REPO_NAME}@{sha}/"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finalize_sandbox_ref",
        description=(
            "Rewrite the PENDING sandbox SHA placeholder on a Run record "
            "to the resolved commit SHA. Closes the two-pass emission "
            "loop so the recorded SHA pins the commit that actually "
            "contains the Run record on disk."
        ),
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help=(
            "Run ID to finalize. Matches a file under ops/run-records/ "
            "(for example: run-2eab3c611b6a)."
        ),
    )
    parser.add_argument(
        "--sha",
        default=None,
        help=(
            "Full 40-char hex SHA to pin. Defaults to `git rev-parse HEAD` "
            "against the repo root."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Allow rewriting a sandbox_image_ref that already pins a real "
            "(non-PENDING) SHA. Off by default to keep finalization "
            "idempotent."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return finalize(run_id=args.run_id, sha=args.sha, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
