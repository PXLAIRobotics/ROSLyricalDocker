#!/usr/bin/env python3
"""Check all pad contacts and one takeoff/landing in 1-, 10- and 32-drone fleets."""
import math
import os
import signal
import subprocess
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from std_msgs.msg import Empty, String

os.environ['ROS_DOMAIN_ID'] = '83'
os.environ['GZ_PARTITION'] = f'orchard-test-{os.getpid()}'


def check(count):
    names = ['ardrone'] if count == 1 else [f'ardrone_{i+1}' for i in range(count)]
    with open(f'/tmp/orchard-{count}.log', 'w') as log:
        process = subprocess.Popen(['ros2', 'launch', 'ardrone_gazebo', 'multi_ardrones.launch.py',
            'world:=orchard', f'count:={count}', 'gui:=false', 'cameras:=false'], stdout=log, stderr=log)
        rclpy.init()
        node = Node('orchard_check')
        odom, state = {}, {}
        for name in names:
            node.create_subscription(Odometry, f'/{name}/odom', lambda msg,n=name: odom.__setitem__(n,msg), qos_profile_sensor_data)
            node.create_subscription(String, f'/{name}/state', lambda msg,n=name: state.__setitem__(n,msg.data), 10)
        takeoff = node.create_publisher(Empty, f'/{names[0]}/takeoff', 10)
        land = node.create_publisher(Empty, f'/{names[0]}/land', 10)

        def wait(predicate, tick=None):
            deadline = time.monotonic()+240
            while time.monotonic() < deadline:
                assert process.poll() is None, f'Launch exited; see /tmp/orchard-{count}.log'
                rclpy.spin_once(node, timeout_sec=.02)
                if tick is not None:
                    tick()
                if predicate():
                    return
            raise AssertionError(f'Timed out: {state}')

        try:
            wait(lambda: len(odom) == count and len(state) == count and
                 all(abs(m.twist.twist.linear.z) < .01 and abs(m.pose.pose.position.z-.29) < .02 for m in odom.values())
                 and takeoff.get_subscription_count() > 0)
            columns = math.ceil(math.sqrt(count))
            for i,name in enumerate(names):
                pos = odom[name].pose.pose.position
                assert abs(pos.x+(i//columns)*1.5) < .02
                assert abs(pos.y-((i % columns)-(columns-1)/2)*1.5) < .02
                assert state[name] == 'landed'
            takeoff.publish(Empty())
            wait(lambda: state[names[0]] == 'flying', lambda: takeoff.publish(Empty()))
            assert odom[names[0]].pose.pose.position.z > 1.1
            assert all(state[n] == 'landed' for n in names[1:])
            land.publish(Empty())
            wait(lambda: state[names[0]] == 'landed' and abs(odom[names[0]].pose.pose.position.z-.29) < .02
                 and abs(odom[names[0]].twist.twist.linear.z) < .01, lambda: land.publish(Empty()))
            print(f'PASS orchard: {count} drones on {count} platforms; takeoff and return to pad', flush=True)
        finally:
            node.destroy_node()
            rclpy.shutdown()
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    import sys
    for count in map(int, sys.argv[1:] or (1, 10, 32)):
        check(count)
