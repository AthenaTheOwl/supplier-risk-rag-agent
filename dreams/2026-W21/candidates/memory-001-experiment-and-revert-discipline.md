---
id: dream-2026-W21-memory-001
kind: memory_update
target: .agents/AGENTS.md
mode: memory_consolidation
human_review_required: true
evidence:
  - experiments/01-cross-encoder-rerank/notes.md
  - experiments/01-cross-encoder-rerank/baseline.json
  - experiments/01-cross-encoder-rerank/variant.json
  - decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
  - decisions/DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag.md
---

## proposal

Add a paragraph under `.agents/AGENTS.md` `## Workflow
conventions` that names the experiments/-and-revert pattern as
the right shape for any change with uncertain eval lift. Suggested
text:

> Changes with uncertain eval lift (a new reranker, a different
> chunker, a swapped embedder) land under `experiments/NN-<slug>/`
> with `config.yaml`, `baseline.json`, `variant.json`, and
> `notes.md`. The four-suite gate decides; the experiment ships
> as a documented negative result if the variant misses any
> threshold. Production code is reverted in the same pass that
> records the result.

## why it earns its keep

The pattern is already load-bearing in the repo but lives only in
the reverted experiment's notes file. A future agent reading
`.agents/AGENTS.md` should see the discipline named where the
behavioral contract lives. The pattern is the difference between
"we tried it and it broke production" and "we tried it under a
gated rubric, the gate caught it, we shipped the negative result
as a documented artifact."

## evidence

- `experiments/01-cross-encoder-rerank/notes.md` — the format the
  pattern produced.
- `baseline.json` and `variant.json` — the measured deltas that
  drove the revert.
- `DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md` — the
  decision that recorded the result.
- `DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag.md`
  — the decision that kept the wiring opt-in so the experiment
  can be re-run on a larger corpus without re-implementation.

## promotion path

A human reviewer applies the paragraph to `.agents/AGENTS.md`
under `## Workflow conventions`, runs `python
scripts/voice_lint.py` against the modified file, and confirms
the lint stays clean. The patch is one paragraph; the diff is
small enough to land in a single commit.

## risks if promoted blindly

- Adding a generic "always run an experiment first" instruction
  would slow down obvious wins. The proposal scopes the pattern
  to "changes with uncertain eval lift" specifically.
- Codifying the pattern in `.agents/AGENTS.md` before the second
  experiment lands risks pinning the shape too early. The current
  shape (four files in `experiments/NN-<slug>/`) is one data
  point. A second experiment may surface a missing file or a
  different config layout; the memory update earns a revision in
  that case, not a rewrite.
