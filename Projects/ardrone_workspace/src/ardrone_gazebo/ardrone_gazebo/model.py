"""Original AR.Drone visual mesh with local collision and rotor physics."""
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def element(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, tag, attrs)
    if text is not None:
        node.text = str(text)
    return node


def plugin(parent, library, name, **params):
    node = element(parent, 'plugin', filename=f'gz-sim-{library}-system',
                   name=f'gz::sim::systems::{name}')
    for key, value in params.items():
        element(node, key, value)
    return node


def shape(parent, name, geometry, size, pose='0 0 0 0 0 0',
          color='0.12 0.12 0.14 1', collision=True, visual=True):
    for kind in ('visual', 'collision'):
        if (kind == 'visual' and not visual) or (kind == 'collision' and not collision):
            continue
        node = element(parent, kind, name=name)
        element(node, 'pose', pose)
        geom = element(element(node, 'geometry'), geometry)
        if geometry == 'box':
            element(geom, 'size', size)
        else:
            radius, length = size.split()
            element(geom, 'radius', radius)
            element(geom, 'length', length)
        if kind == 'visual':
            mat = element(node, 'material')
            element(mat, 'ambient', color)
            element(mat, 'diffuse', color)


def inertia(link, mass, diagonal):
    inertial = element(link, 'inertial')
    element(inertial, 'mass', mass)
    tensor = element(inertial, 'inertia')
    for key, value in zip(('ixx', 'iyy', 'izz'), diagonal):
        element(tensor, key, value)
    for key in ('ixy', 'ixz', 'iyz'):
        element(tensor, key, 0)


def drone(name, x, y, cameras=True, mesh_path=None):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
        raise ValueError('Drone name must start with a letter and contain letters, digits or _.')
    model = ET.Element('model', name=name)
    element(model, 'pose', f'{x} {y} 0.09 0 0 0')
    base = element(model, 'link', name='base_link')
    inertia(base, 0.42, (0.0023, 0.0023, 0.004))
    if mesh_path is None:
        from ament_index_python.packages import get_package_share_directory
        mesh_path = Path(get_package_share_directory('ardrone_gazebo')) / 'meshes/ardrone_gazebo.dae'
    visual = element(base, 'visual', name='original_ardrone')
    element(visual, 'pose', '0 0 -0.02 0 0 0')
    mesh = element(element(visual, 'geometry'), 'mesh')
    element(mesh, 'uri', Path(mesh_path).resolve().as_uri())
    # Retain the tested lightweight collision envelope, but render only the
    # original COLLADA model (including its own hull, propellers and materials).
    shape(base, 'body', 'box', '0.30 0.12 0.10', visual=False)
    for i, (fx, fy) in enumerate([(.10, .08), (.10, -.08), (-.10, .08), (-.10, -.08)]):
        shape(base, f'foot_{i}', 'box', '0.03 0.03 0.02', f'{fx} {fy} -0.06 0 0 0', visual=False)
    config = []
    for i, (rx, ry, direction) in enumerate([
            (0.145, 0.145, 1), (-0.145, -0.145, 1),
            (0.145, -0.145, -1), (-0.145, 0.145, -1)]):
        angle = math.atan2(ry, rx)
        shape(base, f'arm_{i}', 'box', '0.22 0.018 0.018',
              f'{rx/2} {ry/2} 0 0 0 {angle}', visual=False)
        # Four lightweight protective rims, built from local segments.
        for j in range(16):
            a = j * math.tau / 16
            shape(base, f'guard_{i}_{j}', 'box', '0.040 0.009 0.025',
                  f'{rx + .098*math.cos(a)} {ry + .098*math.sin(a)} 0 0 0 {a+math.pi/2}', visual=False)
        rotor = element(model, 'link', name=f'rotor_{i}')
        element(rotor, 'pose', f'{rx} {ry} 0.025 0 0 0')
        inertia(rotor, 0.005, (0.00001, 0.00001, 0.00002))
        joint = element(model, 'joint', name=f'rotor_{i}_joint', type='revolute')
        element(joint, 'parent', 'base_link')
        element(joint, 'child', f'rotor_{i}')
        element(element(joint, 'axis'), 'xyz', '0 0 1')
        plugin(model, 'multicopter-motor-model', 'MulticopterMotorModel',
               robotNamespace=name, jointName=f'rotor_{i}_joint', linkName=f'rotor_{i}',
               turningDirection='ccw' if direction == 1 else 'cw',
               timeConstantUp=0.0125, timeConstantDown=0.025, maxRotVelocity=900,
               motorConstant=8.54858e-6, momentConstant=0.016,
               commandSubTopic='motor_speed', actuator_number=i,
               rotorDragCoefficient=8.06428e-5, rollingMomentCoefficient=1e-6,
               rotorVelocitySlowdownSim=10, motorType='velocity')
        config.append((i, direction))
    control = plugin(model, 'multicopter-control', 'MulticopterVelocityControl',
                     robotNamespace=name, commandSubTopic='sim/cmd_vel',
                     enableSubTopic='sim/enable', comLinkName='base_link',
                     velocityGain='2.7 2.7 2.7', attitudeGain='2 2 0.15',
                     angularRateGain='0.4 0.4 0.18', maximumLinearAcceleration='2 2 2',
                     maximumLinearVelocity='2 2 1', maximumAngularVelocity='0 0 1.5')
    rotors = element(control, 'rotorConfiguration')
    for i, direction in config:
        rotor = element(rotors, 'rotor')
        for key, value in dict(jointName=f'rotor_{i}_joint', forceConstant=8.54858e-6,
                               momentConstant=0.016, direction=direction).items():
            element(rotor, key, value)
    plugin(model, 'odometry-publisher', 'OdometryPublisher', dimensions=3,
           odom_frame='world', robot_base_frame=f'{name}/base_link',
           odom_topic=f'/{name}/odom', odom_publish_frequency=50)
    imu = element(base, 'sensor', name='imu', type='imu')
    element(imu, 'topic', f'/{name}/imu')
    element(imu, 'frame_id', f'{name}/base_link')
    element(imu, 'update_rate', 100)
    element(imu, 'always_on', 'true')
    element(imu, 'imu')
    if cameras:
        for camera_name, pose in [('front_camera', '0.28 0 0.02 0 0 0'),
                                  ('bottom_camera', '0 0 -0.065 0 1.57079632679 0')]:
            sensor = element(base, 'sensor', name=camera_name, type='camera')
            element(sensor, 'pose', pose)
            element(sensor, 'topic', f'/{name}/{camera_name}/image_raw')
            element(sensor, 'frame_id', f'{name}/{camera_name}_optical_frame')
            element(sensor, 'update_rate', 15)
            element(sensor, 'always_on', 'true')
            camera = element(sensor, 'camera')
            element(camera, 'horizontal_fov', 1.4)
            element(camera, 'camera_info_topic', f'/{name}/{camera_name}/camera_info')
            image = element(camera, 'image')
            for key, value in dict(width=320, height=240, format='R8G8B8').items():
                element(image, key, value)
            clip = element(camera, 'clip')
            element(clip, 'near', 0.02)
            element(clip, 'far', 100)
    return model
