# Failure Modes

1. **Sample corpus is small.** The demo can miss companies or risks outside the
   20 checked-in excerpts. Full EDGAR ingestion plus a larger index would reduce
   this gap.

2. **Deterministic local embeddings are approximate.** Hash vectors are stable
   and keyless, but they are weaker than real semantic embeddings. Supplying an
   OpenAI key and building a Chroma index would improve semantic recall.

3. **Citation granularity is sentence-level.** The current answerer cites the
   best matching sentence in a retrieved chunk. Claim-level citation extraction
   would improve precision for long sentences.

4. **Live LLM rewrite can phrase unsupported nuance.** The app keeps verified
   deterministic citations, but a live rewrite could still introduce wording
   that is more interpretive than the source span. A stricter post-generation
   claim checker would reduce this risk.

5. **EDGAR filing sections vary by issuer.** The chunker preserves provided
   section labels but does not yet robustly detect every filing's internal Item
   headings. A filing-aware section parser would improve filtering.

6. **BM25 favors exact wording.** Queries using different industry terms can
   under-rank relevant excerpts. Query expansion and learned reranking would
   improve recall.

7. **No real-time SEC updates.** The repo is pull-on-demand. Scheduled ingestion
   and freshness metadata would be needed for current filing coverage.
