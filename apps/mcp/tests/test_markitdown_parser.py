from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.parser import MarkItDownParser


def _write_text_pdf(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 50 220 Td (Deep Dig digital PDF text) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as destination:
        writer.write(destination)


def test_markitdown_parses_digital_pdf(tmp_path: Path) -> None:
    path = tmp_path / "digital.pdf"
    _write_text_pdf(path)
    parsed = MarkItDownParser().parse(
        path,
        config={"min_text_chars": 10, "min_chars_per_page": 1},
    )
    assert "Deep Dig digital PDF text" in parsed.markdown
    assert parsed.parser == "markitdown"
    assert parsed.page_count == 1


def test_damaged_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "damaged.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(DeepDigMcpError) as error:
        MarkItDownParser().parse(path)
    assert error.value.code == "INVALID_PDF"
