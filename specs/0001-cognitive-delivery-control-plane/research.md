# research: cognitive-delivery-control-plane

Research checked 2026-05-24.

- The CDCP framing came out of a synthesis pass across athena-site
  and the other product repos. Specs were already gated by a six-file
  pattern in `ai-field-brief`; decisions were not. The supplier-risk
  RAG agent here had a single `DECISIONS.md` flat file with no
  schema, no per-requirement traceability, and no gate.
- The cross-repo schemas under `athena-site/ops/schemas/` (artifact,
  decision, dream-output, role, tool, policy, skill) are the source
  of truth. This repo references them by URL and keeps a local cache
  copy for offline CI.
- Anthropic's published guidance on agent skills (March 2026) frames
  a skill as instructions plus optional scripts and evals, graduated
  from observed practice. The `skill.schema.json` shape in
  athena-site follows that pattern.
- The codex workflow pattern in athena-site uses declarative YAML
  workflows with named steps; this repo mirrors that under
  `.agents/workflows/`.
- The reset ledger pattern came from the
  `procurement-negotiation-lab` repo's audit-trail discipline;
  force-pushes get recorded in the same push so the trail survives
  the rewrite.
- The release ledger backfill covers six commits from `70f3253`
  (initial RAG agent) through `58797c6` (the cross-encoder reranker
  experiment, reverted). Each entry names which gates the release
  passed.

## Why now

- Specs alone do not record why a path was chosen over alternatives.
  DEC files fill that gap. The repo shipped six commits without one
  structured decision record.
- The eval discipline (retrieval, citation faithfulness, abstention,
  refusal) was already strong but the agent-side governance was
  thin. CDCP closes the loop.
- The prompt-or-model-change coupling is repo-specific: a change to
  `src/agent/prompts/` without a paired eval result update silently
  drifts answer quality. The operating-model layer encodes that as a
  policy plus a workflow gate, not a hope.

## Alternatives considered

- Keep the single-file `DECISIONS.md` and call it done: skipped
  because the flat file generates no executable gate and offers no
  schema to drift against.
- Adopt a framework stack (LangGraph, CrewAI, Strands): skipped
  because frameworks turn over every six months; the records survive
  the framework.
- A 12-screen control-plane SaaS: deferred until artifact volume
  warrants a UI layer beyond the markdown ledgers.
- Mirror the full 44-role operating-model catalog now: deferred. Six
  roles cover the single-change flow this repo runs; the rest land
  as specs grow into product surfaces that need them.

## Open questions

- When does the first dream output land? Likely after the second
  experiment in `experiments/` lands; the agent contract will name
  the trigger.
- How does the prompt-or-model-change workflow enforce the eval-suite
  hard gate in CI? Today the policy file encodes the rule and the
  workflow YAML documents the steps. A future commit wires the
  enforcement into a CI check.
- How do dream candidates that propose changes to gate scripts
  themselves get handled? Treated as a skill patch, gated by human
  review.
