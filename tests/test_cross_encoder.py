"""Tests for the opt-in CrossEncoderReranker.

These tests mock the sentence-transformers `CrossEncoder` class so the
suite runs without the experiments-group dep installed and without any
model download.

Covers:
- shape of rerank() output (top_k, type, score replacement)
- lazy load: first call constructs the model; second call reuses it
- ordering: rerank reorders candidates by predicted score
- empty input: returns []
- graceful fallback when model load fails (returns input top_k unchanged)

DEC requirements exercised: R-RET-004 (opt-in reranker via constructor
and runner flag), R-RET-006 (cross-encoder reranker shipped opt-in).
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.retrieval.index import DocumentChunk
from src.retrieval.ranker import SearchResult


def _result(label: str, score: float) -> SearchResult:
    chunk = DocumentChunk(
        cik="0000000001",
        accession="0000000001-24-000001",
        section="risk_factors",
        text=f"chunk-text-for-{label}",
        metadata={"label": label},
        chunk_index=0,
    )
    return SearchResult(
        chunk=chunk,
        score=score,
        bm25_score=score,
        vector_score=score,
        overlap=1,
    )


def _install_fake_sentence_transformers(
    monkeypatch: pytest.MonkeyPatch,
    predict_scores: list[float] | Exception,
) -> MagicMock:
    """Stand up a fake `sentence_transformers` module exporting CrossEncoder.

    Returns the MagicMock standing in for the model instance so tests can
    assert on construction and `.predict` calls.
    """
    fake_model = MagicMock(name="CrossEncoderModel")
    if isinstance(predict_scores, Exception):
        fake_model.predict.side_effect = predict_scores
    else:
        fake_model.predict.return_value = predict_scores

    fake_ctor = MagicMock(name="CrossEncoder", return_value=fake_model)
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = fake_ctor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    return fake_ctor


def test_rerank_returns_top_k_in_score_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reranker reorders candidates by predicted score and trims to top_k."""
    from src.retrieval.reranker import CrossEncoderReranker

    candidates = [_result("a", 0.9), _result("b", 0.8), _result("c", 0.7)]
    # Predicted scores invert the input order: c > b > a.
    _install_fake_sentence_transformers(monkeypatch, predict_scores=[0.1, 0.5, 0.9])

    reranker = CrossEncoderReranker()
    top = reranker.rerank("query", candidates, top_k=2)

    assert len(top) == 2
    assert [r.chunk.metadata["label"] for r in top] == ["c", "b"]
    # Scores are replaced with the cross-encoder's float prediction.
    assert top[0].score == pytest.approx(0.9)
    assert top[1].score == pytest.approx(0.5)


def test_rerank_lazy_loads_model_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The model is constructed on first rerank() call and reused after."""
    from src.retrieval.reranker import CrossEncoderReranker

    candidates = [_result("a", 0.9), _result("b", 0.8)]
    fake_ctor = _install_fake_sentence_transformers(
        monkeypatch, predict_scores=[0.4, 0.6]
    )

    reranker = CrossEncoderReranker(model_name="dummy-model")
    # Construction alone must not load the model.
    assert fake_ctor.call_count == 0

    reranker.rerank("q1", candidates, top_k=2)
    assert fake_ctor.call_count == 1
    fake_ctor.assert_called_with("dummy-model")

    # Second call reuses the cached model.
    reranker.rerank("q2", candidates, top_k=2)
    assert fake_ctor.call_count == 1


def test_rerank_empty_candidates_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty input returns [] without loading the model."""
    from src.retrieval.reranker import CrossEncoderReranker

    fake_ctor = _install_fake_sentence_transformers(monkeypatch, predict_scores=[])
    reranker = CrossEncoderReranker()

    assert reranker.rerank("query", [], top_k=5) == []
    # Model never loaded because the early-return short-circuits.
    assert fake_ctor.call_count == 0


def test_rerank_falls_back_when_model_load_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the model fails to load, rerank returns the input top_k unchanged."""
    from src.retrieval.reranker import CrossEncoderReranker

    # Install a fake sentence_transformers module whose CrossEncoder
    # constructor raises. The reranker should catch, log, and degrade
    # to the hybrid order.
    fake_module = types.ModuleType("sentence_transformers")

    def _failing_ctor(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("simulated model-download failure")

    fake_module.CrossEncoder = _failing_ctor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    candidates = [_result("a", 0.9), _result("b", 0.8), _result("c", 0.7)]
    reranker = CrossEncoderReranker()
    with caplog.at_level("WARNING"):
        out = reranker.rerank("query", candidates, top_k=2)

    # Returned shape: top_k of the input, original ordering and scores.
    assert len(out) == 2
    assert [r.chunk.metadata["label"] for r in out] == ["a", "b"]
    assert out[0].score == pytest.approx(0.9)
    # A second call also degrades without re-raising or re-attempting.
    out2 = reranker.rerank("query2", candidates, top_k=3)
    assert [r.chunk.metadata["label"] for r in out2] == ["a", "b", "c"]
    # The warning was logged on first failure.
    assert any("model load failed" in record.message for record in caplog.records)


def test_hybrid_ranker_with_reranker_uses_reranked_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: HybridRanker(reranker=...) routes results through the reranker."""
    from src.retrieval.ranker import HybridRanker
    from src.retrieval.reranker import CrossEncoderReranker

    chunks = [
        DocumentChunk(
            cik="0000000001",
            accession="0000000001-24-000001",
            section="risk_factors",
            text="supplier risk concentration disclosure alpha",
            metadata={"label": "alpha"},
            chunk_index=0,
        ),
        DocumentChunk(
            cik="0000000001",
            accession="0000000001-24-000002",
            section="risk_factors",
            text="supplier risk concentration disclosure beta",
            metadata={"label": "beta"},
            chunk_index=0,
        ),
        DocumentChunk(
            cik="0000000001",
            accession="0000000001-24-000003",
            section="risk_factors",
            text="weather forecast cloudy tomorrow",
            metadata={"label": "gamma"},
            chunk_index=0,
        ),
    ]
    # Make the cross-encoder score beta > alpha so the reranker output
    # disagrees with whatever the hybrid order happens to be.
    _install_fake_sentence_transformers(
        monkeypatch, predict_scores=[0.2, 0.9, 0.05]
    )

    reranker = CrossEncoderReranker()
    ranker = HybridRanker(chunks, reranker=reranker, candidate_pool=10)
    results = ranker.search("supplier risk concentration disclosure", top_k=2)

    assert len(results) == 2
    # Beta wins because the cross-encoder gave it the highest score.
    assert results[0].chunk.metadata["label"] == "beta"
    assert results[0].score == pytest.approx(0.9)
