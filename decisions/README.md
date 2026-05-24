# decisions

Specs name the what. Decisions name the why. Every shipped R-*
requirement carries at least one `DEC-*.md` file in this directory
that names the requirement, lists the alternatives, records the
rationale, points at the evidence, and writes down the rollback.

## Format

Each file is a markdown file with YAML front-matter at the top
matching the cross-repo `decision.schema.json` contract from
`https://raw.githubusercontent.com/AthenaTheOwl/athena-site/main/ops/schemas/decision.schema.json`.

The body holds five sections in this order:

1. `## decision` — one or two sentences naming what was chosen.
2. `## alternatives` — other paths considered, each with a label and
   a `rejected_because` reason.
3. `## rationale` — why the chosen path beats the alternatives.
4. `## evidence` — pointers to artifacts, runs, benchmarks, or prior
   decisions consulted.
5. `## rollback` — concrete steps to undo the decision.

## Filename

Filename format: `DEC-<PREFIX>-<NNN>-<kebab-slug>.md`.

The prefix follows the same R-* prefix as the requirement the
decision resolves. Example: `DEC-RET-001-hybrid-ranker.md` would
resolve `R-RET-001`. The slug is the short title in kebab-case.

## Adding a new decision

1. Identify the R-* requirement the decision resolves.
2. Copy an existing DEC file as a starting template.
3. Fill in the front-matter fields per `decision.schema.json`.
4. Write the five body sections.
5. Run `python scripts/validate_decisions.py` and confirm exit 0.
6. Run `python scripts/spec_check.py` and confirm the requirement is
   no longer flagged as orphaned.
7. Ship the DEC in the same commit as the requirement it resolves.

## Backfill

A DEC may document a past decision that landed without a record.
Backfill DECs use the same shape; the `date` field carries the date
the decision was originally taken (or the closest recorded date).

The repo's first DEC is:

- `DEC-CDCP-001-install-cdcp-governance.md` — the meta-decision to
  install the CDCP scaffold.

Existing pre-CDCP choices (BYOK key handling, deterministic CI,
sample manifest CIK mappings, model ID selection) are documented in
the legacy `DECISIONS.md` flat file and will be migrated to the
DEC-* shape as each subsystem earns its own spec (`0002-ingestion`,
`0003-retrieval`, etc.). Until then, the `R-CDCP-*` prefix is
exempt from per-ID DEC coverage via the
`DEC-BOOTSTRAP_PREFIXES` rule in `scripts/spec_check.py`.

## Gates

`scripts/validate_decisions.py` walks every `DEC-*.md` and validates
the front-matter against the cross-repo schema. The script keeps a
cache copy at `ops/schemas-cache/decision.schema.json` so CI runs
offline.

`scripts/spec_check.py` walks every R-* requirement and flags any
that lack a DEC reference (or an allowlist entry). The check runs on
every push.
