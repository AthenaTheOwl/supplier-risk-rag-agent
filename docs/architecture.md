# Architecture

The repo is a local-first supplier-risk RAG agent over SEC filing excerpts.

## Data flow

1. `data/sample_manifest.json` defines the default companies and filing types.
2. `data/sample_corpus/chunks.jsonl` provides 20 pre-chunked excerpts for demo
   and CI use without EDGAR or embedding API calls.
3. `src.ingest.sec_client.SECClient` can fetch EDGAR metadata and raw filing
   HTML when `--full-fetch` is used. It applies a custom `User-Agent`, a hard
   rate limit below 10 requests per second, retries transport failures, and
   caches raw HTML under `data/raw/`.
4. `src.ingest.chunker` strips HTML and creates overlapping chunks while
   preserving section metadata.
5. `src.retrieval.ranker.HybridRanker` combines BM25, deterministic local
   hashing vectors, and lexical overlap. OpenAI embeddings can be injected for
   live experiments, but CI defaults to the local embedder.
6. `src.agent.answerer.SupplierRiskAgent` retrieves excerpts, refuses weak or
   out-of-scope questions, and assembles cited answers.
7. `src.retrieval.citations` verifies that each citation span exists verbatim in
   a retrieved chunk before the answer is returned.
8. `app.py` exposes the workflow in Streamlit with BYOK keys.

## Citation contract

Each citation contains:

- `cik`
- `accession`
- `section`
- `span_text`
- `span_offsets`
- `chunk_id`

`verify_citations` rejects citations whose chunk was not retrieved or whose
offsets do not match the cited text.

## LLM use

The deterministic answerer is the default for tests and evals. A live Claude
rewrite can be enabled in Streamlit when the visitor supplies an Anthropic key.
The live rewrite receives only retrieved context and the deterministic cited
answer; citations remain the verified deterministic spans.
