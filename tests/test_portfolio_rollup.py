import pytest

from src.agent.portfolio_rollup import (
    HoldingParseError,
    build_portfolio_rollup,
    parse_holdings,
)
from src.retrieval.citations import verify_citations
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker


def test_parse_holdings_accepts_ticker_cik_and_normalizes_weights() -> None:
    holdings = parse_holdings("AAPL 25%\nCIK:0001045810 weight:75")
    assert [holding.identifier for holding in holdings] == ["AAPL", "0001045810"]
    assert [holding.identifier_type for holding in holdings] == ["ticker", "cik"]
    assert holdings[0].weight == pytest.approx(0.25)
    assert holdings[1].weight == pytest.approx(0.75)


def test_parse_holdings_requires_all_or_no_weights() -> None:
    with pytest.raises(HoldingParseError) as exc:
        parse_holdings("AAPL 50\nNVDA")
    assert "provide weights for every holding" in str(exc.value)


def test_rollup_groups_supported_cards_with_verified_citations() -> None:
    ranker = HybridRanker(load_sample_corpus())
    holdings = parse_holdings("AAPL 25\nNVDA 35\nTSM 40")
    rollup = build_portfolio_rollup(holdings, ranker)

    assert not rollup.refused
    supplier = next(card for card in rollup.cards if card.category.key == "supplier")
    export_control = next(card for card in rollup.cards if card.category.key == "export_control")
    taiwan = next(card for card in rollup.cards if card.category.key == "taiwan")

    assert supplier.status == "supported"
    assert export_control.status == "supported"
    assert taiwan.status == "supported"
    assert supplier.evidence_weight > 0
    assert all(card.citations for card in [supplier, export_control, taiwan])

    for card in [supplier, export_control, taiwan]:
        for evidence in card.evidence:
            results = ranker.search(
                card.category.query,
                top_k=3,
                filters={"cik": evidence.holding.cik},
            )
            assert verify_citations([evidence.citation], results)


def test_rollup_refuses_when_no_holding_matches_corpus() -> None:
    ranker = HybridRanker(load_sample_corpus())
    holdings = parse_holdings("ZZZZ 100")
    rollup = build_portfolio_rollup(holdings, ranker)

    assert rollup.refused
    assert "None of the supplied holdings matched" in (rollup.refused_reason or "")
    assert all(card.status == "insufficient_evidence" for card in rollup.cards)
    assert not rollup.citations
