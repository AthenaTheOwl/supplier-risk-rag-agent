from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker, tokenize


def test_tokenize_removes_common_stop_words() -> None:
    assert tokenize("Which suppliers disclosed customer concentration risk?") == [
        "suppliers",
        "disclosed",
        "customer",
        "concentration",
        "risk",
    ]


def test_ranker_finds_customer_concentration_results() -> None:
    """Hybrid ranker over the deterministic hashing-embedder index.

    Covers: R-RET-002.
    """
    ranker = HybridRanker(load_sample_corpus())
    results = ranker.search("Which companies disclosed customer concentration risk?", top_k=5)
    accessions = {result.chunk.accession for result in results}
    assert "0001045810-24-000029" in accessions
    assert results[0].score > 0.18


def test_ranker_filters_by_cik() -> None:
    """Filter results by chunk metadata keys (cik/accession/section).

    Covers: R-RET-003.
    """
    ranker = HybridRanker(load_sample_corpus())
    results = ranker.search(
        "export controls China restrictions",
        filters={"cik": "0000937966"},
        top_k=3,
    )
    assert results
    assert all(result.chunk.cik == "0000937966" for result in results)
