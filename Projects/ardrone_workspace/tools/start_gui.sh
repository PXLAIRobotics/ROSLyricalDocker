#!/usr/bin/env bash
# Interactive launcher for the local AR.Drone GUI. Run inside the ROS container.
set -euo pipefail
workspace=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
dry_run=false
if (( $# > 1 )); then echo "Usage: $0 [--dry-run]" >&2; exit 2; fi
case "${1:-}" in
    --dry-run) dry_run=true ;;
    --help|-h) echo "Usage: $0 [--dry-run] — select a drone and keyboard layout, then open the GUI. Ctrl+C cancels."; exit 0 ;;
    '') ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
esac

ask() {
    local answer
    read -r -p "$1 [$2]: " answer || { echo 'Input ended; launch cancelled.' >&2; exit 1; }
    REPLY=${answer:-$2}
}

echo 'AR.Drone GUI — Enter accepts each default; Ctrl+C cancels.'
while true; do
    ask 'Drone namespace (ardrone for one drone, ardrone_1 for a fleet)' ardrone
    if [[ "$REPLY" =~ ^/?[a-zA-Z_][a-zA-Z0-9_]*(/[a-zA-Z_][a-zA-Z0-9_]*)*/?$ ]]; then
        drone=$REPLY
        break
    fi
    echo 'Use a namespace such as ardrone, ardrone_2, or fleet/ardrone_1.' >&2
done
while true; do
    ask 'Keyboard layout (QWERTY/AZERTY)' QWERTY
    case "${REPLY^^}" in
        QWERTY|AZERTY) layout=${REPLY^^}; break ;;
        *) echo 'Choose QWERTY or AZERTY.' >&2 ;;
    esac
done
command=(ros2 run ardrone_control gui --drone "$drone" --layout "$layout")
printf '\n'; printf '%q ' "${command[@]}"; printf '\n'
if [[ "$dry_run" == true ]]; then exit 0; fi

source "$workspace/tools/prepare_workspace.sh"
prepare_workspace ardrone_control
exec "${command[@]}"
