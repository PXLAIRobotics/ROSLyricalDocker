# Shared by the entrypoint and interactive shells, including docker exec shells.
source /opt/ros/lyrical/setup.bash
if [[ -f "$HOME/Projects/ros2_workspace/install/local_setup.bash" ]]; then
    source "$HOME/Projects/ros2_workspace/install/local_setup.bash"
fi
# Prefer a user-built overlay; otherwise use the image's standalone install.
if [[ -f "$HOME/Projects/ardrone_workspace/install/local_setup.bash" ]]; then
    source "$HOME/Projects/ardrone_workspace/install/local_setup.bash"
elif [[ -f /opt/ardrone_workspace/install/local_setup.bash ]]; then
    source /opt/ardrone_workspace/install/local_setup.bash
fi
