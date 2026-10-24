#!/usr/bin/env bash
# Verify image-installed packages survive Projects mounts and local builds win.
set -euo pipefail
image=${1:-pxl_ros2_lyrical_vnc:latest}
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
empty_projects=$(mktemp -d)
trap 'rmdir "$empty_projects"' EXIT
for projects in "$root/Projects" "$empty_projects"; do
    docker run --rm -v "$projects:/home/user/Projects:ro" "$image" bash -c '
        set -e
        test "$(ros2 pkg prefix ardrone_gazebo)" = /opt/ardrone_workspace/install/ardrone_gazebo
        python3 -c "from pathlib import Path; from ament_index_python.packages import get_package_share_directory; from ardrone_gazebo.simulation import build_world; print(len(build_world(Path(get_package_share_directory(\"ardrone_gazebo\"))/\"worlds\", \"glasshouse\", [\"ardrone\"])))"
        ros2 launch ardrone_gazebo single_ardrone.launch.py --show-args >/dev/null
        bash -ic '\''test "$(ros2 pkg prefix ardrone_gazebo)" = /opt/ardrone_workspace/install/ardrone_gazebo'\''
    '
done
docker run --rm "$image" bash -c '
    set -eo pipefail
    cd "$HOME/Projects/ardrone_workspace"
    colcon build --symlink-install
    /usr/local/bin/ros-entrypoint bash -c '\''test "$(ros2 pkg prefix ardrone_gazebo)" = "$HOME/Projects/ardrone_workspace/install/ardrone_gazebo"'\''
    bash -ic '\''test "$(ros2 pkg prefix ardrone_gazebo)" = "$HOME/Projects/ardrone_workspace/install/ardrone_gazebo"'\''
'
echo 'Prebuilt AR.Drone works with mounted or hidden sources; local builds take precedence.'
