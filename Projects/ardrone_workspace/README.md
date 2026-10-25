# AR.Drone simulation for ROS 2 Lyrical / Gazebo Jetty

A self-contained simulation workspace for one or many AR.Drone quadrotors.
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
| `world` | `empty` | `empty`, `summerforall`, `sternformost`, `rommel`, `glasshouse`, `orchard` |
| `spacing` | `1.5` | Spawn-grid spacing in metres; minimum 0.7 (1.2 for orchard) |
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

## Interactive startup and disturbances

Gazebo starts with the Entity Tree and Component Inspector side panels closed,
and without the shape and light creation toolbars. Translation and rotation
controls remain at the top-left. Reopen either side panel from Gazebo's top-right
plugin menu; right-click its panel and select **Close** to hide it again.
All drone launches use the bundled `ardrone_gazebo/config/gui.config` layout,
so the side panels start closed again on the next launch.

Inside the container, run:

```bash
~/Projects/ardrone_workspace/tools/start_sim.sh
```

The launcher asks for world, drone count, Gazebo window, cameras, flight time,
recharge time, and whether to enable drift/wind. Enter accepts the displayed
default; Ctrl+C cancels. Battery defaults respect existing environment variables.
Use `tools/start_sim.sh --dry-run` to answer the questions and print the command
without building or starting Gazebo. Before a normal launch, it sources ROS,
builds the local `ardrone_gazebo` package if needed, and sources the workspace.
The first launch builds once; subsequent launches rebuild when package sources
change or the local install is missing. Build failures stop the launch.
The launchers put the local workspace ahead of the image's prebuilt packages
and print the selected package path. Source edits do not require rebuilding
the Docker image.

Disturbances are **off by default**, and available with every launch preset:

```bash
ros2 launch ardrone_gazebo single_ardrone.launch.py disturbances:=true
ros2 launch ardrone_gazebo multi_ardrones.launch.py count:=4 disturbances:=true \
  drift_speed:=0.08 wind_x:=0.1 wind_y:=0.0
```

| Startup argument | Default | Meaning |
| --- | --- | --- |
| `disturbances` | `false` | Enable horizontal hover drift and wind-like bias |
| `drift_speed` | `0.08` | Maximum varying drift on each world axis, m/s; range 0–0.5 |
| `wind_x`, `wind_y` | `0.1`, `0.0` | Constant world-axis velocity biases, m/s; each −0.5–0.5 |

Set both wind components to zero for drift only, or `drift_speed:=0` for a
steady wind-like push. The shared wind direction stays fixed in the world when
a drone turns; each drone has a separate, reproducible smooth drift pattern.
These settings are also startup ROS parameters on each flight controller.

This is a training approximation that adds a bounded horizontal velocity bias
to the physics controller, not an aerodynamic wind-force or turbulence model.
It affects actual Gazebo motion and camera/odometry observations. Hover (including
command timeout) can drift, requiring corrective pilot or position-controller
commands. Disturbances apply only in `flying` with fresh odometry: takeoff,
manual/low-battery landing, ground, and emergency states have no added bias.
Vertical/yaw commands are unchanged, and horizontal commands retain their limits.
Patterns use simulation time: pausing freezes them and rewinding repeats them.

The older [SJTU simulator used by the Noetic port](https://github.com/NovoG93/sjtu_drone)
also exposes motion-noise/drift settings. This implementation is standalone and
adds no external repositories or dependencies.

The optional local GUI has a matching launcher:

```bash
~/Projects/ardrone_workspace/tools/start_gui.sh
```

It asks for the drone namespace and QWERTY/AZERTY layout, then opens the GUI.
Use `ardrone` for a single drone or `ardrone_1` etc. for a fleet. It requires the
local `ardrone_control` sources (excluded from Git), or an existing installed
package. Like the simulator launcher, it builds its local package when needed
and sources the workspace before launching.
Add `--dry-run` to print the command without building or starting the GUI.

## Simulated battery

Each drone controller owns an independent battery, initially at 100%. The GUI
only reads ROS telemetry; closing or switching the GUI does not reset charge.
Linear discharge starts at takeoff, continues through landing, and stops when
landed. Takeoff is refused below 20% or while charging. At 3% or below the controller automatically requests a controlled landing.
Discharge continues during descent; if it reaches 0%, a simulation reserve
permits the landing to finish.

Set these environment variables **in the terminal launching the simulation**:

```bash
export ARDRONE_FLIGHT_TIME_MINUTES=30      # full battery flight time; default 30
export ARDRONE_RECHARGE_TIME_SECONDS=30    # empty-to-full charging time; default 30
ros2 launch ardrone_gazebo single_ardrone.launch.py
```

Both must be finite and positive. Each controller also accepts the corresponding
ROS parameters `flight_time_minutes` and `recharge_time_seconds` at startup.
Discharge and charging use simulation time, so pausing Gazebo pauses both.
Charge survives land/takeoff cycles and clock resets; restarting the controller
starts a new full battery. Voltage and physical capacity are unknown (NaN).

Call the namespaced `std_srvs/srv/Trigger` service to recharge:

```bash
ros2 service call /ardrone/recharge std_srvs/srv/Trigger '{}'
```

The drone must be landed and settled with fresh odometry. Charging increases
battery telemetry gradually at a constant rate; a partially full battery takes
proportionally less time. The service returns success only when full. Invalid or
duplicate requests return failure immediately. Losing ground confirmation stops
charging and returns failure. Clients should call asynchronously so their UI
keeps displaying telemetry. Charging continues if a GUI disconnects.

## ROS interfaces (under each drone namespace)

| Topic | Message | Direction / purpose |
| --- | --- | --- |
| `takeoff`, `land`, `reset` | `std_msgs/msg/Empty` | Commands |
| `cmd_vel` | `geometry_msgs/msg/Twist` | Body velocity command |
| `state` | `std_msgs/msg/String` | `landed`, `taking_off`, `flying`, `landing`, `emergency` |
| `battery` | `sensor_msgs/msg/BatteryState` | Charge fraction (0–1) and charging status at 5 Hz |
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
networking, legacy position-control modes, sonar, and real-drone
control are outside this initial port. The visual model is the original bundled AR.Drone COLLADA mesh, with its embedded
materials and scale. Lightweight invisible collision shapes and the tested ROS 2
flight dynamics are retained; mass, inertia and motor parameters are approximate,
not a calibrated hardware model. Physics uses thrust, torque, gravity, collisions
and spinning rotor joints. The original mesh contains fixed propeller visuals;
the physics rotor joints do not add duplicate visible blades.

## Hillside orchard

`orchard` is an original, self-contained outdoor world: an 8° grassy hillside,
8 rows of 10 three-dimensional apple trees with tapered, branching trunks and irregular crowns made from
individual folded leaves, and a stone wall along the crest. Each tree
has 12 visible apples: green (unripe), yellow (turning), orange-red (blushing),
and red (ripe), with lobed/dimpled shapes, approximately 6–9 cm diameters, slender
2.2 cm stems, and varied positions partly tucked into the foliage. All four stages appear
on each tree. Ripeness is static visual variation, not a time-based growth
simulation or a calibrated color classifier.

Terrain, tree trunks/canopies, wall and platforms have collision geometry.
Individual apples, stems and small branches are visual details. Three reusable procedural tree meshes provide varied bark ridges, branch/twig
structure, individual leaf blades, veins and shaded undersides. Simplified
invisible colliders keep physics cheaper than the rendered foliage. These
remain procedural simulation assets rather than photogrammetry scans.

```bash
ros2 launch ardrone_gazebo single_ardrone.launch.py world:=orchard
ros2 launch ardrone_gazebo multi_ardrones.launch.py world:=orchard count:=10
# Largest fleet; omit camera rendering to reduce load:
ros2 launch ardrone_gazebo multi_ardrones.launch.py world:=orchard count:=32 cameras:=false
```

The flat gravel launch area is generated for the selected fleet. **One drone
creates one platform; ten drones create ten platforms**, up to 32. Each 0.95 m
square raised platform has a gold landing surface and white H. Drones spawn
centered above their own platform, facing the orchard (+world X). Platforms
are named `landing_platform_01`, `landing_platform_02`, etc. The grid extends
away from the hill; the gravel area grows with the grid. `spacing` sets center
distance and must be at least 1.2 m in this world (default 1.5 m).

Takeoff height is relative to the platform. Landing still descends vertically
to the original launch height; it does **not** navigate back to a platform or
follow terrain. Fly back above a platform before landing. Rows extend roughly
from x=11 to x=38 m and the crest rises about 4.5 m above the launch ground;
trees extend up to about 3.7 m above the slope, so climb for clearance when approaching uphill. Automatic obstacle avoidance and
terrain-following flight are not implemented.

All geometry is bundled or generated locally, without Fuel or external assets.
The three tree meshes and four apple meshes are reused throughout the orchard.
Regenerate them with `python3 -m ardrone_gazebo.orchard_assets src/ardrone_gazebo/meshes`.
Regenerate the static landscape after editing `ardrone_gazebo/orchard.py` with
`python3 -m ardrone_gazebo.orchard > src/ardrone_gazebo/worlds/orchard.sdf`
from a sourced workspace. Platforms are generated separately at launch time.

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
# Orchard platform spawning and takeoff/landing with 1, 10 and 32 drones:
python3 tools/check_orchard.py
# Calm/disturbed hover comparison and landing with real physics:
python3 tools/check_disturbance.py
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

The package builds and its unit tests cover flight, worlds and battery behavior. Live tests covered single- and
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
