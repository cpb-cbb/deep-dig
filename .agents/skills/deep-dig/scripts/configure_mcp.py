#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_config(workspace: Path, output: Path, image: str) -> str:
    args = [
        "run",
        "--rm",
        "-i",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--add-host",
        "host.docker.internal:host-gateway",
    ]
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        args.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
    args.extend(
        [
            "-v",
            f"{workspace}:/workspace:ro",
            "-v",
            f"{output}:/output",
            "-e",
            "DEEP_DIG_API_TOKEN",
            "-e",
            "DEEP_DIG_API_BASE_URL",
            image,
            "mcp",
        ]
    )
    rendered_args = ",\n  ".join(toml_string(value) for value in args)
    return (
        "[mcp_servers.deep-dig]\n"
        'command = "docker"\n'
        f"args = [\n  {rendered_args}\n]\n"
        'env_vars = ["DEEP_DIG_API_TOKEN", "DEEP_DIG_API_BASE_URL"]\n'
        "startup_timeout_sec = 30\n"
        "tool_timeout_sec = 300\n"
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(
        description="Print a Codex project MCP configuration for the Deep Dig Docker image."
    )
    parser.add_argument("--workspace", type=Path, default=repo_root)
    parser.add_argument("--output", type=Path, default=repo_root / "deep-dig-output")
    parser.add_argument("--image", default="deep-dig-mcp:local")
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    print(build_config(workspace, output, args.image))


if __name__ == "__main__":
    main()
