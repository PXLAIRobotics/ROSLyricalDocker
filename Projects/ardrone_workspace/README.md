# AR.Drone simulation for ROS 2 Lyrical / Gazebo Jetty

A self-contained simulation workspace for one or many AR.Drone-style quadrotors.
It replaces the Noetic/Gazebo Classic plugins with Jetty's multicopter motor and
velocity-control systems plus a small ROS 2 flight-state controller. No Git
clones, Fuel downloads, `ardrone_autonomy`, `ardronelib`, PX4, or hardware SDKs
are needed to build or run. Standard ROS 2 and Gazebo dependencies are provided
by this repository's Docker image.

## Build and launch

Building the Docker image also builds this package into
`/opt/ardrone_workspace/install`. Container startup and interactive shells source
it automatically, so a newly built image can launch immediately:

```bash
ros2 launch ardrone_gazebo single_ardrone.launch.py
```

The editable workspace is already mounted at `~/Projects/ardrone_workspace` by
the launchers' shared `Projects` bind mount. The prebuilt install lives outside
that mount so it stays available even when the host has no build output.

To use source edits, or use an older image without the prebuilt package:

```bash
cd ~/Projects/ardrone_workspace
colcon build --symlink-install
source install/local_setup.bash
```

New shells and container starts automatically prefer this local build when it
exists. Source edits are not automatically compiled at startup; rebuild locally
or rebuild the image to apply them. The image's prebuilt copy is used when there
is no local install. Build outputs in the mounted workspace persist on the host.

```bash
# Two drones (ardrone_1 and ardrone_2)
ros2 launch ardrone_gazebo multi_ardrones.launch.py

# Four drones on the original Summer For All floor map
ros2 launch ardrone_gazebo multi_ardrones.launch.py count:=4 world:=summerforall

# Ten drones, without a GUI or camera rendering
ros2 launch ardrone_gazebo ten_ardrones.launch.py gui:=false cameras:=false
```

`two_ardrones.launch.py`, `four_ardrones.launch.py`, and `ten_ardrones.launch.py`
are convenient presets. Every launch accepts:

| Argument | Default | Meaning |
| --- | --- | --- |
| `count` | 1 single / 2 multi | 1–32 independently controlled drones |
| `name` | `ardrone` | Single namespace, or prefix for `name_1`, `name_2`, … |
| `world` | `empty` | `empty`, `summerforall`, `sternformost`, `rommel`, `glasshouse` |
| `spacing` | `1.5` | Spawn-grid spacing in metres; minimum 0.7 |
| `gui` | `true` | Set false for headless Gazebo |
| `cameras` | `true` | Set false to omit rendering and camera bridges |
| `takeoff_height` | `1.0` | Target metres above launch surface |
| `command_timeout` | `0.5` | Simulation seconds without commands before hover |

Headless cameras use EGL; software rendering is supported where Mesa provides
EGL. Large fleets with cameras need substantially more CPU/GPU resources.
Run one launch per ROS domain/Gazebo partition; for independent simultaneous
simulations set different `ROS_DOMAIN_ID` and `GZ_PARTITION` values.

## Fly a drone

From another container terminal:

```bash
source ~/Projects/ardrone_workspace/install/setup.bash
ros2 topic pub --once /ardrone/takeoff std_msgs/msg/Empty '{}'
# Wait until state is flying, then command forward motion (metres/second):
ros2 topic pub -r 10 /ardrone/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.4}}'
# Ctrl+C stops commands; the drone slows to a hover after 0.5 simulation seconds.
ros2 topic pub --once /ardrone/land std_msgs/msg/Empty '{}'
```

For a fleet, replace `/ardrone` with `/ardrone_1`, `/ardrone_2`, etc.
`linear.x` is forward, `linear.y` left, `linear.z` up, and `angular.z` positive
counterclockwise in the body frame. Units are m/s and rad/s, not the real
AR.Drone SDK's normalized commands. Limits are ±2 m/s horizontally, ±1 m/s
vertically, and ±1.5 rad/s yaw. Roll/pitch command fields are ignored.

`reset` is an emergency motor stop: an airborne drone falls. It does not teleport
or reset the world. Takeoff becomes available after the drone reaches its launch
floor height again. Restart the simulation after an overturned crash.
Landing targets the launch surface height; arbitrary raised-platform landing and
obstacle avoidance are not implemented. Do not use simulation commands to drive
real hardware.

## ROS interfaces (under each drone namespace)

| Topic | Message | Direction / purpose |
| --- | --- | --- |
| `takeoff`, `land`, `reset` | `std_msgs/msg/Empty` | Commands |
| `cmd_vel` | `geometry_msgs/msg/Twist` | Body velocity command |
| `state` | `std_msgs/msg/String` | `landed`, `taking_off`, `flying`, `landing`, `emergency` |
| `odom` | `nav_msgs/msg/Odometry` | Gazebo ground-truth pose and velocity |
| `imu` | `sensor_msgs/msg/Imu` | Simulated IMU at 100 Hz |
| `front_camera/image_raw`, `bottom_camera/image_raw` | `sensor_msgs/msg/Image` | 320×240 RGB, 15 Hz |
| `front_camera/camera_info`, `bottom_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | Calibration |
| `sim/cmd_vel`, `sim/enable` | `Twist`, `Bool` | Internal controller/bridge interface |

There is one shared `/clock`. All controllers use simulation time, so pausing
Gazebo pauses command expiry. TF uses a shared `world` and unique
`ardrone[_N]/base_link` and camera optical frames. Odometry and sensor frame IDs
are also unique. Camera optical frames use ROS conventions (z forward, x right,
y down). The `world` frame can be selected as RViz's fixed frame.

This is a new simulation interface, not a drop-in ROS 1 `Navdata` API. Hardware
networking, battery emulation, legacy position-control modes, sonar, and real-drone
control are outside this initial port. The locally authored airframe resembles
an AR.Drone with four protective rims; its dimensions, mass, inertia and motor
parameters are approximate, not a calibrated hardware model. Physics uses real
thrust, torque, gravity, collisions and spinning rotor joints.

## Recreated Noetic worlds

The original ROSNoeticDocker floor artwork is bundled locally and uses Jetty PBR
materials instead of Gazebo Classic material scripts. Map dimensions and poses
are preserved. These maps are flat textured planes, including `glasshouse`;
they were not 3D buildings in the source repository.

`rommel` retains the floor and all 50 scenery model positions. Its external
Gazebo mesh visuals are recreated with primitive collision shapes; mesh-only
collisions use simple local box approximations. Scenery, including the old
TurtleBot/rover props, is static and is not a second simulated robot stack.
The obsolete `rommel_old.world` snapshot is not a separate launch option.
See [PROVENANCE.md](src/ardrone_gazebo/PROVENANCE.md) for source revisions and asset terms.

`tools/import_noetic_worlds.py /path/to/ROSNoeticDocker` regenerates the checked-in
worlds from a source checkout. This is a maintainer tool, never a runtime step.

## Verification

Inside the container, after building and sourcing the workspace:

```bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
# Two-drone flight, isolation, IMU and state transitions:
tools/smoke.sh empty 2 false
# Single-drone flight plus both camera streams and calibration:
tools/smoke.sh summerforall 1 true
# Sensor/startup check for other worlds or larger fleets:
SENSORS_ONLY=true tools/smoke.sh rommel 4 true
```

From the repository root on the host, `./tests/ardrone.sh [world] [count] [cameras]`
builds and tests in a temporary Docker container, with read-only sources and
disposable build directories. `ARDRONE_TEST_IMAGE` overrides
the default `pxl_ros2_lyrical_novnc:latest` image. Tests run in a separate ROS domain
and Gazebo partition. The integration check exercises takeoff, translation, yaw,
command timeout, independent control, landing, repeat takeoff and emergency stop.

### Validation in the supplied Lyrical image

The package builds and all 19 unit tests pass. Live tests covered single- and
two-drone takeoff, translation, yaw, hover timeout, landing and emergency stop;
four-drone camera/IMU/odometry streams; and ten-drone IMU/odometry startup.
All four recreated worlds loaded, and floor artwork was checked in rendered
camera images. The host test runner also completed with read-only sources.

One remaining issue was observed in the image's installed `ros_gz_bridge`:
it sometimes exits with SIGSEGV (`exit code -11`) when the launch is shut down.
Flight and sensor checks complete before this happens, and the simulator and
workspace controllers exit cleanly. The test runner reports functional test
results and prints shutdown logs; it does not count this bridge cleanup crash
as a flight-test failure. This port does not patch the installed bridge binary.
