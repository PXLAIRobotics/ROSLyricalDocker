#!/usr/bin/env bash
set -euo pipefail
source /etc/os-release
[[ "$VERSION_ID" == 26.04 ]] || { echo "Ubuntu 26.04 is required" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg locales software-properties-common
add-apt-repository -y universe
# The official ROS apt-source package manages repository keys and configuration.
curl -fL --retry 3 "https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.3.0/ros2-apt-source_1.3.0.${VERSION_CODENAME}_all.deb" -o /tmp/ros2-apt-source.deb
dpkg -i /tmp/ros2-apt-source.deb
rm /tmp/ros2-apt-source.deb
apt-get update
apt-get install -y --no-install-recommends \
    ros-dev-tools ros-lyrical-desktop ros-lyrical-ros-gz \
    ros-lyrical-navigation2 ros-lyrical-nav2-bringup \
    ros-lyrical-nav2-minimal-tb4-description ros-lyrical-nav2-minimal-tb4-sim \
    ros-lyrical-topic-tools ros-lyrical-teleop-twist-keyboard \
    python3-opencv python3-pyqt5 python3-pip python-is-python3 libopencv-dev \
    git vim nano tmux htop sudo wget bash-completion universal-ctags \
    mesa-utils libgl1-mesa-dri iputils-ping xauth
rm -rf /var/lib/apt/lists/*
