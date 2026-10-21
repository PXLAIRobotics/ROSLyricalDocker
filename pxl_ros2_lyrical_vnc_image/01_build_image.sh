#!/usr/bin/env bash
set -euo pipefail
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
args=(--target vnc --tag pxl_ros2_lyrical_vnc:latest)
args+=(--build-arg "USER_UID=$(id -u)" --build-arg "USER_GID=$(id -g)")
exec docker build "${args[@]}" "$@" "$REPO_DIR"
