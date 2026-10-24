#!/usr/bin/env bash
# Container build, unit tests and live physics/sensor checks; no network needed.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
image=${ARDRONE_TEST_IMAGE:-pxl_ros2_lyrical_novnc:latest}
docker run --rm --init -e SENSORS_ONLY="${SENSORS_ONLY:-false}" \
    -v "$root/Projects/ardrone_workspace:/workspace:ro" "$image" bash -c '
        set -eo pipefail
        source /opt/ros/lyrical/setup.bash
        cd /workspace
        colcon --log-base /tmp/ardrone-log build --symlink-install \
            --build-base /tmp/ardrone-build --install-base /tmp/ardrone-install
        source /tmp/ardrone-install/setup.bash
        colcon --log-base /tmp/ardrone-log test --build-base /tmp/ardrone-build \
            --install-base /tmp/ardrone-install --event-handlers console_direct+
        colcon --log-base /tmp/ardrone-log test-result --test-result-base /tmp/ardrone-build --verbose
        tools/smoke.sh "$@"
    ' bash "${@}"
