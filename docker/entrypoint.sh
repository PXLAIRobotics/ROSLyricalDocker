#!/usr/bin/env bash
set -e
# Avoid RViz's missing-settings error on first launch; preserve user settings.
mkdir -p "$HOME/.rviz2"
if [[ ! -e "$HOME/.rviz2/persistent_settings" ]]; then
    cp /etc/ros-workshop-rviz-settings "$HOME/.rviz2/persistent_settings"
fi
source /etc/ros-workshop-workspaces.bash
exec "$@"
