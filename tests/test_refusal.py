from src.agent.answerer import SupplierRiskAgent
from src.agent.refusal import should_refuse
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker


def test_refuses_out_of_scope_question() -> None:
    ranker = HybridRanker(load_sample_corpus())
    results = ranker.search("Who won the Super Bowl?", top_k=5)
    decision = should_refuse("Who won the Super Bowl?", results)
    assert decision.refused


def test_refuses_unsupported_stock_question_even_with_company_name() -> None:
    ranker = HybridRanker(load_sample_corpus())
    results = ranker.search("What is Apple's stock price today?", top_k=5)
    decision = should_refuse("What is Apple's stock price today?", results)
    assert decision.refused


def test_answer_has_verified_citations_for_supported_question() -> None:
    agent = SupplierRiskAgent(HybridRanker(load_sample_corpus()))
    answer = agent.answer("Which companies disclosed customer-concentration risk?")
    assert not answer.refused
    assert answer.citations
    assert "[C1]" in answer.text


def test_answer_refuses_when_retrieval_is_unsupported() -> None:
    agent = SupplierRiskAgent(HybridRanker(load_sample_corpus()))
    answer = agent.answer("What is the weather in Taipei tomorrow?")
    assert answer.refused
    assert not answer.citations
