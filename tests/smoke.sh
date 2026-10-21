#!/usr/bin/env bash
set -euo pipefail
image=${1:-pxl_ros2_lyrical_vnc:latest}
docker run --rm "$image" bash -c '
    set -eo pipefail
    source /etc/os-release
    test "$VERSION_ID" = 26.04
    test "$ROS_DISTRO" = lyrical
    python3 -c "import cv2; import rclpy"
    test -w "$HOME/.rviz2/persistent_settings"
    tmux -L smoke new-session -d -s smoke
    test -f "$HOME/.tmux/plugins/tmux/nord.tmux"
    test -f "$HOME/.tmux/plugins/tmux-sensible/sensible.tmux"
    test "$(tmux -L smoke show-options -gv @plugin)" = "nordtheme/tmux"
    tmux -L smoke kill-server
    vim -Nu "$HOME/.vimrc" -n -es -c "qall!"
    ros2 pkg prefix rviz2
    ros2 pkg prefix ros_gz_bridge
    ros2 pkg prefix nav2_minimal_tb4_sim
    cd "$HOME/Projects/ros2_workspace"
    colcon build --symlink-install
    source install/setup.bash
    ros2 run example_package example_node | grep -F "Hi from example_package."
    ros2 run demo_nodes_cpp talker >/tmp/talker.log 2>&1 &
    talker_pid=$!
    trap '\''kill "$talker_pid" 2>/dev/null || true'\'' EXIT
    timeout 20 ros2 run demo_nodes_cpp listener >/tmp/listener.log 2>&1 || test "$?" -eq 124
    grep -F "I heard:" /tmp/listener.log
'
container=$(docker run -d --rm "$image")
cleanup() { docker stop -t 5 "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT
for attempt in {1..60}; do
    if docker exec "$container" python3 -c '
import socket, urllib.request
with socket.create_connection(("localhost", 5901), timeout=2) as s:
    assert s.recv(12).startswith(b"RFB ")
assert urllib.request.urlopen("http://localhost:6901/vnc.html", timeout=2).status == 200
with socket.create_connection(("localhost", 6901), timeout=2) as s:
    s.sendall(b"GET /websockify HTTP/1.1\r\nHost: localhost:6901\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n")
    response = s.recv(4096)
    assert b"101 Switching Protocols" in response, response
' 2>/dev/null && docker exec "$container" pgrep -x xfce4-session >/dev/null; then
        docker exec "$container" bash -c '
            export DISPLAY=:1 XDG_RUNTIME_DIR="/tmp/runtime-$(id -u)"
            source /opt/ros/lyrical/setup.bash
            timeout -s INT 8 rviz2 >/tmp/rviz-smoke.log 2>&1
            result=$?
            cat /tmp/rviz-smoke.log
            test "$result" -eq 124 || exit 1
            ! grep -F "Could not open file:" /tmp/rviz-smoke.log
        '
        echo 'ROS workspace, DDS, tmux, RViz, VNC, and browser checks passed.'
        exit 0
    fi
    sleep 1
done
docker logs "$container"
exit 1
