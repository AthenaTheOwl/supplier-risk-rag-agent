---
id: DEC-RET-002-deterministic-hashing-embedder-default
spec: specs/0002-retrieval/
requirement: R-RET-002
date: 2026-05-24
status: approved
reversible: true
decision: |
  Ship a local 128-dimensional hashing embedder
  (`src/retrieval/embedder.py::HashingEmbedder`) as the default
  embedding path for CI evals and the deployed Streamlit demo. The
  BM25 index, the cosine score over hashing vectors, and the
  query/chunk term-overlap count are all pure functions of the
  in-memory corpus, so `python -m src.evals.runner --suite all`
  returns the same recall@5 on every run with no network access. The
  `OpenAIEmbedder` stays in tree as an opt-in path for live
  experiments that pass a BYOK `Keys` object.
alternatives:
  - label: OpenAI text-embedding-3-small as the default
    rejected_because: |
      Adds a per-query network round trip and a vendor key as a
      hard CI dependency. The eval suites must run on every push
      without secrets; a keyed embedder would either fail CI or
      force the test runner to fall back to a mocked embedder that
      drifts from production behavior. The OpenAI path stays
      available for live ingestion when a caller passes a key.
  - label: text-embedding-3-large or BGE-large local model
    rejected_because: |
      Larger vector dimensions and a model artifact for no measured
      recall lift on the 20-case retrieval_quality suite (BM25 plus
      the hashing cosine already saturates recall@5 at 1.000). The
      added download and the GPU-versus-CPU latency split are not
      worth the no-op delta at current corpus size.
  - label: sentence-transformers MiniLM as the default
    rejected_because: |
      Pulls in `sentence-transformers` and `torch` as required
      dependencies for the deployed demo and CI. Those packages
      already live in the `experiments` group, where they are
      optional; making them required would inflate the Streamlit
      build and the CI image without a recall payoff on the
      current corpus.
  - label: cached embeddings file checked into the repo
    rejected_because: |
      Saves the network round trip but introduces a stale-cache
      failure mode whenever the corpus changes. The hashing
      embedder regenerates vectors on every process start in
      microseconds; there is no cache to invalidate.
rationale: |
  Determinism is the load-bearing property. The four eval suites
  block PR merge through `python -m src.evals.runner --suite all`;
  if the embedder is nondeterministic, the gate flaps and the
  signal goes to zero. The hashing embedder is pure Python over
  `hashlib.sha256` plus a fixed dimension, so the vector for a
  given token is byte-identical on every host.

  The BM25 path through `rank_bm25` is also deterministic on a
  fixed token list, and the term-overlap count is a set
  intersection. The full ranker output is a pure function of the
  corpus plus the query.

  The hashing embedder also keeps CI free of vendor keys. The repo
  ships with BYOK as the deployment posture (see DEC-DEP-001); the
  default retrieval path matches that posture by needing zero
  secrets. The `OpenAIEmbedder` is constructed only when a caller
  passes a populated `Keys` object, so the keyed path stays
  available for live ingestion or experiments without leaking
  into CI.
evidence:
  - kind: spec
    ref: specs/0002-retrieval/requirements.md (R-RET-002)
  - kind: doc
    ref: src/retrieval/embedder.py (HashingEmbedder + OpenAIEmbedder)
  - kind: doc
    ref: src/retrieval/ranker.py (HybridRanker uses HashingEmbedder
      when no embedder is passed)
  - kind: benchmark
    ref: eval_suites/retrieval_quality.yaml (recall@5 >= 0.7 gate;
      observed 1.000 across runs)
  - kind: run
    ref: experiments/01-cross-encoder-rerank/baseline.json
      (deterministic baseline at recall@5 = 1.000)
  - kind: decision
    ref: DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
      (the weighted score that consumes these embeddings)
  - kind: decision
    ref: DEC-DEP-001-byok-streamlit-no-committed-keys.md (the BYOK
      posture this default matches)
rollback: |
  Switch the default embedder by editing the `embedder or
  HashingEmbedder()` line in `HybridRanker.__init__` to construct
  an `OpenAIEmbedder` instead. Callers passing a populated `Keys`
  object are unchanged. Re-run
  `python -m src.evals.runner --suite all` after the swap; the
  four-suite gate catches recall or faithfulness regressions. CI
  will start failing without a key in the environment, so a
  rollback to a keyed default also means wiring a CI secret.
owner: science.proof-gate-runner
---

## decision

Ship the local 128-dimensional hashing embedder as the default
embedding path. The BM25 + cosine + overlap ranker becomes a pure
function of the corpus and the query, so the eval runner returns
the same recall@5 on every run with no vendor key. The
`OpenAIEmbedder` stays in tree for opt-in live experiments.

## alternatives

- OpenAI `text-embedding-3-small` as default — forces a vendor key
  on every CI run and a per-query network round trip.
- `text-embedding-3-large` or BGE-large — larger vectors and a
  model artifact for no recall lift on the saturated sample
  corpus.
- sentence-transformers MiniLM — pulls torch into the deployed
  demo and CI image for no payoff at current corpus size.
- Cached embeddings file — saves the round trip but adds a
  stale-cache failure mode whenever the corpus changes.

## rationale

The four-suite eval gate runs on every push and must return a
stable score; a nondeterministic embedder flaps the gate and
drops the signal to zero. The hashing embedder is pure Python
over `hashlib.sha256` plus a fixed dimension, so the same query
returns byte-identical vectors on every host. The default also
matches the BYOK deployment posture from DEC-DEP-001: zero
secrets needed for CI or the deployed demo.

## evidence

- `src/retrieval/embedder.py` — the `HashingEmbedder` (default)
  and `OpenAIEmbedder` (opt-in) implementations.
- `src/retrieval/ranker.py` — the `HybridRanker.__init__` line
  that picks `HashingEmbedder` when no embedder is passed.
- `eval_suites/retrieval_quality.yaml` — the recall@5 >= 0.7 gate
  the deterministic path holds at 1.000.
- `experiments/01-cross-encoder-rerank/baseline.json` — captured
  baseline showing the deterministic recall@5.
- `DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md` — the
  weighted score that consumes the hashing vectors.
- `DEC-DEP-001-byok-streamlit-no-committed-keys.md` — the BYOK
  posture this default matches.

## rollback

Switch the default by editing the `embedder or HashingEmbedder()`
line in `HybridRanker.__init__` to construct an `OpenAIEmbedder`
instead. Re-run the four-suite gate after the swap; CI starts
failing without a key in the environment, so a keyed default also
means wiring a CI secret.
