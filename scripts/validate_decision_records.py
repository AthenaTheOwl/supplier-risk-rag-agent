#!/usr/bin/env python3
"""Validate every ops/decision-records/*.json against the JSON Schema.

Walks the records directory, loads each file, and runs jsonschema
validation against schemas/decision_record.schema.json. Exits 1 with
a categorized list of failures on any mismatch.

Designed to run in CI alongside the other Python validators
(spec_check, validate_decisions, validate_dreams). Adopts the same
exit-code contract (0 OK, 1 fail) so the existing CI wiring catches it.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "decision_record.schema.json"
RECORDS_DIR = ROOT / "ops" / "decision-records"


@dataclass(frozen=True)
class Failure:
    path: Path
    reason: str


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_one(path: Path, schema: dict) -> Failure | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Failure(path, f"could not read/parse: {exc}")
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        return Failure(path, f"schema violation at /{exc.json_path or 'root'}: {exc.message}")
    return None


def main() -> int:
    if not SCHEMA_PATH.is_file():
        print(
            f"validate_decision_records: schema missing at {SCHEMA_PATH}",
            file=sys.stderr,
        )
        return 1
    schema = _load_schema()

    if not RECORDS_DIR.is_dir():
        print(
            f"validate_decision_records: no records dir at {RECORDS_DIR}; nothing to validate"
        )
        return 0

    files = sorted(RECORDS_DIR.glob("*.json"))
    if not files:
        print("validate_decision_records: 0 records (clean)")
        return 0

    failures: list[Failure] = []
    for path in files:
        failure = validate_one(path, schema)
        if failure:
            failures.append(failure)

    if failures:
        print(
            f"validate_decision_records: {len(failures)} of {len(files)} record(s) failed",
            file=sys.stderr,
        )
        for f in failures:
            rel = f.path.relative_to(ROOT).as_posix()
            print(f"  - {rel}: {f.reason}", file=sys.stderr)
        return 1

    print(f"validate_decision_records OK ({len(files)} record(s) validated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
