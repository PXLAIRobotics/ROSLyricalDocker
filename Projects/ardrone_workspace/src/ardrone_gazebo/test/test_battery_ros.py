"""Exercise the delayed service and telemetry using a real ROS executor/transport."""
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Empty
from std_srvs.srv import Trigger
from ardrone_gazebo.controller import FlightController


def test_drone_owns_charge_and_delayed_service_stays_responsive(monkeypatch):
    monkeypatch.setenv('ARDRONE_FLIGHT_TIME_MINUTES', '0.05')
    monkeypatch.setenv('ARDRONE_RECHARGE_TIME_SECONDS', '1.5')
    rclpy.init(args=['--ros-args', '-r', '__ns:=/battery_test'])
    controller = FlightController()
    probe = Node('battery_probe')
    executor = SingleThreadedExecutor()
    executor.add_node(controller)
    executor.add_node(probe)
    samples = []
    probe.create_subscription(BatteryState, 'battery', lambda msg: samples.append(msg), 10)
    pub = probe.create_publisher(Odometry, 'odom', 10)
    takeoff = probe.create_publisher(Empty, 'takeoff', 10)
    client = probe.create_client(Trigger, 'recharge')
    odom = Odometry()
    odom.pose.pose.position.z = .1
    publishing = [True]
    probe.create_timer(.02, lambda: pub.publish(odom) if publishing[0] else None)

    def wait(predicate, timeout=5.):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
            if predicate():
                return
        raise AssertionError('Timed out waiting for battery behavior')

    def run_for(seconds):
        end = time.monotonic() + seconds
        wait(lambda: time.monotonic() >= end, seconds + 1)

    try:
        wait(lambda: samples and controller.grounded() and client.service_is_ready())
        assert samples[-1].percentage == 1.
        run_for(.2)
        assert controller.battery.percentage == 1.
        takeoff.publish(Empty())
        wait(lambda: controller.flight.state == 'taking_off')
        odom.pose.pose.position.z = 1.1
        wait(lambda: controller.flight.state == 'flying')
        denied = client.call_async(Trigger.Request())
        wait(denied.done)
        assert not denied.result().success
        wait(lambda: controller.battery.percentage < .19)
        controller.flight.land()
        odom.pose.pose.position.z = .1
        wait(controller.grounded)
        before = controller.battery.percentage
        takeoff.publish(Empty())
        run_for(.15)
        assert controller.flight.state == 'landed'
        assert abs(controller.battery.percentage - before) < .01
        samples.clear()
        request = client.call_async(Trigger.Request())
        wait(lambda: controller.battery.charging)
        duplicate = client.call_async(Trigger.Request())
        wait(duplicate.done)
        assert not duplicate.result().success
        assert not request.done()
        takeoff.publish(Empty())
        run_for(.3)
        assert controller.flight.state == 'landed'
        assert controller.battery.percentage > before
        assert not request.done()
        wait(request.done)
        assert request.result().success
        assert controller.battery.percentage == 1.
        charging = [m.percentage for m in samples if m.power_supply_status == BatteryState.POWER_SUPPLY_STATUS_CHARGING]
        assert len(charging) >= 3 and charging[-1] > charging[0]
        assert all(a <= b for a, b in zip(charging, charging[1:]))
        takeoff.publish(Empty())
        wait(lambda: controller.flight.state == 'taking_off')
        odom.pose.pose.position.z = 1.1
        wait(lambda: controller.flight.state == 'flying')
        wait(lambda: controller.flight.state == 'landing')  # low battery lands before depletion
        assert 0. < controller.battery.percentage <= .03
        odom.pose.pose.position.z = .1
        wait(controller.grounded)
        interrupted = client.call_async(Trigger.Request())
        wait(lambda: controller.battery.charging)
        publishing[0] = False
        wait(interrupted.done)
        assert not interrupted.result().success and not controller.battery.charging
        assert controller.battery.percentage < 1.
        denied = client.call_async(Trigger.Request())
        wait(denied.done)
        assert not denied.result().success  # stale ground feedback
    finally:
        executor.shutdown()
        probe.destroy_node()
        controller.destroy_node()
        rclpy.shutdown()
