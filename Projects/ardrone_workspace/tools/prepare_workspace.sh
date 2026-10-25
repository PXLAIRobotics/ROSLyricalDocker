#!/usr/bin/env bash
# Shared by the interactive launchers; workspace is set by the caller.
source_ros_setup() {
    # ROS setup scripts may read unset variables.
    set +u
    source "$1"
    set -u
}

source_local_workspace() {
    # Colcon's prepend-non-duplicate hooks do not move existing entries. Remove
    # this overlay's old entries before sourcing it so it wins over the image,
    # including in shells which already sourced both workspaces.
    local variable entry value
    local -a entries
    for variable in AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH PATH LD_LIBRARY_PATH; do
        value=''
        IFS=: read -r -a entries <<< "${!variable:-}"
        for entry in "${entries[@]}"; do
            case "$entry" in
                "$workspace/install"|"$workspace/install/"*|"$workspace/build"|"$workspace/build/"*) continue ;;
            esac
            [[ -n "$entry" ]] && value="${value:+$value:}$entry"
        done
        export "$variable=$value"
    done
    # Underlays have already been sourced; do not replay a recorded chain.
    source_ros_setup "$workspace/install/local_setup.bash"
}

prepare_workspace() {
    local package=$1 source_dir="$workspace/src/$1"
    local stamp="$workspace/build/.launcher-$1.sha256" fingerprint previous=''
    local ros_setup="/opt/ros/${ROS_DISTRO:-lyrical}/setup.bash"
    if [[ -f "$ros_setup" ]]; then
        source_ros_setup "$ros_setup"
    fi
    if [[ -f /opt/ardrone_workspace/install/setup.bash ]]; then
        source_ros_setup /opt/ardrone_workspace/install/setup.bash
    fi
    if [[ -f "$workspace/install/local_setup.bash" ]]; then
        source_local_workspace
    fi
    command -v ros2 >/dev/null || {
        echo 'Run this script inside the ROS container with ROS installed.' >&2
        return 1
    }
    if [[ -f "$source_dir/package.xml" ]]; then
        # Hash paths and contents to detect edits, additions and deletions, even
        # when symlink-install already exposes some changes without a build.
        fingerprint=$(python3 - "$source_dir" <<'PY'
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1])
digest = hashlib.sha256()
for path in sorted(root.rglob('*')):
    relative = path.relative_to(root)
    if any(part in {'__pycache__', '.pytest_cache', '.git'} or
           part.endswith('.egg-info') for part in relative.parts):
        continue
    if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
        digest.update(str(relative).encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
print(digest.hexdigest())
PY
        )
        if [[ -f "$stamp" ]]; then previous=$(cat "$stamp"); fi
        if [[ "$fingerprint" != "$previous" ||
              ! -f "$workspace/install/local_setup.bash" ||
              ! -f "$workspace/install/$package/share/$package/package.xml" ]] ||
              ! ros2 pkg prefix "$package" >/dev/null 2>&1; then
            command -v colcon >/dev/null || {
                echo "Building $package requires colcon; run inside the ROS container." >&2
                return 1
            }
            echo "Building $package in $workspace…"
            # Record only successful builds; failures must stop the launch.
            (cd "$workspace" && colcon build --symlink-install --packages-select "$package") || return 1
            source_local_workspace
            mkdir -p "$workspace/build"
            printf '%s\n' "$fingerprint" > "$stamp"
        fi
        local selected_prefix
        selected_prefix=$(ros2 pkg prefix "$package")
        if [[ "$selected_prefix" != "$workspace/install/$package" ]]; then
            echo "Expected local $package, but ROS selected $selected_prefix; refusing to launch stale code." >&2
            return 1
        fi
        echo "Using $package from $selected_prefix"
    fi
    if ! ros2 pkg prefix "$package" >/dev/null 2>&1; then
        echo "Package $package is unavailable. Add its sources under $source_dir and rerun." >&2
        return 1
    fi
}
