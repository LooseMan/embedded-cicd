#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

CGO_ENABLED="${CGO_ENABLED:-0}" GOOS=linux GOARCH=amd64 \
    go build -o api_client .
