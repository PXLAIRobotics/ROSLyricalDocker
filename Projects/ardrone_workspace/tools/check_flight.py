#!/usr/bin/env python3
"""Integration assertions against a running single/fleet launch (ROS environment)."""
import argparse
import math
import time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu, CameraInfo
from std_msgs.msg import Empty, String


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='+', default=['ardrone_1', 'ardrone_2'])
    parser.add_argument('--cameras', action='store_true')
    parser.add_argument('--sensors-only', action='store_true')
    parser.add_argument('--image-output')
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('ardrone_integration_check')
    odom, states, sensors = {}, {}, {}
    publishers = {}
    for name in args.names:
        node.create_subscription(Odometry, f'/{name}/odom',
                                 lambda msg, n=name: odom.__setitem__(n, msg), qos_profile_sensor_data)
        node.create_subscription(String, f'/{name}/state',
                                 lambda msg, n=name: states.__setitem__(n, msg.data), 10)
        node.create_subscription(Imu, f'/{name}/imu',
                                 lambda msg, n=name: sensors.__setitem__((n, 'imu'), msg), qos_profile_sensor_data)
        for topic, kind in [('takeoff', Empty), ('land', Empty), ('reset', Empty), ('cmd_vel', Twist)]:
            publishers[name, topic] = node.create_publisher(kind, f'/{name}/{topic}', 10)
        if args.cameras:
            for camera in ('front_camera', 'bottom_camera'):
                for suffix, kind in [('image_raw', Image), ('camera_info', CameraInfo)]:
                    topic = f'{camera}/{suffix}'
                    node.create_subscription(kind, f'/{name}/{topic}',
                        lambda msg, n=name, t=topic: sensors.__setitem__((n, t), msg), qos_profile_sensor_data)

    def wait(predicate, label, timeout=45, tick=None):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            if tick:
                tick()
            if predicate():
                print('PASS:', label, flush=True)
                return
        raise AssertionError(f'{label}: timed out; states={states}; positions=' +
                             str({n: (m.pose.pose.position.x, m.pose.pose.position.y,
                                      m.pose.pose.position.z) for n, m in odom.items()}))

    def sim_time(name):
        stamp = odom[name].header.stamp
        return stamp.sec + stamp.nanosec * 1e-9

    def duration(seconds, tick=None):
        start = sim_time(args.names[0])
        wait(lambda: sim_time(args.names[0]) - start >= seconds,
             f'{seconds}s simulated', tick=tick)

    try:
        wait(lambda: all(n in odom and states.get(n) == 'landed' and (n, 'imu') in sensors
                         for n in args.names), 'all drones landed, odometry and IMU available')
        duration(1)
        for name in args.names:
            assert odom[name].header.frame_id == 'world', odom[name].header
            assert odom[name].child_frame_id == f'{name}/base_link'
            assert sensors[name, 'imu'].header.frame_id == f'{name}/base_link'
        if args.cameras:
            wait(lambda: len(sensors) == len(args.names) * 5, 'both cameras and camera info on every drone', 90)
            for name in args.names:
                for camera in ('front_camera', 'bottom_camera'):
                    image = sensors[name, f'{camera}/image_raw']
                    info = sensors[name, f'{camera}/camera_info']
                    assert image.width == info.width == 320 and image.height == info.height == 240
                    assert len(image.data) > 0
                    assert image.header.frame_id == info.header.frame_id == f'{name}/{camera}_optical_frame'
        if args.sensors_only:
            return
        first = args.names[0]
        ground = {n: odom[n].pose.pose.position.z for n in args.names}
        start_positions = {n: odom[n].pose.pose.position for n in args.names}
        wait(lambda: states[first] == 'flying', 'first drone takes off',
             tick=lambda: publishers[first, 'takeoff'].publish(Empty()))
        assert odom[first].pose.pose.position.z > ground[first] + .8
        if args.cameras and args.image_output:
            from pathlib import Path
            import cv2
            import numpy as np
            duration(.5)
            output = Path(args.image_output)
            output.mkdir(parents=True, exist_ok=True)
            for camera in ('front_camera', 'bottom_camera'):
                msg = sensors[first, f'{camera}/image_raw']
                assert msg.encoding == 'rgb8', msg.encoding
                pixels = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
                pixels = pixels[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
                cv2.imwrite(str(output / f'{camera}.png'), cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR))
        for other in args.names[1:]:
            assert states[other] == 'landed'
            assert abs(odom[other].pose.pose.position.z - ground[other]) < .08
        x = odom[first].pose.pose.position.x
        command = Twist()
        command.linear.x = .4
        duration(2, lambda: publishers[first, 'cmd_vel'].publish(command))
        assert odom[first].pose.pose.position.x > x + .35, 'Forward command did not move drone'
        duration(3)
        assert abs(odom[first].twist.twist.linear.x) < .15, 'Command timeout did not stop motion'
        q = odom[first].pose.pose.orientation
        yaw_before = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        command = Twist()
        command.angular.z = .4
        duration(2, lambda: publishers[first, 'cmd_vel'].publish(command))
        q = odom[first].pose.pose.orientation
        yaw_after = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        assert abs(math.atan2(math.sin(yaw_after-yaw_before), math.cos(yaw_after-yaw_before))) > .3
        for other in args.names[1:]:
            p = odom[other].pose.pose.position
            assert math.hypot(p.x-start_positions[other].x, p.y-start_positions[other].y) < .05
        print('PASS: movement, yaw, stale-command hover, and namespace isolation', flush=True)
        for other in args.names[1:]:
            wait(lambda n=other: states[n] == 'flying', f'{other} independent takeoff',
                 tick=lambda n=other: publishers[n, 'takeoff'].publish(Empty()))
        for name in args.names:
            wait(lambda n=name: states[n] == 'landed', f'{name} lands',
                 tick=lambda n=name: publishers[n, 'land'].publish(Empty()))
            assert abs(odom[name].pose.pose.position.z-ground[name]) < .08
        wait(lambda: states[first] == 'flying', 'repeat takeoff',
             tick=lambda: publishers[first, 'takeoff'].publish(Empty()))
        publishers[first, 'reset'].publish(Empty())
        wait(lambda: states[first] == 'emergency', 'emergency motor stop')
        wait(lambda: states[first] == 'landed', 'emergency settles on floor')
        print('Flight integration checks passed.', flush=True)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
