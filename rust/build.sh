#!/usr/bin/env bash

set -euo pipefail

output="${OUTPUT:-hello_world}"

docker run --rm \
    --mount "type=bind,source=$(pwd),target=/workspace" \
    embedded-cicd-rust \
    env OUTPUT="$output" \
    sh -c 'cargo build --release && cp target/release/hello "$OUTPUT"'
