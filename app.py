from __future__ import annotations

from dataclasses import replace

import streamlit as st

from src.agent.answerer import SupplierRiskAgent
from src.agent.llm import LLMClient
from src.agent.portfolio_rollup import HoldingParseError, rollup_from_text
from src.config import MissingKeyError, get_keys, get_model_config
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker


@st.cache_resource(show_spinner=False)
def load_agent(use_reranker: bool = False) -> SupplierRiskAgent:
    chunks = load_sample_corpus()
    reranker = None
    if use_reranker:
        # Lazy import keeps sentence-transformers off the default-path cost.
        from src.retrieval.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker()
    return SupplierRiskAgent(HybridRanker(chunks, reranker=reranker))


def sidebar_keys() -> None:
    with st.sidebar:
        st.markdown("### Bring your own key")
        st.caption(
            "Paste the selected provider's key to enable live evidence ordering. Keys stay in "
            "this browser session (`st.session_state`). They are not logged, stored, "
            "or sent anywhere except the vendor SDK call you triggered."
        )
        anthropic_key = st.text_input(
            "Anthropic API key",
            type="password",
            value=st.session_state.get("anthropic_key", ""),
            help="Required when Anthropic is selected. Without a key the app still "
            "returns the deterministic cited answer.",
        )
        openai_key = st.text_input(
            "OpenAI API key",
            type="password",
            value=st.session_state.get("openai_key", ""),
            help="Required when OpenAI is selected; optional for separate live embedding "
            "experiments.",
        )
        st.session_state["anthropic_key"] = anthropic_key
        st.session_state["openai_key"] = openai_key
        st.divider()
        st.markdown("### Retrieval")
        use_reranker = st.checkbox(
            "Enable cross-encoder reranker (slower, may improve recall)",
            value=st.session_state.get("use_reranker", False),
            help=(
                "Off by default. When on, the hybrid ranker retrieves a wider "
                "candidate pool and a cross-encoder reorders the top-k. The "
                "model loads on first use (one-time ~80 MB download + a few "
                "seconds of CPU init); each query then pays ~150-400 ms of "
                "extra latency. The default hybrid stays the production path "
                "per DEC-RET-001."
            ),
        )
        st.session_state["use_reranker"] = use_reranker
        st.divider()
        st.caption(
            "No keys? The app still works. Deterministic retrieval, verbatim-span "
            "citations, and the offline eval suites all run without vendor calls."
        )


def render_answer(query: str, use_live_llm: bool) -> None:
    use_reranker = bool(st.session_state.get("use_reranker", False))
    agent = load_agent(use_reranker=use_reranker)
    keys = None
    key_error = None
    model_config = get_model_config()
    try:
        keys = get_keys(st.session_state, provider=model_config.provider)
    except (MissingKeyError, ValueError) as exc:
        key_error = str(exc)

    if key_error:
        st.info(f"{key_error} Showing deterministic retrieval preview without a live LLM call.")
        use_live_llm = False

    try:
        llm_client = LLMClient(keys, model_config) if keys and use_live_llm else None
        answer = agent.answer(
            query,
            use_live_llm=use_live_llm and llm_client is not None,
            keys=keys,
            llm_client=llm_client,
        )
    except Exception as exc:
        answer = replace(
            agent.answer(query, use_live_llm=False),
            generation_mode="live_failed",
            generation_reason=f"Live client failed ({exc.__class__.__name__}).",
        )

    if answer.generation_mode == "live_ordered":
        st.success("Live evidence order accepted. Every claim below is a verified source span.")
        st.caption(f"Live provider: {model_config.provider} / {model_config.model}")
    elif answer.generation_mode == "live_rejected":
        st.warning(
            f"Live output rejected: {answer.generation_reason} "
            "Showing the deterministic verified answer."
        )
    elif answer.generation_mode == "live_failed":
        st.error(
            f"Live provider fallback: {answer.generation_reason} "
            "Showing the deterministic verified answer."
        )
    else:
        st.caption("Deterministic answer. No live provider call was made.")

    if answer.refused:
        st.warning(answer.text)
    else:
        st.markdown(answer.text)

    st.divider()
    st.caption(f"Confidence: {answer.confidence:.3f}")
    with st.expander("Citations", expanded=True):
        if not answer.citations:
            st.write("No verified citations returned.")
        for citation in answer.citations:
            company = citation.metadata.get("company", "Unknown company")
            filing_type = citation.metadata.get("filing_type", "filing")
            year = citation.metadata.get("year", "unknown year")
            st.markdown(f"**[{citation.label}] {company} - {filing_type} {year}**")
            st.code(citation.span_text, language="text")
            st.caption(
                f"CIK {citation.cik} | {citation.accession} | {citation.section} | "
                f"offsets {citation.span_offsets[0]}-{citation.span_offsets[1]}"
            )


def render_investor_rollup() -> None:
    st.subheader("Investor rollup")
    holdings_text = st.text_area(
        "Holdings",
        value="AAPL 25\nNVDA 35\nTSM 40",
        height=140,
        help="One holding per line: ticker or CIK, optional weight. Example: NVDA 35.",
    )
    run_rollup = st.button("Build rollup", type="primary")
    if not run_rollup:
        return

    agent = load_agent(use_reranker=bool(st.session_state.get("use_reranker", False)))
    try:
        rollup = rollup_from_text(holdings_text, agent.ranker)
    except HoldingParseError as exc:
        for message in exc.messages:
            st.error(message)
        return

    if rollup.refused:
        st.warning(rollup.refused_reason)

    st.markdown("#### Holdings")
    for holding in rollup.holdings:
        weight = f"{holding.weight * 100:.1f}%"
        if holding.is_supported:
            st.write(f"- {holding.label}: {weight}")
        else:
            st.write(f"- {holding.label}: {weight}; insufficient evidence")

    st.markdown("#### Risk cards")
    for card in rollup.cards:
        st.markdown(f"**{card.category.title}**")
        st.caption(
            f"Status: {card.status} | Portfolio weight with verified evidence: "
            f"{card.evidence_weight * 100:.1f}%"
        )
        if card.refused_reason:
            st.info(card.refused_reason)
        for item in card.evidence:
            citation = item.citation
            st.markdown(
                f"- {item.holding.label} ({item.holding.weight * 100:.1f}%): "
                f"{citation.span_text} [{citation.label}]"
            )
        if card.missing_holdings:
            st.caption(
                "Insufficient evidence: "
                + ", ".join(holding.label for holding in card.missing_holdings)
            )
        st.divider()

    with st.expander("Rollup citations", expanded=False):
        if not rollup.citations:
            st.write("No verified citations returned.")
        for citation in rollup.citations:
            company = citation.metadata.get("company", "Unknown company")
            filing_type = citation.metadata.get("filing_type", "filing")
            year = citation.metadata.get("year", "unknown year")
            st.markdown(f"**[{citation.label}] {company} - {filing_type} {year}**")
            st.code(citation.span_text, language="text")
            st.caption(
                f"CIK {citation.cik} | {citation.accession} | {citation.section} | "
                f"offsets {citation.span_offsets[0]}-{citation.span_offsets[1]}"
            )

    col_md, col_json = st.columns(2)
    with col_md:
        st.download_button(
            "Download markdown",
            data=rollup.to_markdown(),
            file_name="investor-rollup.md",
            mime="text/markdown",
        )
    with col_json:
        st.download_button(
            "Download JSON",
            data=rollup.to_json(),
            file_name="investor-rollup.json",
            mime="application/json",
        )


def main() -> None:
    st.set_page_config(page_title="Supplier Risk RAG Agent", layout="wide")
    sidebar_keys()

    st.title("Supplier Risk RAG Agent")
    st.caption(
        "Citation-faithful RAG over SEC EDGAR filings. Every claim points at a "
        "verbatim span in a retrieved filing excerpt; unverified spans get refused, not "
        "paraphrased."
    )
    st.caption(
        "Try a starter question below, or write your own. Toggle **Live evidence order** "
        "to order verified evidence with the selected provider's key; leave it off for the "
        "deterministic cited answer."
    )

    ask_tab, rollup_tab = st.tabs(["Ask filings", "Investor rollup"])
    with ask_tab:
        example_queries = [
            "Which suppliers in this corpus disclosed export-control exposure?",
            "Which companies disclosed customer-concentration risk?",
            "Which firms mentioned advanced packaging capacity constraints?",
            "Where did filings mention supplier concentration or sole-source suppliers?",
        ]

        selected_example = st.selectbox("Starter questions", options=example_queries, index=0)
        query = st.text_input("Your question", value=selected_example)
        cols = st.columns([1, 1, 4])
        with cols[0]:
            live_llm = st.toggle("Live evidence order", value=False)
        with cols[1]:
            ask = st.button("Ask", type="primary")

        if ask and query.strip():
            render_answer(query.strip(), live_llm)

    with rollup_tab:
        render_investor_rollup()


if __name__ == "__main__":
    main()
