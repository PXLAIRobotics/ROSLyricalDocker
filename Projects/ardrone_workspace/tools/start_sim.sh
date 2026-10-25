#!/usr/bin/env bash
# Interactive simulator launcher. Run inside the ROS container.
set -euo pipefail
workspace=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
dry_run=false
case "${1:-}" in
    --dry-run) dry_run=true ;;
    --help|-h) echo "Usage: $0 [--dry-run] — ask for simulation settings, then launch. Ctrl+C cancels."; exit 0 ;;
    '') ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
esac

ask() {
    local prompt=$1 fallback=$2 answer
    read -r -p "$prompt [$fallback]: " answer || { echo 'Input ended; launch cancelled.' >&2; exit 1; }
    REPLY=${answer:-$fallback}
}
number() {
    local prompt=$1 fallback=$2 minimum=$3 maximum=$4
    while true; do
        ask "$prompt" "$fallback"
        if python3 - "$REPLY" "$minimum" "$maximum" <<'PY'
import math, sys
try:
    v, low, high = map(float, sys.argv[1:])
    valid = math.isfinite(v) and low <= v <= high
except ValueError:
    valid = False
sys.exit(0 if valid else 1)
PY
        then return; fi
        echo "Enter a finite number between $minimum and $maximum." >&2
    done
}
yesno() {
    while true; do
        ask "$1 (yes/no)" "$2"
        case "${REPLY,,}" in
            y|yes|true) REPLY=true; return ;;
            n|no|false) REPLY=false; return ;;
            *) echo 'Enter yes or no.' >&2 ;;
        esac
    done
}

echo 'AR.Drone simulation — Enter accepts each default; Ctrl+C cancels.'
while true; do
    ask 'World (empty, summerforall, sternformost, rommel, glasshouse, orchard)' empty
    case "$REPLY" in empty|summerforall|sternformost|rommel|glasshouse|orchard) world=$REPLY; break ;; esac
    echo 'Choose a world from the list.' >&2
done
while true; do
    ask 'Number of drones (1–32)' 1
    if [[ "$REPLY" =~ ^([1-9]|[12][0-9]|3[0-2])$ ]]; then count=$REPLY; break; fi
    echo 'Enter an integer from 1 to 32.' >&2
done
yesno 'Show Gazebo window' yes; gui=$REPLY
yesno 'Enable cameras' yes; cameras=$REPLY
number 'Full battery flight time (minutes)' "${ARDRONE_FLIGHT_TIME_MINUTES:-30}" .001 1000000
export ARDRONE_FLIGHT_TIME_MINUTES=$REPLY
number 'Empty-to-full recharge time (seconds)' "${ARDRONE_RECHARGE_TIME_SECONDS:-30}" .001 1000000
export ARDRONE_RECHARGE_TIME_SECONDS=$REPLY
yesno 'Enable drifting and wind-like disturbances' no; disturbances=$REPLY
drift_speed=.08; wind_x=.1; wind_y=0.
if [[ "$disturbances" == true ]]; then
    number 'Maximum drift per axis (m/s; 0 disables drift)' .08 0 .5; drift_speed=$REPLY
    number 'Wind-like bias along world X (m/s)' .1 -.5 .5; wind_x=$REPLY
    number 'Wind-like bias along world Y (m/s)' 0 -.5 .5; wind_y=$REPLY
fi
command=(ros2 launch ardrone_gazebo multi_ardrones.launch.py
    "count:=$count" "world:=$world" "gui:=$gui" "cameras:=$cameras"
    "disturbances:=$disturbances" "drift_speed:=$drift_speed" "wind_x:=$wind_x" "wind_y:=$wind_y")
printf '\nARDRONE_FLIGHT_TIME_MINUTES=%q ARDRONE_RECHARGE_TIME_SECONDS=%q ' "$ARDRONE_FLIGHT_TIME_MINUTES" "$ARDRONE_RECHARGE_TIME_SECONDS"
printf '%q ' "${command[@]}"
printf '\n'
if [[ "$dry_run" == true ]]; then exit 0; fi
source "$workspace/tools/prepare_workspace.sh"
prepare_workspace ardrone_gazebo
exec "${command[@]}"
