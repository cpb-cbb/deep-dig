from __future__ import annotations

import re


def assess_markdown_quality(
    markdown: str,
    *,
    page_count: int | None,
    min_text_chars: int,
    min_chars_per_page: int,
) -> tuple[list[str], bool]:
    meaningful = re.sub(r"[\s#*_`>|\-]+", "", markdown)
    meaningful_length = len(meaningful)
    warnings: list[str] = []
    needs_ocr = False

    if meaningful_length == 0:
        warnings.append("No readable text was extracted; the document may be scanned or damaged.")
        needs_ocr = True
    elif meaningful_length < min_text_chars:
        warnings.append(
            f"Only {meaningful_length} meaningful characters were extracted; OCR may be required."
        )
        needs_ocr = True

    if page_count and meaningful_length / page_count < min_chars_per_page:
        warnings.append(
            "Extracted text density is unusually low for the number of PDF pages; "
            "the document may be image-based."
        )
        needs_ocr = True

    return warnings, needs_ocr


def chunk_markdown(markdown: str, max_chars: int) -> list[str]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if not markdown:
        return [""]

    chunks: list[str] = []
    remaining = markdown
    while len(remaining) > max_chars:
        cut = remaining.rfind("\n\n", 0, max_chars + 1)
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 2
        chunks.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining or not chunks:
        chunks.append(remaining)
    return chunks
