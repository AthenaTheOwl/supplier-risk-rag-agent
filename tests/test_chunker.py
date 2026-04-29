from src.ingest.chunker import ChunkingConfig, chunk_text, html_to_text


def test_html_to_text_removes_scripts_and_tables() -> None:
    html = """
    <html><body><script>secret()</script><p>Risk factor text</p>
    <table><tr><td>numeric table</td></tr></table></body></html>
    """
    text = html_to_text(html)
    assert "Risk factor text" in text
    assert "secret" not in text
    assert "numeric table" not in text


def test_chunk_text_uses_overlap_and_metadata() -> None:
    words = " ".join(f"word{i}" for i in range(12))
    chunks = chunk_text(
        words,
        cik="320193",
        accession="0000320193-24-000123",
        section="Risk Factors",
        metadata={"company": "Apple Inc."},
        config=ChunkingConfig(max_words=5, overlap_words=2),
    )
    assert len(chunks) == 4
    assert chunks[0].text.split()[-2:] == chunks[1].text.split()[:2]
    assert chunks[0].cik == "0000320193"
    assert chunks[0].metadata["company"] == "Apple Inc."
