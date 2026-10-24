"""Shared single/multiple-drone launch configuration."""
from pathlib import Path
import tempfile
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from .simulation import WORLDS, bridges, build_world
from .flight import Flight


def boolean(value):
    if value.lower() not in ('true', 'false'):
        raise ValueError('Boolean launch arguments must be true or false')
    return value.lower() == 'true'


def setup(context):
    value = lambda name: LaunchConfiguration(name).perform(context)
    count = int(value('count'))
    Flight(float(value('takeoff_height')), float(value('command_timeout')))
    if not 1 <= count <= 32:
        raise ValueError('count must be between 1 and 32')
    cameras, gui = boolean(value('cameras')), boolean(value('gui'))
    name = value('name')
    names = [name] if count == 1 else [f'{name}_{i+1}' for i in range(count)]
    world_dir = Path(get_package_share_directory('ardrone_gazebo')) / 'worlds'
    world = build_world(world_dir, value('world'), names, float(value('spacing')), cameras)
    directory = tempfile.TemporaryDirectory(prefix='ardrone_sim_')
    world_file = Path(directory.name) / 'world.sdf'
    bridge_file = Path(directory.name) / 'bridge.yaml'
    world_file.write_text(world)
    bridge_file.write_text(yaml.safe_dump(bridges(names, cameras)))
    command = ['gz', 'sim', '-r', '-v', '2']
    if not gui:
        command += ['-s', '--headless-rendering']
    command.append(str(world_file))
    simulator = ExecuteProcess(cmd=command, output='screen')
    actions = [
        RegisterEventHandler(OnShutdown(on_shutdown=[OpaqueFunction(
            function=lambda context: directory.cleanup())])),
        RegisterEventHandler(OnProcessExit(target_action=simulator,
            on_exit=[EmitEvent(event=Shutdown(reason='Gazebo exited'))])),
        simulator,
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='ardrone_bridge',
             parameters=[{'config_file': str(bridge_file)}], output='screen'),
    ]
    for drone_name in names:
        actions.append(Node(package='ardrone_gazebo', executable='flight_controller',
                            namespace=drone_name, output='screen', parameters=[{
                                'use_sim_time': True,
                                'takeoff_height': float(value('takeoff_height')),
                                'command_timeout': float(value('command_timeout'))}]))
    return actions


def description(count='1'):
    return LaunchDescription([
        DeclareLaunchArgument('count', default_value=count, description='Number of drones (1–32)'),
        DeclareLaunchArgument('name', default_value='ardrone', description='Namespace, or prefix for a fleet'),
        DeclareLaunchArgument('world', default_value='empty', choices=WORLDS),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('cameras', default_value='true', description='Disable for faster physics-only runs'),
        DeclareLaunchArgument('spacing', default_value='1.5', description='Spawn grid spacing in metres'),
        DeclareLaunchArgument('takeoff_height', default_value='1.0', description='Height above launch surface'),
        DeclareLaunchArgument('command_timeout', default_value='0.5', description='Seconds before hovering'),
        OpaqueFunction(function=setup),
    ])
