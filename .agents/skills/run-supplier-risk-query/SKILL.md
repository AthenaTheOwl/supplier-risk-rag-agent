---
id: run-supplier-risk-query
version: 0.1.0
owner_guild: domain
trigger:
  - operator question in the Streamlit sidebar
  - direct call to SupplierRiskAgent.answer
  - "manual supplier-risk query pass"
instructions_file: .agents/skills/run-supplier-risk-query/SKILL.md
scripts:
  - name: voice_lint
    path: scripts/voice_lint.py
    description: voice rules the published answer copy must pass
  - name: eval_runner
    path: src/evals/runner.py
    description: deterministic suite that scores citation faithfulness, recall, abstention, and refusal
evals: []
promotion_policy:
  requires:
    - human_approval
---

# skill: run-supplier-risk-query

This skill graduates the recurring supplier-risk RAG query pattern
implemented under `src/agent/`. The pattern has shipped in `app.py`
since the initial commit; this SKILL.md records the graduation and
pins the trigger surface, the scripts, and the promotion rule.

## What it does

Drives one supplier-risk question end-to-end:

1. Receive the operator question via Streamlit or a direct call.
2. Plan retrieval over the supplier-risk RAG index
   (`src/agent/planner.py`).
3. Run the hybrid retriever (BM25 + hashing embeddings + lexical
   overlap; see `src/retrieval/ranker.py`).
4. Run the refusal classifier (`src/agent/refusal.py`); if the
   question falls outside scope, return a refusal with rationale.
5. Assemble the cited answer (`src/agent/answerer.py`), verifying
   each citation span against the retrieved chunks
   (`src/retrieval/citations.py`).
6. When the operator supplies a live Claude key, rewrite the
   answer wording while keeping the verified spans as the citation
   source of truth.
7. Return the cited answer or the refusal.

## Trigger

- Operator question entered in the Streamlit sidebar at the
  deployed demo `https://supplier-risk-rag-agent.streamlit.app`.
- Direct call to `SupplierRiskAgent.answer(question)` from a
  Python script or notebook.
- Manual pass during eval-suite authoring or experiment runs.

## Instructions

Read `src/agent/answerer.py` top-to-bottom before changing the
behavior. Key rules:

- Citations are verified spans. Every claim in the returned answer
  points at a chunk the retriever returned, with span offsets that
  match the cited text. Do not relax the verifier.
- Refusal is the default for off-topic, opinion, or
  forward-looking-projection questions. The refusal classifier
  ships in `src/agent/refusal.py`; the rubric is in
  `eval_suites/refusal_cases.yaml`.
- Retrieval is deterministic in CI. The hashing embedder runs
  without API keys. The OpenAI embedder is opt-in for live
  experiments only.
- The live Claude rewrite path receives only the retrieved context
  and the deterministic cited answer. The verified spans remain
  the source of truth.
- No edits to `src/agent/prompts/` without a paired eval result
  update under `reports/`. The
  `eval-suite-required-before-prompt-change` policy fires
  otherwise.

## Scripts

- `scripts/voice_lint.py` — voice rules the published answer copy
  must pass when the answer ships to the demo or to a brief.
- `src/evals/runner.py` — deterministic suite that scores citation
  faithfulness, retrieval recall@5, abstention precision, and
  refusal correctness. Run before any prompt or model change.

## Evals

None yet wired as `passing_skill_eval` in the promotion policy. The
deterministic suite under `src/evals/` covers the four scoring axes
already; a golden-case eval for end-to-end answer quality lands when
the second supplier-risk skill graduates. Until then, promotion past
version 0.1.0 is gated on `human_approval`.

## Promotion policy

- v0.1.0 ships under `human_approval`.
- v0.2.0 onward requires `passing_skill_eval` in addition to
  `human_approval`.
- A breaking change to the trigger surface or the script API
  requires a major version bump.

## Open items

- Wire a golden-case eval that compares end-to-end answer quality
  against a reference set (today, the four deterministic scorers
  cover the components but not the composed output).
- Document the SEC `User-Agent` requirement for live EDGAR fetches
  in the skill body once the ingestion subsystem earns its own
  spec.
- Decide whether the live Claude rewrite path graduates as a
  separate skill once a second LLM provider is wired in.
