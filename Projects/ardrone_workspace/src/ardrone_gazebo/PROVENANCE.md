# Sources and asset provenance

This ROS 2 implementation was written for ROSLyricalDocker. New Python code,
launch files and primitive drone geometry use the repository's MIT license.

Behavioral reference:

- https://github.com/PXLRoboticsLab/ardrone_gazebo
- Inspected revision: `6beb80fa97298581c868124fef2a64ae6d69f01a`
- No ROS 1 plugin code or drone meshes are copied. The reference package declares
  its license as `TODO` and contains no root license file.

World layout and floor artwork source:

- https://github.com/PXLAIRobotics/ROSNoeticDocker
- Inspected revision: `a6cb13fc3b5340f199fb3f0d803eafcf5f791176`
- `Projects/catkin_ws_src/summerforall/worlds/summerforall.world`
- `Projects/catkin_ws_src/sternformost/worlds/{sternformost,rommel}.world`
- `Projects/catkin_ws_src/pxl_drones_week/worlds/glasshouse.world`
- Floor PNGs from the corresponding packages' `models/*/materials/textures/`.

Floor PNGs are retained unchanged. Generated world geometry preserves layout
facts (poses and dimensions); external scenery meshes are replaced by local
primitive geometry. The conversion script records how the worlds are recreated.
Gazebo Classic plugins, saved simulation state, OGRE material scripts, and
absolute Noetic installation paths are not carried over.

The source world packages do not provide a usable asset license declaration.
Their original artwork is not relicensed under this repository's MIT license;
its original rights remain with its authors. Confirm artwork redistribution
terms with the source maintainers before distributing it under a new license.

Implementation references:

- Gazebo Jetty's installed `multicopter_velocity_control.sdf` example and API:
  https://gazebosim.org/api/sim/10/classgz_1_1sim_1_1systems_1_1MulticopterVelocityControl.html
- Standard ROS/Gazebo bridge supplied by `ros-lyrical-ros-gz`.
