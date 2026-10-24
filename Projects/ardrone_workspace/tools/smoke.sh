#!/usr/bin/env bash
# Run inside the Lyrical environment after sourcing ROS and this workspace.
set -euo pipefail
workspace=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
world=${1:-empty}
count=${2:-2}
cameras=${3:-false}
if ! [[ "$count" =~ ^([1-9]|[12][0-9]|3[0-2])$ ]]; then
    echo "count must be an integer between 1 and 32" >&2
    exit 2
fi
export GZ_PARTITION="ardrone-test-$$"
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-73}
log_dir=$(mktemp -d)
launch_pid=
cleanup() {
    if [[ -n "$launch_pid" ]]; then
        kill -INT "$launch_pid" 2>/dev/null || true
        for attempt in {1..100}; do
            kill -0 "$launch_pid" 2>/dev/null || break
            sleep 0.1
        done
        kill -TERM -- "-$launch_pid" 2>/dev/null || true
        wait "$launch_pid" 2>/dev/null || true
    fi
    cat "$log_dir/launch.log"
    rm -rf "$log_dir"
}
trap cleanup EXIT
setsid python3 -c 'import os, signal, sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execvp(sys.argv[1], sys.argv[1:])' ros2 launch ardrone_gazebo multi_ardrones.launch.py \
    world:="$world" count:="$count" gui:=false cameras:="$cameras" \
    >"$log_dir/launch.log" 2>&1 &
launch_pid=$!
names=()
if (( count == 1 )); then names=(ardrone); else
    for ((i=1; i<=count; i++)); do names+=("ardrone_$i"); done
fi
options=()
[[ -n "${IMAGE_OUTPUT:-}" ]] && options+=(--image-output "$IMAGE_OUTPUT")
[[ "$cameras" == true ]] && options+=(--cameras)
[[ "${SENSORS_ONLY:-false}" == true ]] && options+=(--sensors-only)
python3 "$workspace/tools/check_flight.py" --names "${names[@]}" "${options[@]}"
