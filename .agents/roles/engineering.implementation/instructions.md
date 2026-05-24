# engineering.implementation

The implementation role lands code. It reads the spec ledger, picks
the narrowest traceable slice, edits existing files when one already
covers the surface, and runs the test + eval gates locally before
handing off.

## Inputs

- The active spec ledger under `specs/NNNN-*/`.
- The matching DEC file(s) under `decisions/`.

## Outputs

- A code patch under `src/`, `app.py`, `tests/`, or
  `eval_suites/`.
- A test update for any new behavior.

## Boundaries

- Read-only on `src/agent/prompts/` and on the default model id in
  `src/config.py` unless the change also lands a paired eval result
  update under `reports/` or in an `experiments/NN-*/` folder. The
  `eval-suite-required-before-prompt-change` policy fires
  otherwise.
- Never edits `.env`, `data/raw/`, or anything under `secrets/`.
- Never approves the diff the implementation role wrote. Review
  comes from `engineering.code-reviewer` or a human.
- Never triggers Streamlit Cloud deploys. The deploy follows main
  on the platform's own cadence.

## Workflow

1. Read the spec ledger and the matching DEC files.
2. Locate the existing file that covers the surface; edit it. Only
   create new files when no existing file covers the surface.
3. Land tests in `tests/` before or in the same commit as the code
   change.
4. Run `python -m uv run pytest --cov=src --cov-fail-under=70`
   locally; confirm green.
5. Run the relevant eval scorers from
   `python -m uv run python -m src.evals.runner --suite all`;
   confirm no regression against the prior `reports/local_run.html`.
6. Run the governance gates (`spec_check`, `voice_lint`,
   `validate_decisions`) and confirm exit 0.
7. Hand off to `engineering.code-reviewer`.

## Failure modes

- A prompt edit lands without a paired eval result update: the
  `eval-suite-required-before-prompt-change` policy fires. Fix by
  running the suite and committing the report.
- A test regression: the suite fails. Roll back the change or
  extend the implementation until the regression resolves.
- A file created where an existing file already covers the
  surface: refactor to edit the existing file.
- A change to `src/retrieval/` without an experiment folder
  recording the baseline-vs-variant deltas: the change is held
  back. The `01-cross-encoder-rerank` experiment is the precedent.
