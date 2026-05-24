"""Validate the spec-driven-development artifact set for supplier-risk-rag-agent.

Phase 0 rules — every active spec under `specs/NNNN-*/` must:
  1. Carry the six required ledger files (requirements, design, tasks,
     acceptance, research, traceability).
  2. Define at least one R-* requirement in requirements.md, with the
     R-PREFIX-NNN shape: `### R-PREFIX-001: ...`.
  3. Use an R-* prefix from the allowed set for this repo.
  4. Have a traceability.md that names every requirement defined in
     requirements.md (no orphan reqs).
  5. Avoid referencing R-* IDs in traceability.md that are not
     defined in requirements.md (no phantom IDs).
  6. Be listed in specs/README.md.

CDCP rule (added by spec 0001):
  7. Every R-* requirement defined in any requirements.md must be
     resolved by at least one decisions/DEC-*.md file whose
     front-matter `requirement:` field names that ID, OR be listed in
     `decisions/.spec-check-allowlist.yaml` under the `deferred` key,
     OR carry an R-CDCP-* prefix (covered collectively by
     DEC-CDCP-001-install-cdcp-governance.md).

Exit codes: 0 OK, 1 violations found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_ROOT = ROOT / "specs"
SPECS_INDEX = SPECS_ROOT / "README.md"
DECISIONS_ROOT = ROOT / "decisions"
ALLOWLIST_PATH = DECISIONS_ROOT / ".spec-check-allowlist.yaml"

# R-* requirements with this prefix do not need a per-ID DEC; they are
# resolved collectively by DEC-CDCP-001-install-cdcp-governance.md.
DEC_BOOTSTRAP_PREFIXES = {"CDCP"}

REQUIRED_FILES = (
    "requirements.md",
    "design.md",
    "tasks.md",
    "acceptance.md",
    "research.md",
    "traceability.md",
)

# R-* prefixes reserved for supplier-risk-rag-agent specs. CDCP covers
# the cognitive delivery control plane install (spec 0001). The
# subsystem backfill specs (0002-0006) carve out one prefix each.
# Future specs may add prefixes; add them here.
ALLOWED_PREFIXES = {
    "CDCP",  # 0001 cognitive delivery control plane
    "ING",   # ingestion (SEC client, chunker, manifest)
    "RET",   # 0002 retrieval (BM25, embedder, hybrid ranker, reranker)
    "AGT",   # agent (planner, answerer, refusal, citations)
    "LLM",   # 0003 LLM provider abstraction
    "EVL",   # 0004 evals (recall, citation faithfulness, abstention, refusal)
    "DEP",   # 0005 deploy + BYOK + secrets
    "CIT",   # 0006 citation verifier
    "UI",    # streamlit app surface
    "OPS",   # ops + deployment + BYOK
}

REQ_RE = re.compile(r"^###\s+(R-[A-Z]+-\d{3,}):", re.MULTILINE)
ID_RE = re.compile(r"\bR-([A-Z]+)-(\d{3,})\b")
SPEC_DIR_RE = re.compile(r"^\d{4}-[a-z0-9][a-z0-9-]*$")


def active_specs() -> list[Path]:
    if not SPECS_ROOT.exists():
        return []
    return sorted(
        path
        for path in SPECS_ROOT.iterdir()
        if path.is_dir() and SPEC_DIR_RE.match(path.name)
    )


def parse_dec_requirement(text: str) -> str | None:
    """Pull the `requirement:` value from a DEC file's YAML front-matter.

    A DEC file starts with `---` on line 1, has YAML key/value pairs,
    and closes with another `---`. We do a tiny line-based parse rather
    than pulling in PyYAML at this layer.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("requirement:"):
            value = stripped.split(":", 1)[1].strip()
            value = value.strip("\"'")
            return value or None
    return None


def collect_dec_requirements() -> set[str]:
    """Return the set of R-* IDs that at least one DEC file resolves."""
    resolved: set[str] = set()
    if not DECISIONS_ROOT.is_dir():
        return resolved
    for path in DECISIONS_ROOT.glob("DEC-*.md"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rid = parse_dec_requirement(text)
        if rid:
            resolved.add(rid)
    return resolved


def collect_allowlisted() -> set[str]:
    """Return the set of R-* IDs deferred via the allowlist file."""
    if not ALLOWLIST_PATH.is_file():
        return set()
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        print(
            f"spec_check: PyYAML not installed; "
            f"cannot read {ALLOWLIST_PATH.relative_to(ROOT).as_posix()}",
            file=sys.stderr,
        )
        return set()
    try:
        data = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(
            f"spec_check: failed to parse "
            f"{ALLOWLIST_PATH.relative_to(ROOT).as_posix()}: {exc}",
            file=sys.stderr,
        )
        return set()
    if not isinstance(data, dict):
        return set()
    deferred = data.get("deferred")
    if not isinstance(deferred, list):
        return set()
    ids: set[str] = set()
    for entry in deferred:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            ids.add(entry["id"])
        elif isinstance(entry, str):
            ids.add(entry)
    return ids


def main() -> int:
    violations: list[str] = []
    spec_dirs = active_specs()
    if not spec_dirs:
        print(f"spec_check: no spec folders found under {SPECS_ROOT}", file=sys.stderr)
        return 1

    index_text = SPECS_INDEX.read_text(encoding="utf-8") if SPECS_INDEX.exists() else ""

    # CDCP rule prep: collect all R-* IDs across every spec, then check
    # each against the DEC + allowlist + bootstrap-prefix exemptions.
    all_req_ids: set[str] = set()

    for spec_dir in spec_dirs:
        rel = spec_dir.relative_to(ROOT).as_posix()

        # 1. Required files
        missing = [name for name in REQUIRED_FILES if not (spec_dir / name).is_file()]
        if missing:
            violations.append(
                f"{rel}: missing required file(s): {', '.join(missing)}"
            )

        req_path = spec_dir / "requirements.md"
        trace_path = spec_dir / "traceability.md"
        if not req_path.is_file():
            continue

        req_text = req_path.read_text(encoding="utf-8")
        ids = REQ_RE.findall(req_text)
        all_req_ids.update(ids)

        # 2. At least one R-* defined
        if not ids:
            violations.append(
                f"{rel}/requirements.md: no R-* requirements defined "
                f"(expected `### R-PREFIX-001: ...` shape)"
            )
            continue

        # 3. Prefix allowed
        for rid in ids:
            prefix = rid.split("-", 2)[1]
            if prefix not in ALLOWED_PREFIXES:
                violations.append(
                    f"{rel}/requirements.md: unknown prefix `{prefix}` in `{rid}`. "
                    f"Allowed: {', '.join(sorted(ALLOWED_PREFIXES))}."
                )

        # 4 + 5. Traceability coverage + no phantom IDs
        if trace_path.is_file():
            trace_text = trace_path.read_text(encoding="utf-8")
            trace_ids = {
                f"R-{p}-{n}" for p, n in ID_RE.findall(trace_text)
            }
            req_id_set = set(ids)

            missing_in_trace = sorted(req_id_set - trace_ids)
            if missing_in_trace:
                violations.append(
                    f"{rel}/traceability.md: missing references to "
                    f"{', '.join(missing_in_trace)}"
                )

            phantom = sorted(trace_ids - req_id_set)
            phantom_unknown = [
                rid
                for rid in phantom
                if rid.split("-", 2)[1] not in ALLOWED_PREFIXES
            ]
            if phantom_unknown:
                violations.append(
                    f"{rel}/traceability.md: references unknown-prefix IDs "
                    f"{', '.join(phantom_unknown)}"
                )

        # 6. Spec listed in index
        if SPECS_INDEX.exists() and spec_dir.name not in index_text:
            violations.append(
                f"specs/README.md: missing entry for spec folder `{spec_dir.name}`"
            )

    # 7. CDCP rule: every R-* requirement must be resolved by a DEC,
    # listed in the allowlist, or carry a bootstrap-exempt prefix.
    dec_resolved = collect_dec_requirements()
    allowlisted = collect_allowlisted()
    for rid in sorted(all_req_ids):
        prefix = rid.split("-", 2)[1]
        if prefix in DEC_BOOTSTRAP_PREFIXES:
            continue
        if rid in dec_resolved:
            continue
        if rid in allowlisted:
            continue
        violations.append(
            f"decisions/: no DEC-* file resolves `{rid}` "
            f"(add a decisions/DEC-*.md with `requirement: {rid}` in "
            f"front-matter, or list {rid} under `deferred` in "
            f"decisions/.spec-check-allowlist.yaml)"
        )

    if violations:
        print("spec_check: violations found", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"spec_check OK ({len(spec_dirs)} active specs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
