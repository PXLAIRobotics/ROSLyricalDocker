"""Generate an offline world and explicit, unidirectional per-drone bridges."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from .model import drone, element, plugin

WORLDS = ('empty', 'summerforall', 'sternformost', 'rommel', 'glasshouse')


def build_world(world_dir, world_name, names, spacing=1.5, cameras=True):
    if world_name not in WORLDS:
        raise ValueError(f'world must be one of {WORLDS}')
    if not names or len(names) != len(set(names)):
        raise ValueError('Drone names must be nonempty and unique')
    if not math.isfinite(spacing) or spacing < 0.7:
        raise ValueError('spacing must be finite and at least 0.7 m')
    tree = ET.parse(Path(world_dir) / f'{world_name}.sdf')
    world = tree.getroot().find('world')
    world.set('name', 'ardrone_world')
    for uri in world.iter('albedo_map'):
        uri.text = str(Path(world_dir) / uri.text)
    physics = element(world, 'physics', name='physics', type='ignored')
    element(physics, 'max_step_size', 0.002)
    element(physics, 'real_time_factor', 1)
    plugin(world, 'physics', 'Physics')
    plugin(world, 'user-commands', 'UserCommands')
    plugin(world, 'scene-broadcaster', 'SceneBroadcaster')
    plugin(world, 'imu', 'Imu')
    if cameras:
        plugin(world, 'sensors', 'Sensors', render_engine='ogre2')
    columns = math.ceil(math.sqrt(len(names)))
    for i, name in enumerate(names):
        world.append(drone(name, (i % columns) * spacing, (i // columns) * spacing, cameras))
    ET.indent(tree)
    return ET.tostring(tree.getroot(), encoding='unicode')


def bridges(names, cameras=True):
    def bridge(topic, ros_type, gz_type, direction='GZ_TO_ROS', gz_topic=None):
        return dict(ros_topic_name=topic, gz_topic_name=gz_topic or topic,
                    ros_type_name=ros_type, gz_type_name=f'gz.msgs.{gz_type}',
                    direction=direction)
    result = [bridge('/clock', 'rosgraph_msgs/msg/Clock', 'Clock',
                     gz_topic='/world/ardrone_world/clock')]
    result[0]['qos_profile'] = 'CLOCK'
    for name in names:
        for topic, ros_type, gz_type, direction in [
            ('sim/cmd_vel', 'geometry_msgs/msg/Twist', 'Twist', 'ROS_TO_GZ'),
            ('sim/enable', 'std_msgs/msg/Bool', 'Boolean', 'ROS_TO_GZ'),
            ('odom', 'nav_msgs/msg/Odometry', 'Odometry', 'GZ_TO_ROS'),
            ('imu', 'sensor_msgs/msg/Imu', 'IMU', 'GZ_TO_ROS')]:
            result.append(bridge(f'/{name}/{topic}', ros_type, gz_type, direction))
        if cameras:
            for camera in ('front_camera', 'bottom_camera'):
                result.append(bridge(f'/{name}/{camera}/image_raw', 'sensor_msgs/msg/Image', 'Image'))
                result.append(bridge(f'/{name}/{camera}/camera_info', 'sensor_msgs/msg/CameraInfo', 'CameraInfo'))
    return result
