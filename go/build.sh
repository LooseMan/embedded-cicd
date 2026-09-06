#!/usr/bin/env bash

set -euo pipefail

target="${1:-amd64}"
case "$target" in
    amd64|linux-amd64)
        default_os=linux
        default_arch=amd64
        default_output=hello_world
        ;;
    mach-o|darwin-amd64|macos-amd64)
        default_os=darwin
        default_arch=amd64
        default_output=hello_world_macos_amd64
        ;;
    *)
        echo "usage: $0 [amd64|mach-o]" >&2
        exit 2
        ;;
esac

target_os="${TARGET_OS:-$default_os}"
target_arch="${TARGET_ARCH:-$default_arch}"
output="${OUTPUT:-$default_output}"

docker run --rm \
    --mount "type=bind,source=$(pwd),target=/workspace" \
    embedded-cicd-go \
    env GOOS="$target_os" GOARCH="$target_arch" \
    go build -o "$output" hello_world.go