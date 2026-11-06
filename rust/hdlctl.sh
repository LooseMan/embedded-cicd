#!/usr/bin/env bash

set -euo pipefail

# Usage: hdlctl.sh [--release] PROCESS_NAME [APPLICATION_ARGS...]
# The process name is supplied by the caller so no PID file is required.
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly ENV_FILE="${SCRIPT_DIR}/.env"

log() {
    printf '[hdlctl] %s\n' "$*" >&2
}

usage() {
    printf 'usage: %s [--release] PROCESS_NAME [APPLICATION_ARGS...]\n' "$0" >&2
}

load_environment() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log "environment file not found: ${ENV_FILE}"
        return 1
    fi

    log "loading environment from ${ENV_FILE}"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
}

stop_container() {
    local process_name="$1"
    local running

    command -v docker >/dev/null 2>&1 || return 1
    running="$(docker container inspect --format '{{.State.Running}}' "$process_name" 2>/dev/null || true)"

    [[ "$running" == true ]] || return 1

    log "stopping container ${process_name}"
    docker stop "$process_name" >/dev/null
}

stop_host_process() {
    local process_name="$1"
    local attempt

    if ! pgrep -x "$process_name" >/dev/null 2>&1; then
        return 0
    fi

    log "stopping process ${process_name}"
    pkill -TERM -x "$process_name"

    for attempt in {1..50}; do
        if ! pgrep -x "$process_name" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.1
    done

    log "process ${process_name} did not stop after 5 seconds; sending SIGKILL"
    pkill -KILL -x "$process_name" 2>/dev/null || true
}

stop_previous_process() {
    local process_name="$1"

    if stop_container "$process_name"; then
        return 0
    fi

    stop_host_process "$process_name"
}

build_binary() {
    local process_name="$1"
    local build_profile="$2"
    local cargo_args=(build --bin "$process_name")

    if [[ "$build_profile" == release ]]; then
        cargo_args+=(--release)
    fi

    log "building ${process_name} (${build_profile})"
    (
        cd -- "$SCRIPT_DIR"
        cargo "${cargo_args[@]}"
    )
}

main() {
    if [[ "$#" -lt 1 ]]; then
        usage
        return 2
    fi

    local build_profile=debug
    if [[ "$1" == "--release" ]]; then
        build_profile=release
        shift
    fi

    if [[ "$#" -lt 1 ]]; then
        usage
        return 2
    fi

    local process_name="${1}-handler"
    shift

    if [[ "$process_name" == -* || ! "$process_name" =~ ^[[:alnum:]_.-]+$ ]]; then
        printf 'invalid process name: %s\n' "$process_name" >&2
        return 2
    fi

    load_environment
    build_binary "$process_name" "$build_profile"
    stop_previous_process "$process_name"

    log "starting ${process_name} (pid=$$)"
    exec "${SCRIPT_DIR}/target/${build_profile}/${process_name}" "$@"
}

main "$@"
