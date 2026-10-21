#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "$SCRIPT_DIR/pxl_ros2_lyrical_vnc_image/99_remove_image.sh" "$@"
