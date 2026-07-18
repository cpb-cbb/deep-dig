from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess

from PyInstaller.__main__ import run as run_pyinstaller


DESKTOP_DIR = Path(__file__).resolve().parents[1]
ENTRY_POINT = DESKTOP_DIR / "desktop_parser" / "parse_pdf.py"
TAURI_DIR = DESKTOP_DIR / "src-tauri"
BINARY_DIR = TAURI_DIR / "binaries"
BINARY_NAME = "deep-dig-parser"


def host_target() -> str:
    result = subprocess.run(
        ["rustc", "--print", "host-tuple"],
        check=True,
        capture_output=True,
        text=True,
    )
    target = result.stdout.strip()
    if not target:
        raise RuntimeError("rustc returned an empty host target triple")
    return target


def output_path(target: str) -> Path:
    extension = ".exe" if "windows" in target else ""
    return BINARY_DIR / f"{BINARY_NAME}-{target}{extension}"


def source_is_newer_than(destination: Path) -> bool:
    if not destination.is_file():
        return True
    inputs = [
        *sorted((DESKTOP_DIR / "desktop_parser").rglob("*.py")),
        DESKTOP_DIR / "pyproject.toml",
        DESKTOP_DIR / "uv.lock",
        Path(__file__),
    ]
    destination_mtime = destination.stat().st_mtime
    return any(path.stat().st_mtime > destination_mtime for path in inputs)


def build(target: str, force: bool) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", target):
        raise ValueError(f"Invalid target triple: {target!r}")
    host = host_target()
    if target != host:
        raise RuntimeError(
            f"PyInstaller cannot cross-compile from {host} to {target}; "
            "run this build on the target platform"
        )

    destination = output_path(target)
    if not force and not source_is_newer_than(destination):
        print(f"Sidecar is up to date: {destination}")
        return destination

    build_root = DESKTOP_DIR / "build" / "sidecar" / target
    dist_dir = build_root / "dist"
    work_dir = build_root / "work"
    spec_dir = build_root / "spec"
    shutil.rmtree(build_root, ignore_errors=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    run_pyinstaller(
        [
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            BINARY_NAME,
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(work_dir),
            "--specpath",
            str(spec_dir),
            "--collect-data",
            "pymupdf",
            str(ENTRY_POINT),
        ]
    )

    extension = ".exe" if "windows" in target else ""
    built_binary = dist_dir / f"{BINARY_NAME}{extension}"
    if not built_binary.is_file():
        raise FileNotFoundError(f"PyInstaller did not create {built_binary}")

    BINARY_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_binary, destination)
    if "windows" not in target:
        destination.chmod(destination.stat().st_mode | 0o111)
    print(f"Built Tauri sidecar: {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the self-contained PDF parser sidecar.")
    parser.add_argument("--target", help="Rust target triple; defaults to the host target")
    parser.add_argument(
        "--force", action="store_true", help="Rebuild even when inputs are unchanged"
    )
    args = parser.parse_args()
    target = args.target or os.environ.get("TAURI_ENV_TARGET_TRIPLE") or host_target()
    destination = build(target, args.force)
    print(destination)


if __name__ == "__main__":
    main()
