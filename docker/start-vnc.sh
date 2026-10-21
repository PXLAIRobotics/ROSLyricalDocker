#!/usr/bin/env bash
set -euo pipefail
# One D-Bus session for the X server and desktop; tini reaps orphan processes.
if [[ "${1:-}" != --session ]]; then
    exec dbus-run-session -- "$0" --session
fi
export DISPLAY=:1
export XDG_RUNTIME_DIR="/tmp/runtime-$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR" "$HOME/.vnc"
chmod 700 "$XDG_RUNTIME_DIR" "$HOME/.vnc"
printf '%s\n' "${VNC_PW:-password}" | tigervncpasswd -f > "$HOME/.vnc/passwd"
chmod 600 "$HOME/.vnc/passwd"
# Both endpoints are published only on the host loopback interface by the launcher.
Xtigervnc :1 -rfbport 5901 -localhost no -SecurityTypes VncAuth \
    -PasswordFile "$HOME/.vnc/passwd" -geometry "${VNC_RESOLUTION:-1280x800}" -depth 24 &
vnc_pid=$!
cleanup() {
    kill "$vnc_pid" "${desktop_pid:-}" "${web_pid:-}" 2>/dev/null || true
    wait || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
# Wait for X before starting clients.
for attempt in {1..50}; do
    if xdpyinfo >/dev/null 2>&1; then break; fi
    kill -0 "$vnc_pid" 2>/dev/null || { echo "VNC server failed" >&2; exit 1; }
    sleep 0.1
done
xdpyinfo >/dev/null
startxfce4 &
desktop_pid=$!
websockify --web=/usr/share/novnc/ 6901 localhost:5901 &
web_pid=$!
wait -n "$vnc_pid" "$desktop_pid" "$web_pid"
