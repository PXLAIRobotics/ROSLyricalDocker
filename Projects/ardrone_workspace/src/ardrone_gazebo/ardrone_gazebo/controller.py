"""ROS interface around Gazebo's physical multicopter velocity controller."""
import math
import signal
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.task import Future
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, Empty, String
from sensor_msgs.msg import BatteryState
from std_srvs.srv import Trigger
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from .flight import Flight
from .battery import Battery, duration
from .disturbance import Disturbance


class FlightController(Node):
    def __init__(self):
        super().__init__('flight_controller')
        self.flight = Flight(
            self.declare_parameter('takeoff_height', 1.0).value,
            self.declare_parameter('command_timeout', 0.5).value)
        self.battery = Battery(
            self.declare_parameter('flight_time_minutes', duration('ARDRONE_FLIGHT_TIME_MINUTES', 30.)).value,
            self.declare_parameter('recharge_time_seconds', duration('ARDRONE_RECHARGE_TIME_SECONDS', 30.)).value)
        self.recharge_done = None
        self.vertical_speed = math.inf
        self.drone_name = self.get_namespace().strip('/')
        self.disturbance = Disturbance(
            self.declare_parameter('disturbances', False).value,
            self.declare_parameter('drift_speed', .08).value,
            self.declare_parameter('wind_x', .1).value,
            self.declare_parameter('wind_y', 0.).value, seed=self.drone_name)
        self.yaw = 0.
        self.command_pub = self.create_publisher(Twist, 'sim/cmd_vel', 10)
        self.enable_pub = self.create_publisher(Bool, 'sim/enable', 10)
        self.state_pub = self.create_publisher(String, 'state', 10)
        self.battery_pub = self.create_publisher(BatteryState, 'battery', 10)
        self.recharge_service = self.create_service(
            Trigger, 'recharge', self.recharge, callback_group=ReentrantCallbackGroup())
        self.tf = TransformBroadcaster(self)
        self.static_tf = StaticTransformBroadcaster(self)
        self.create_subscription(Empty, 'takeoff', self.takeoff, 10)
        self.create_subscription(Empty, 'land', lambda _: self.flight.land(), 10)
        self.create_subscription(Empty, 'reset', lambda _: self.flight.reset(), 10)
        self.create_subscription(Twist, 'cmd_vel', self.command, 10)
        self.create_subscription(Odometry, 'odom', self.odometry, qos_profile_sensor_data)
        transforms = []
        # ROS optical axes: z forward, x right, y down.
        for camera, xyz, quat in [
            ('front_camera', (.28, 0., .02), (-.5, .5, -.5, .5)),
            ('bottom_camera', (0., 0., -.065), (-math.sqrt(.5), math.sqrt(.5), 0., 0.))]:
            tf = TransformStamped()
            tf.header.stamp = self.get_clock().now().to_msg()
            tf.header.frame_id = f'{self.drone_name}/base_link'
            tf.child_frame_id = f'{self.drone_name}/{camera}_optical_frame'
            tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = xyz
            (tf.transform.rotation.x, tf.transform.rotation.y,
             tf.transform.rotation.z, tf.transform.rotation.w) = quat
            transforms.append(tf)
        self.static_tf.sendTransform(transforms)
        self.create_timer(0.02, self.update)
        self.create_timer(0.2, self.publish_battery)

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def grounded(self):
        f = self.flight
        return (f.state == 'landed' and f.odom_time is not None
                and 0 <= self.now() - f.odom_time < .5
                and abs(self.vertical_speed) < .05)

    def takeoff(self, _):
        self.battery.update(self.now(), self.flight.state != 'landed')
        if not self.battery.can_takeoff:
            self.get_logger().warning('Takeoff refused: charging or battery below 20%.')
            return
        self.flight.takeoff()
        self.battery.update(self.now(), self.flight.state != 'landed')

    async def recharge(self, request, response):
        if self.recharge_done is not None:
            response.success, response.message = False, 'Already recharging.'
            return response
        if not self.grounded():
            response.success, response.message = False, 'Recharge requires a settled, landed drone with fresh odometry.'
            return response
        self.battery.update(self.now(), False)
        if self.battery.percentage >= 1.:
            response.success, response.message = True, 'Battery already full.'
            return response
        self.recharge_done = Future()
        self.battery.charging = True
        self.publish_battery()
        # Yield to the executor: telemetry and flight callbacks keep running.
        response.success, response.message = await self.recharge_done
        self.recharge_done = None
        return response

    def publish_battery(self):
        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f'{self.drone_name}/base_link'
        msg.present = True
        msg.percentage = self.battery.percentage
        for field in ('voltage', 'temperature', 'current', 'charge', 'capacity', 'design_capacity'):
            setattr(msg, field, math.nan)
        msg.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_CHARGING if self.battery.charging else
            BatteryState.POWER_SUPPLY_STATUS_FULL if self.battery.percentage >= 1. else
            BatteryState.POWER_SUPPLY_STATUS_DISCHARGING if self.battery.airborne else
            BatteryState.POWER_SUPPLY_STATUS_NOT_CHARGING)
        self.battery_pub.publish(msg)

    def command(self, msg):
        self.flight.velocity((msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.z), self.now())

    def odometry(self, msg):
        self.flight.odometry(msg.pose.pose.position.z, self.now())
        self.vertical_speed = msg.twist.twist.linear.z
        q = msg.pose.pose.orientation
        self.yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        tf = TransformStamped()
        tf.header = msg.header
        tf.child_frame_id = f'{self.drone_name}/base_link'
        tf.transform.translation.x = msg.pose.pose.position.x
        tf.transform.translation.y = msg.pose.pose.position.y
        tf.transform.translation.z = msg.pose.pose.position.z
        tf.transform.rotation = msg.pose.pose.orientation
        self.tf.sendTransform(tf)

    def update(self):
        self.battery.update(self.now(), self.flight.state != 'landed')
        if self.recharge_done is not None and not self.recharge_done.done():
            if not self.grounded():
                self.battery.charging = False
                self.recharge_done.set_result((False, 'Charging stopped: drone no longer grounded or odometry lost.'))
            elif self.battery.percentage >= 1.:
                self.battery.charging = False
                self.recharge_done.set_result((True, 'Recharge complete: battery 100%.'))
        if self.battery.percentage <= .03:
            self.flight.land()
        enabled, values = self.flight.step(self.now())
        self.battery.update(self.now(), self.flight.state != 'landed')
        fresh = self.flight.odom_time is not None and 0 <= self.now() - self.flight.odom_time < .5
        values = self.disturbance.apply(values, self.now(), self.yaw,
                                        enabled and fresh and self.flight.state == 'flying')
        self.enable_pub.publish(Bool(data=enabled))
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.z = values
        self.command_pub.publish(msg)
        self.state_pub.publish(String(data=self.flight.state))


def main(args=None):
    # Finish spinning before shutting down the context (avoids callback races).
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    node = FlightController()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
