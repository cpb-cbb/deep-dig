from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf4llm


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def parse_pdf(path: Path) -> dict[str, object]:
    pdf_path = path.expanduser().resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file: {pdf_path}")

    markdown = pymupdf4llm.to_markdown(str(pdf_path))
    return {
        "fileName": pdf_path.name,
        "fileHash": sha256_file(pdf_path),
        "text": markdown,
        "textFormat": "markdown",
        "textLength": len(markdown),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a local PDF into Markdown.")
    parser.add_argument("pdf", type=Path, help="Path to the local PDF file")
    args = parser.parse_args()
    print(json.dumps(parse_pdf(args.pdf), ensure_ascii=False))


if __name__ == "__main__":
    main()
