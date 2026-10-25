#!/usr/bin/env python3
"""Compare calm and disturbed hover with real Gazebo physics (no cameras)."""
import math
import os
import signal
import subprocess
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import Empty, String

os.environ['ROS_DOMAIN_ID'] = '82'
os.environ['GZ_PARTITION'] = f'drift-check-{os.getpid()}'
os.environ['ARDRONE_FLIGHT_TIME_MINUTES'] = '30'


def check(enabled):
    with open(f'/tmp/ardrone-drift-{enabled}.log', 'w') as log:
        launch = subprocess.Popen(['ros2', 'launch', 'ardrone_gazebo', 'two_ardrones.launch.py',
            'gui:=false', 'cameras:=false', f'disturbances:={str(enabled).lower()}',
            'wind_x:=0.15', 'wind_y:=0.0', 'drift_speed:=0.03'], stdout=log, stderr=log)
        rclpy.init()
        node = Node('disturbance_check')
        samples = {}
        for name in ('ardrone_1', 'ardrone_2'):
            for topic, kind in [('state', String), ('odom', Odometry)]:
                key = f'{name}/{topic}'
                node.create_subscription(kind, '/'+key, lambda msg, key=key: samples.__setitem__(key, msg), 10)
        takeoff = node.create_publisher(Empty, '/ardrone_1/takeoff', 10)
        land = node.create_publisher(Empty, '/ardrone_1/land', 10)

        def wait(predicate):
            end = time.monotonic() + 90
            while time.monotonic() < end:
                assert launch.poll() is None, 'Simulator exited'
                rclpy.spin_once(node, timeout_sec=.02)
                if predicate():
                    return
            raise AssertionError(f'Timeout (disturbances={enabled})')

        def simtime():
            stamp = samples['ardrone_1/odom'].header.stamp
            return stamp.sec + stamp.nanosec*1e-9

        try:
            wait(lambda: len(samples) == 4 and takeoff.get_subscription_count() > 0)
            takeoff.publish(Empty())
            wait(lambda: samples['ardrone_1/state'].data == 'flying')
            start = samples['ardrone_1/odom'].pose.pose.position
            start_time = simtime()
            wait(lambda: simtime() - start_time > 6)
            end = samples['ardrone_1/odom'].pose.pose.position
            distance = math.hypot(end.x-start.x, end.y-start.y)
            assert (distance > .45 if enabled else distance < .15), distance
            assert samples['ardrone_2/state'].data == 'landed'
            assert abs(samples['ardrone_2/odom'].pose.pose.position.x - 1.5) < .05
            land.publish(Empty())
            wait(lambda: samples['ardrone_1/state'].data == 'landed')
            print(f'PASS disturbances={enabled}: hover displacement {distance:.3f} m; second drone grounded; landing succeeds', flush=True)
        finally:
            node.destroy_node()
            rclpy.shutdown()
            launch.send_signal(signal.SIGINT)
            try:
                launch.wait(timeout=15)
            except subprocess.TimeoutExpired:
                launch.kill()
                launch.wait()


if __name__ == '__main__':
    check(False)
    check(True)
