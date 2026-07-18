#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_config(url: str, token_env: str) -> str:
    return (
        "[mcp_servers.deep-dig]\n"
        f"url = {toml_string(url)}\n"
        f"bearer_token_env_var = {toml_string(token_env)}\n"
        "startup_timeout_sec = 30\n"
        "tool_timeout_sec = 300\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a Codex project configuration for the hosted Deep Dig MCP service."
    )
    parser.add_argument("--url", required=True, help="Hosted Streamable HTTP MCP URL ending in /mcp")
    parser.add_argument("--token-env", default="DEEP_DIG_MCP_TOKEN")
    args = parser.parse_args()
    url = args.url.strip()
    if not url.startswith(("https://", "http://")):
        parser.error("--url must be an http:// or https:// URL")
    if not url.rstrip("/").endswith("/mcp"):
        parser.error("--url must end with /mcp")
    token_env = args.token_env.strip()
    if not token_env or not token_env.replace("_", "").isalnum():
        parser.error("--token-env must be an environment variable name")
    print(build_config(url, token_env))


if __name__ == "__main__":
    main()
