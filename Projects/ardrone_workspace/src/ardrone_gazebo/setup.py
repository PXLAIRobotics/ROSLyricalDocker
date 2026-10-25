from glob import glob
from setuptools import find_packages, setup

setup(
    name='ardrone_gazebo', version='0.1.0', packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/ardrone_gazebo']),
        ('share/ardrone_gazebo', ['package.xml', 'LICENSE', 'PROVENANCE.md']),
        ('share/ardrone_gazebo/launch', glob('launch/*.launch.py')),
        ('share/ardrone_gazebo/config', glob('config/*.config')),
        ('share/ardrone_gazebo/meshes', glob('meshes/*.dae')),
        ('share/ardrone_gazebo/worlds', glob('worlds/*.sdf')),
        ('share/ardrone_gazebo/worlds/textures', glob('worlds/textures/*.png')),
    ],
    install_requires=['setuptools'], extras_require={'test': ['pytest']}, zip_safe=True,
    maintainer='PXL Robotics Lab', maintainer_email='tim.dupont@pxl.be',
    description='Self-contained ROS 2 AR.Drone simulation for Gazebo Jetty',
    license='MIT',
    entry_points={'console_scripts': ['flight_controller = ardrone_gazebo.controller:main']},
)
