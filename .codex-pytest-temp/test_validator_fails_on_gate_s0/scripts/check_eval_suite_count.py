#!/usr/bin/env python3
"""Validate that eval-suite counts stay synchronized across docs and runner."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_SUITES = ROOT / "eval_suites"
RUNNER = ROOT / "src" / "evals" / "runner.py"
README = ROOT / "README.md"
NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def suite_names() -> list[str]:
    return sorted(path.stem for path in EVAL_SUITES.glob("*.yaml"))


def runner_gate_names() -> list[str]:
    module = ast.parse(RUNNER.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "GATES":
                    if not isinstance(node.value, ast.Dict):
                        raise ValueError("GATES is not a dict literal")
                    names = []
                    for key in node.value.keys:
                        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                            raise ValueError("GATES keys must be string literals")
                        names.append(key.value)
                    return sorted(names)
    raise ValueError("GATES dict not found in src/evals/runner.py")


def main() -> int:
    suites = suite_names()
    gates = runner_gate_names()
    count = len(suites)
    count_word = NUMBER_WORDS.get(count, str(count))
    readme = README.read_text(encoding="utf-8").lower()

    findings: list[str] = []
    if suites != gates:
        findings.append(f"runner GATES {gates} does not match eval_suites {suites}")

    expected_phrase = f"{count_word} eval suites"
    if expected_phrase not in readme:
        findings.append(f"README does not contain {expected_phrase!r}")

    stale_four_phrase = re.search(r"\bfour eval suites\b", readme)
    if count != 4 and stale_four_phrase:
        findings.append("README still contains stale 'four eval suites' wording")

    if findings:
        print("check_eval_suite_count: drift detected", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"check_eval_suite_count OK ({count} suites: {', '.join(suites)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
