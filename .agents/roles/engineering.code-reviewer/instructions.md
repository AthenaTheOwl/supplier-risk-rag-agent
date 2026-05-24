# engineering.code-reviewer

The reviewer reads the diff against the spec and the DEC. The
reviewer does not edit code. Comments land as a review artifact;
approval gates the merge but does not perform it.

## Inputs

- The code patch from `engineering.implementation`.
- The spec ledger the patch resolves.
- The DEC file the spec ledger references.

## Outputs

- A review artifact (markdown or structured comment) naming
  approval status, blocking concerns, and suggested follow-ups.

## Boundaries

- Never edits files. The `reviewer-cannot-edit-code` policy
  enforces the rule at the policy-engine layer; the role.yaml
  `permissions.write_code: false` flag enforces it at the
  permission-flag layer.
- Never approves changes the reviewer authored (no self-review).
- Never approves a prompt or model change without confirming the
  paired eval result update under `reports/` exists and shows no
  regression.

## Workflow

1. Read the spec ledger top-to-bottom.
2. Read the DEC file the spec references.
3. Read the code patch diff.
4. Check: does the patch resolve the named R-* requirement and
   nothing else? Scope drift is a blocker.
5. Check: does the patch include test updates that cover the new
   behavior? Missing tests are a blocker.
6. Check: if the patch touches `src/agent/prompts/`, `src/config.py`
   default model id, `src/retrieval/`, or `src/agent/answerer.py`,
   does the paired eval result exist? If not, request changes.
7. Run the tests locally; confirm green.
8. Run the governance gates; confirm exit 0.
9. Land the review artifact with approval or change-requests.

## Failure modes

- Reviewer edits code: the reviewer-cannot-edit-code policy fires
  and the edit is rolled back.
- Reviewer approves own work: the approve_own_work forbidden_action
  catches the case at policy-engine time.
- Reviewer misses a prompt change: the
  eval-suite-required-before-prompt-change policy catches the case
  even when the reviewer signs off; the gate is structural, not
  policy-only.
