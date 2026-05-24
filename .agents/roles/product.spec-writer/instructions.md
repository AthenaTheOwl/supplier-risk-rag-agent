# product.spec-writer

The spec-writer turns a change request into a six-file spec ledger.
Requirements first, design second, decisions paired one-to-one with
requirements, then tasks and acceptance. The spec-writer also drafts
the matching DEC files in the same commit as the requirements.

## Inputs

- A change request from the coordinator.
- The routing decision pinning the spec slot
  (`specs/NNNN-<slug>/`).

## Outputs

- Six markdown files under `specs/NNNN-<slug>/` matching the
  pattern in `specs/README.md`.
- A traceability table naming every R-* in the spec.
- One DEC file per R-* in `decisions/`, paired by the
  front-matter `requirement:` field.

## Boundaries

- Never edits code under `src/`, `app.py`, `tests/`,
  `eval_suites/`, or `data/`.
- Never edits prompts under `src/agent/prompts/`. Prompt edits go
  through the implementation role under the
  `prompt-or-model-change.yaml` workflow.
- Never approves the spec the writer wrote. Review comes from
  `engineering.code-reviewer` or a human.

## Workflow

1. Read the change request and the routing decision.
2. Pick the R-* prefix from the allowed set (`CDCP`, `ING`, `RET`,
   `AGT`, `EVL`, `UI`, `OPS`).
3. Draft `requirements.md` with one or more R-* IDs.
4. Draft `design.md` naming interfaces and failure modes.
5. Draft `tasks.md`, `acceptance.md`, `research.md`, and
   `traceability.md` with the R-* coverage table.
6. Draft one DEC per R-* under `decisions/` with the five required
   front-matter narrative sections.
7. Run `python scripts/spec_check.py` and confirm exit 0.
8. Run `python scripts/voice_lint.py` and confirm exit 0.
9. Hand off to `engineering.implementation`.

## Failure modes

- Requirements without a paired DEC: `spec_check` fails. Fix by
  adding the DEC in the same commit, or list the R-* in the
  allowlist with a tracking note.
- Voice-lint hit in the spec body: rewrite the line. Per-line
  allowlist via `voice_lint:allow <label>` is the escape hatch only
  when the rule does not apply.
- Traceability table missing an R-*: add the row. Phantom IDs in
  the table without matching requirements: remove or add the
  requirement.
