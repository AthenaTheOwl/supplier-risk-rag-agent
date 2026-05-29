"""eval-001 (promoted from 2026-W21 dream).

Pin the 60/25/15 weighted-score formula and the 0.03 zero-overlap
fallback factor that DEC-RET-001 names as load-bearing for the
hybrid ranker.

The existing tests/test_ranker.py covers behavioral correctness
(the right chunk appears in the top-k). This file pins the
arithmetic so a future "let's tune the weights" PR cannot land
silently without updating both the test and DEC-RET-001.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.retrieval.index import DocumentChunk
from src.retrieval.ranker import HybridRanker


@dataclass
class _FixedEmbedder:
    """Embedder stub returning a controlled vector per text.

    The mapping keys on the first word of the text so the test can
    stage chunk vectors and a query vector with known cosine values.
    """

    vectors: dict[str, list[float]]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            key = text.split()[0].lower() if text.split() else ""
            out.append(self.vectors.get(key, [0.0, 0.0, 0.0]))
        return out


def _chunk(chunk_label: str, text: str, chunk_index: int) -> DocumentChunk:
    """Build a DocumentChunk; the label rides in metadata for lookup."""
    return DocumentChunk(
        cik="0000000001",
        accession="0000000001-24-000001",
        section="risk_factors",
        text=text,
        metadata={"label": chunk_label},
        chunk_index=chunk_index,
    )


def _corpus_with_match_and_noise() -> list[DocumentChunk]:
    """Three-chunk corpus: c1 holds all query tokens, c2/c3 are noise.

    Three chunks make BM25Okapi's IDF non-zero for the matching tokens
    (df=1, N=3 yields a positive IDF rather than the log(1)=0 case at
    df=1, N=2).
    """
    return [
        _chunk("c1", "supplier risk concentration disclosure", 0),
        _chunk("c2", "weather forecast cloudy tomorrow", 1),
        _chunk("c3", "garden tools rake shovel", 2),
    ]


def test_weights_match_dec_ret_001_sixty_twenty_five_fifteen() -> None:
    """The combined-score formula must use 0.60 / 0.25 / 0.15 weights.

    Covers: R-RET-001.
    """
    chunks = _corpus_with_match_and_noise()
    # The fixed embedder returns the same vector for the query and
    # the matching chunk (cosine = 1.0) and orthogonal vectors for
    # the noise chunks (cosine = 0.0). The query vector itself comes
    # back through `embed_texts([query])` with the query as the
    # first text.
    embedder = _FixedEmbedder(
        vectors={
            "supplier": [1.0, 0.0, 0.0],
            "weather": [0.0, 1.0, 0.0],
            "garden": [0.0, 0.0, 1.0],
        }
    )
    ranker = HybridRanker(chunks, embedder=embedder)
    results = ranker.search(
        "supplier risk concentration disclosure",
        top_k=3,
    )
    by_id = {result.chunk.metadata["label"]: result for result in results}

    # Chunk c1: max BM25 in the corpus (bm25_norm = 1.0), cosine 1.0,
    # overlap_ratio = 4 / 4 = 1.0. Combined = 0.60*1 + 0.25*1 + 0.15*1.
    c1 = by_id["c1"]
    assert c1.bm25_score == 1.0
    assert c1.vector_score == 1.0
    assert c1.overlap == 4
    expected_c1 = (0.60 * 1.0) + (0.25 * 1.0) + (0.15 * 1.0)
    assert abs(c1.score - expected_c1) < 1e-9
    assert abs(c1.score - 1.00) < 1e-9


def test_zero_overlap_falls_back_to_three_percent_vector_score() -> None:
    """A chunk with zero query-token overlap scores as 0.03 * vector."""
    chunks = _corpus_with_match_and_noise()
    # Stage chunk c2 with a vector that lands at cosine 0.8 against
    # the query vector so the fallback path returns 0.03 * 0.8.
    embedder = _FixedEmbedder(
        vectors={
            "supplier": [1.0, 0.0, 0.0],
            "weather": [0.8, 0.6, 0.0],
            "garden": [0.0, 0.0, 1.0],
        }
    )
    ranker = HybridRanker(chunks, embedder=embedder)
    results = ranker.search(
        "supplier risk concentration disclosure",
        top_k=3,
    )
    by_id = {result.chunk.metadata["label"]: result for result in results}

    c2 = by_id["c2"]
    assert c2.overlap == 0
    # Cosine of the query vector [1,0,0] against [0.8, 0.6, 0] is 0.8.
    assert abs(c2.vector_score - 0.8) < 1e-9
    expected_c2 = 0.03 * 0.8
    assert abs(c2.score - expected_c2) < 1e-9

    c3 = by_id["c3"]
    assert c3.overlap == 0
    # Cosine of [1,0,0] against [0,0,1] is zero.
    assert c3.vector_score == 0.0
    assert c3.score == 0.0


def test_weight_swap_would_break_combined_score() -> None:
    """A different weight split would change the score; pin 60/25/15."""
    # Stage chunk c1 with a doc vector that yields cosine = 1/sqrt(2)
    # against the query vector. The 0.25 cosine weight then surfaces
    # in the combined score in a way a different split would shift.
    chunks_stage = [
        _chunk("c1", "halfcos risk concentration disclosure", 0),
        _chunk("c2", "weather forecast cloudy tomorrow", 1),
        _chunk("c3", "garden tools rake shovel", 2),
    ]
    embedder_stage = _FixedEmbedder(
        vectors={
            # query vector "supplier risk ..." -> first word "supplier"
            "supplier": [1.0, 0.0, 0.0],
            # chunk c1 doc vector with cosine = 1/sqrt(2) against query
            "halfcos": [1.0, 1.0, 0.0],
            "weather": [0.0, 1.0, 0.0],
            "garden": [0.0, 0.0, 1.0],
        }
    )
    ranker_stage = HybridRanker(chunks_stage, embedder=embedder_stage)
    results_stage = ranker_stage.search(
        "supplier risk concentration disclosure",
        top_k=3,
    )
    c1_stage = next(
        result for result in results_stage if result.chunk.metadata["label"] == "c1"
    )
    # Cosine of [1,0,0] against [1,1,0] is 1/sqrt(2).
    expected_cos = 1.0 / math.sqrt(2.0)
    assert abs(c1_stage.vector_score - expected_cos) < 1e-9
    # Overlap is 3 of 4 query tokens (risk, concentration, disclosure).
    assert c1_stage.overlap == 3
    expected_score = (
        (0.60 * c1_stage.bm25_score)
        + (0.25 * c1_stage.vector_score)
        + (0.15 * (3 / 4))
    )
    assert abs(c1_stage.score - expected_score) < 1e-9
    # A 0.50/0.35/0.15 split yields a measurably different number.
    wrong_score = (
        (0.50 * c1_stage.bm25_score)
        + (0.35 * c1_stage.vector_score)
        + (0.15 * (3 / 4))
    )
    assert abs(c1_stage.score - wrong_score) > 1e-3
