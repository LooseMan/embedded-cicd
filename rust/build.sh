#!/usr/bin/env bash

set -euo pipefail

output="${OUTPUT:-api_server}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

cargo build --release
cp target/release/api_server "$output"
