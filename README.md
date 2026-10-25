# PXL ROS 2 Lyrical Development Environment

Ubuntu **26.04 (Resolute)** with **ROS 2 Lyrical Luth**, RViz, Gazebo Jetty,
Nav2, OpenCV, and a Python example workspace. This carries over the examples,
simulation worlds, helper commands, and mounted folder layout from
`ROS2_Development_Environment` into an independent Lyrical environment.

The desktop uses **Xfce, TigerVNC, and noVNC**. No Kasm components are used.

## Requirements

- Docker Engine (Linux) or Docker Desktop (macOS/Windows).
- Allow roughly 30 GB of free disk space and 8 GB of RAM for building and simulations.
- NVIDIA acceleration is optional and requires the host NVIDIA Container Toolkit.
- Builds use the host architecture. Cross-build with `--platform linux/amd64`
  or `--platform linux/arm64` if Docker has the required emulation configured.

## Browser desktop

From this folder:

```sh
./001_build_pxl_ros2_lyrical_image.sh
./002_run_pxl_ros2_lyrical_container.sh
```

Open [the desktop](http://localhost:6901/vnc.html?autoconnect=true&resize=remote).
Enter the default VNC password `password`; no username is required. A native VNC
client can also connect to `localhost:5901`. The launcher publishes both ports on
`127.0.0.1`. Browser access uses HTTP/WebSocket on localhost.

Customize the password, resolution, or host ports before launching:

```sh
VNC_PW=mysecret VNC_RESOLUTION=1920x1080 WEB_PORT=6902 VNC_PORT=5902 \
  ./002_run_pxl_ros2_lyrical_container.sh
```

TigerVNC's classic authentication uses the first eight password characters.
For remote access, tunnel these localhost ports through SSH.

Lifecycle commands:

```sh
./003_attach_bash_to_pxl_ros2_lyrical_container.sh
./997_stop_pxl_ros2_lyrical_container.sh
./998_remove_pxl_ros2_lyrical_container.sh
./999_remove_pxl_ros2_lyrical_image.sh
```

The container runs in the foreground and is automatically removed on exit.
The remove command is only needed for a container created without `--rm`.
The `001c`, `002c`, `003c`, `997c`, `998c`, and `999c` scripts are explicit aliases
for this same TigerVNC/browser desktop image (`pxl_ros2_lyrical_vnc:latest`).

## Native Linux graphics

The historical `novnc` suffix means **no VNC server**. This mode opens RViz,
Gazebo, and OpenCV windows on the host X11/Xwayland display:

```sh
./001b_build_pxl_ros2_lyrical_novnc_image.sh
./002b_run_pxl_ros2_lyrical_novnc_container.sh
```

Launch from a graphical Linux terminal with `DISPLAY` and a valid Xauthority
cookie. Install `xauth` on the host if necessary. The launcher checks the local
X socket and forwards a temporary authentication cookie. SSH/TCP displays are
not supported. Use the browser desktop on macOS and Windows.

The `003b`, `997b`, `998b`, and `999b` scripts attach, stop, remove the container,
and remove its image. Each mode has a distinct container name, so it can coexist
with the old Jazzy environment. Change `WEB_PORT`/`VNC_PORT` if those ports are
already occupied.

## Persistent files and ROS workspace

All launchers mount the following folders into `/home/user`:

| Host folder | Container folder | Purpose |
| --- | --- | --- |
| `Commands/bin` | `~/bin` | Workshop helpers on PATH |
| `ExampleCode` | `~/ExampleCode` | OpenCV and simulation examples |
| `Data` | `~/Data` | User data (ignored by Git) |
| `Projects` | `~/Projects` | Source workspace and build output |

Images also contain the example source workspace and helpers for use without
bind mounts. Build the workspace inside the container before running its node:

```sh
cd ~/Projects/ros2_workspace
colcon build --symlink-install
source install/setup.bash
ros2 run example_package example_node
```

Expected output: `Hi from example_package.` Newly opened interactive shells
source ROS and the workspace automatically when its install directory exists.
`clean_and_rebuild_ros2_workspace` removes this workspace's build/install/log
folders, rebuilds it, and sources the result in the current shell.

The image uses the UID/GID of the user who builds it, keeping native Linux bind
mount writes owned by that user. Build without sudo, with Docker access configured.
To build for another non-root account, pass Docker build arguments:

```sh
./001_build_pxl_ros2_lyrical_image.sh --build-arg USER_UID=1001 --build-arg USER_GID=1001
```

## AR.Drone simulation

The self-contained [AR.Drone workspace](Projects/ardrone_workspace/README.md)
supports ROS 2 single- and multi-drone flight in Gazebo Jetty, including the
recreated `summerforall`, `sternformost`, `rommel`, and `glasshouse` worlds,
plus a hillside `orchard` with detailed apple trees and one launch platform per
drone (up to 32).
It needs no extra source repositories, drone SDKs, or downloaded Gazebo models.

```sh
ros2 launch ardrone_gazebo single_ardrone.launch.py world:=summerforall
# Or: ros2 launch ardrone_gazebo multi_ardrones.launch.py count:=10 world:=orchard
# Interactive world, fleet, battery and drift settings:
~/Projects/ardrone_workspace/tools/start_sim.sh
```

The image builds this workspace upfront into `/opt/ardrone_workspace/install`
and sources it automatically. Its editable source is already part of the shared
`Projects` bind mount, just like `ros2_workspace`. Keeping the image install in
`/opt` means mounting `Projects` does not hide the prebuilt package.

After editing the source, run `colcon build --symlink-install` in
`~/Projects/ardrone_workspace` and source `install/local_setup.bash`. New shells
and container starts automatically prefer that locally built workspace. Source
edits require a local rebuild or an image rebuild to take effect.

See the workspace guide for flight commands, topics, limitations and tests.

## ROS, simulation, and graphics checks

Inside the container:

```sh
cat /etc/os-release                    # VERSION_ID=26.04
printenv ROS_DISTRO                    # lyrical
ros2 run demo_nodes_cpp talker         # Ctrl+C to stop
rviz2
gz sim
python3 -c 'import cv2; print(cv2.__version__)'
glxinfo -B
```

Use two terminals for the ROS talker/listener demo (`demo_nodes_cpp listener`
in the second). For ROS communication between separate containers or machines,
configure Docker networking and DDS discovery for your network; the launchers
use Docker's default bridge network.

The helpers `start_tugbot_racetrack2`, `start_tugbot_racetrack2_headless`, and
`start_drone_world` carry over the original simulation assets and ROS bridges.
Fuel models may require internet access on first launch. Those worlds were
originally used with Jazzy/Harmonic; their complete behavior needs checking in
Jetty before use in a workshop.

The full TurtleBot 4 package family from the Jazzy image is not published in the
Lyrical release index checked during migration. This image includes Nav2's
`nav2_minimal_tb4_description` and `nav2_minimal_tb4_sim` packages, Navigation2,
and `nav2_bringup` instead. It does not claim the full TurtleBot 4 hardware stack.

Lyrical uses the Gazebo Jetty vendor packages installed by `ros-lyrical-ros-gz`.
Do not add a separate Harmonic repository. See the upstream
[ROS/Gazebo compatibility guide](https://gazebosim.org/docs/latest/ros_installation/)
and [Lyrical release index](https://github.com/ros/rosdistro/blob/master/lyrical/distribution.yaml).
ROS repository setup uses the official
[ros-apt-source](https://github.com/ros-infrastructure/ros-apt-source) package.

## Terminal and RViz defaults

The original TigerVNC `.tmux.conf` and custom `.vimrc` are copied unchanged.
TPM installs Nord and tmux-sensible, and Vundle installs every plugin declared
in `.vimrc` during the Docker build. The build checks that all plugins exist and
that Vim loads the complete configuration successfully. No manual plugin setup
is needed after launching a container.

The Xfce terminal uses the original Cascadia Nerd Font for Powerline glyphs.
Reload tmux with `tmux source-file ~/.tmux.conf`. Vim retains the original
Gruvbox default theme, Airline status line, mappings, and plugin settings.
RViz starts with an initialized, user-writable `~/.rviz2/persistent_settings`
file; existing settings are preserved.

## GPU support

Launchers detect NVIDIA with a working Docker NVIDIA runtime and enable GPU
access. Otherwise a detected NVIDIA host uses Mesa software rendering. Intel/AMD
GPUs use `/dev/dri` when present. Browser/VNC graphics acceleration also depends
on the virtual display and driver; GPU passthrough alone does not guarantee that
Xvnc renders with hardware acceleration. Prefer native Linux graphics for GPU
heavy simulations. Use `glxinfo -B` to inspect the actual renderer.

For an apt-based Linux host with systemd, the optional setup helper installs the
NVIDIA Container Toolkit and restarts Docker (which can stop running containers):

```sh
sudo bash ./setup_nvidia_docker.sh
```

## Layout and verification

The root `Dockerfile` shares the ROS/tool installation between the `native` and
`vnc` stages. Numbered scripts resolve their own location, so they can also be
invoked from another working directory. Build scripts accept extra Docker build
arguments; run scripts accept extra Docker run arguments before the image name.

Run container-level checks after building:

```sh
./tests/smoke.sh
./tests/ardrone-image.sh  # Prebuilt workspace, bind mounts, and local overlay
```

The smoke check verifies Ubuntu/ROS versions, packages, workspace compilation,
the example node, and a local ROS talker/listener exchange. It also starts a
temporary desktop container and checks VNC and browser endpoints.

## License

See [LICENSE](LICENSE). Original example assets retain their existing attribution
and license terms. Maintained by Tim Dupont and Sam van Rijn.
