#!/bin/sh
set -eu

mode="${1:-mcp}"
if [ "$mode" = "mcp" ]; then
  exec deep-dig-mcp
fi
if [ "$mode" = "web" ]; then
  exec deep-dig-web
fi
exec "$@"

