#!/usr/bin/env bash

set -euo pipefail

docker run --rm \
    --mount "type=bind,source=$(pwd),target=/workspace" \
    embedded-cicd-rust \
    rustc hello_world.rs -o hello_world