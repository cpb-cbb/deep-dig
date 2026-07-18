#!/bin/sh
set -eu

mode="${1:-web}"
if [ "$mode" = "web" ]; then
  exec deep-dig-web
fi
exec "$@"
