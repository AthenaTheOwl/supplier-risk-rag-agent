"""A deployment must not reuse an agent with old answer behavior or schema."""

import app


def test_agent_behavior_refreshes_while_retrieval_resource_is_reused(monkeypatch):
    rankers = []

    class AgentBeforeDeploy:
        def __init__(self, ranker):
            self.ranker = ranker
            rankers.append(ranker)

    class AgentAfterDeploy(AgentBeforeDeploy):
        pass

    monkeypatch.setattr(app, "SupplierRiskAgent", AgentBeforeDeploy)
    before = app.load_agent(use_reranker=False)
    monkeypatch.setattr(app, "SupplierRiskAgent", AgentAfterDeploy)
    after = app.load_agent(use_reranker=False)

    assert type(before) is AgentBeforeDeploy
    assert type(after) is AgentAfterDeploy
    assert before is not after
    assert before.ranker is after.ranker
    assert len(rankers) == 2


def test_ranker_built_by_reloaded_modules_is_rebuilt(monkeypatch):
    stale = app.load_ranker(use_reranker=False)

    class ReloadedHybridRanker(app.HybridRanker):
        pass

    monkeypatch.setattr(app, "HybridRanker", ReloadedHybridRanker)
    try:
        agent = app.load_agent(use_reranker=False)
        assert type(agent.ranker) is ReloadedHybridRanker
        assert agent.ranker is not stale
        assert app.load_agent(use_reranker=False).ranker is agent.ranker
    finally:
        app.load_ranker.clear()
