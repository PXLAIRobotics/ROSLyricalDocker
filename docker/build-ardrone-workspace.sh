#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/lyrical/setup.bash
# A normal install copies resources and Python code; symlinks would point back
# into the source bind mount (or the temporary build directory).
colcon --log-base /tmp/ardrone-image-log build \
    --base-paths /home/user/Projects/ardrone_workspace/src \
    --build-base /tmp/ardrone-image-build \
    --install-base /opt/ardrone_workspace/install
source /opt/ardrone_workspace/install/local_setup.bash
ros2 pkg prefix ardrone_gazebo
python3 -c 'from ardrone_gazebo.simulation import build_world'
rm -rf /tmp/ardrone-image-build /tmp/ardrone-image-log
