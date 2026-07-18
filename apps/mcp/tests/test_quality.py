from __future__ import annotations

from deep_dig_mcp.quality import assess_markdown_quality, chunk_markdown


def test_empty_markdown_requires_ocr() -> None:
    warnings, needs_ocr = assess_markdown_quality(
        "",
        page_count=3,
        min_text_chars=200,
        min_chars_per_page=50,
    )
    assert needs_ocr is True
    assert warnings


def test_low_page_density_requires_ocr() -> None:
    warnings, needs_ocr = assess_markdown_quality(
        "short digital text" * 15,
        page_count=20,
        min_text_chars=20,
        min_chars_per_page=50,
    )
    assert needs_ocr is True
    assert any("density" in warning for warning in warnings)


def test_chunking_preserves_complete_markdown() -> None:
    markdown = "# A\n\n" + "first paragraph\n\n" * 30 + "# B\n\nend"
    chunks = chunk_markdown(markdown, 80)
    assert len(chunks) > 1
    assert "".join(chunks) == markdown
    assert all(len(chunk) <= 80 for chunk in chunks)
