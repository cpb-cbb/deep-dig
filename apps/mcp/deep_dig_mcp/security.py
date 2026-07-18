from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from deep_dig_mcp.errors import DeepDigMcpError


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def config_fingerprint(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def document_id_for(
    file_hash: str,
    parser_name: str,
    parser_version: str,
    parser_config_hash: str,
) -> str:
    identity = "\n".join((file_hash, parser_name, parser_version, parser_config_hash))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def resolve_input_document(
    raw_path: str | Path,
    *,
    allowed_roots: Iterable[Path],
    allowed_extensions: set[str],
    max_file_bytes: int,
) -> Path:
    value = str(raw_path)
    if not value or "\x00" in value:
        raise DeepDigMcpError("INVALID_PATH", "Document path is empty or invalid")

    roots = [_resolve_root(root) for root in allowed_roots]
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        if not roots:
            raise DeepDigMcpError("INVALID_PATH", "No input directory is configured")
        candidate = roots[0] / candidate

    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise DeepDigMcpError(
            "DOCUMENT_NOT_FOUND",
            f"Document not found: {candidate}",
        ) from exc

    if not any(resolved.is_relative_to(root) for root in roots):
        raise DeepDigMcpError(
            "PATH_OUTSIDE_ALLOWED_ROOT",
            "Document must be located inside an allowed input directory",
            detail={"path": str(resolved), "allowedRoots": [str(root) for root in roots]},
        )
    if not resolved.is_file():
        raise DeepDigMcpError("NOT_A_FILE", f"Document is not a regular file: {resolved}")
    if resolved.suffix.lower() not in allowed_extensions:
        raise DeepDigMcpError(
            "UNSUPPORTED_FORMAT",
            f"Unsupported document format: {resolved.suffix or '(none)'}",
            detail={"supportedFormats": sorted(allowed_extensions)},
        )
    size = resolved.stat().st_size
    if size <= 0:
        raise DeepDigMcpError("EMPTY_FILE", "Document is empty")
    if size > max_file_bytes:
        raise DeepDigMcpError(
            "FILE_TOO_LARGE",
            f"Document exceeds the {max_file_bytes}-byte local limit",
            detail={"size": size, "limit": max_file_bytes},
        )
    return resolved


def safe_output_path(output_dir: Path, requested_name: str, suffix: str) -> Path:
    name = requested_name.strip()
    if not name:
        raise DeepDigMcpError("INVALID_OUTPUT_NAME", "Output file name is empty")
    if Path(name).name != name or "/" in name or "\\" in name:
        raise DeepDigMcpError(
            "INVALID_OUTPUT_NAME",
            "Output file name must not contain directory components",
        )
    if not name.lower().endswith(suffix.lower()):
        name = f"{name}{suffix}"
    root = output_dir.resolve()
    destination = (root / name).resolve()
    if not destination.is_relative_to(root):
        raise DeepDigMcpError("INVALID_OUTPUT_NAME", "Output path escapes the output directory")
    return destination


def validate_document_id(document_id: str) -> str:
    value = document_id.strip().lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise DeepDigMcpError("INVALID_DOCUMENT_ID", "Document ID must be a SHA-256 hex value")
    return value


def _resolve_root(root: Path) -> Path:
    try:
        return root.expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise DeepDigMcpError(
            "INPUT_ROOT_NOT_FOUND",
            f"Configured input directory does not exist: {root}",
        ) from exc
