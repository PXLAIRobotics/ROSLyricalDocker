#!/usr/bin/env bash
set -euo pipefail
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
args=(--rm -it --name=pxl_lyrical_vnc --hostname=pxl_lyrical_vnc --shm-size=2g)
args+=(-p "127.0.0.1:${VNC_PORT:-5901}:5901" -p "127.0.0.1:${WEB_PORT:-6901}:6901")
args+=(-e "VNC_PW=${VNC_PW:-password}" -e "VNC_RESOLUTION=${VNC_RESOLUTION:-1280x800}")
for directory in Commands/bin ExampleCode Data Projects; do
    args+=(-v "$REPO_DIR/$directory:/home/user/${directory##*/}")
done
source "$REPO_DIR/docker/gpu-options.sh"
exec docker run "${args[@]}" "$@" pxl_ros2_lyrical_vnc:latest
