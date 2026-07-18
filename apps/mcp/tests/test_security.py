from __future__ import annotations

from pathlib import Path

import pytest

from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.security import (
    config_fingerprint,
    document_id_for,
    resolve_input_document,
    safe_output_path,
    sha256_file,
)


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"abc")
    assert (
        sha256_file(path)
        == "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_cache_identity_includes_parser_and_config() -> None:
    first = document_id_for("sha256:a", "markitdown", "1", config_fingerprint({"a": 1}))
    second = document_id_for("sha256:a", "markitdown", "2", config_fingerprint({"a": 1}))
    third = document_id_for("sha256:a", "markitdown", "1", config_fingerprint({"a": 2}))
    assert len({first, second, third}) == 3


def test_input_path_cannot_escape_mount(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4")
    with pytest.raises(DeepDigMcpError, match="allowed input") as error:
        resolve_input_document(
            outside,
            allowed_roots=[workspace],
            allowed_extensions={".pdf"},
            max_file_bytes=1024,
        )
    assert error.value.code == "PATH_OUTSIDE_ALLOWED_ROOT"


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4")
    link = workspace / "link.pdf"
    link.symlink_to(outside)
    with pytest.raises(DeepDigMcpError) as error:
        resolve_input_document(
            link,
            allowed_roots=[workspace],
            allowed_extensions={".pdf"},
            max_file_bytes=1024,
        )
    assert error.value.code == "PATH_OUTSIDE_ALLOWED_ROOT"


def test_output_name_cannot_traverse(tmp_path: Path) -> None:
    with pytest.raises(DeepDigMcpError) as error:
        safe_output_path(tmp_path, "../result", ".xlsx")
    assert error.value.code == "INVALID_OUTPUT_NAME"
