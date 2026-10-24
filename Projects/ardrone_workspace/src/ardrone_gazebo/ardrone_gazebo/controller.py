"""ROS interface around Gazebo's physical multicopter velocity controller."""
import math
import signal
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, Empty, String
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from .flight import Flight


class FlightController(Node):
    def __init__(self):
        super().__init__('flight_controller')
        self.flight = Flight(
            self.declare_parameter('takeoff_height', 1.0).value,
            self.declare_parameter('command_timeout', 0.5).value)
        self.drone_name = self.get_namespace().strip('/')
        self.command_pub = self.create_publisher(Twist, 'sim/cmd_vel', 10)
        self.enable_pub = self.create_publisher(Bool, 'sim/enable', 10)
        self.state_pub = self.create_publisher(String, 'state', 10)
        self.tf = TransformBroadcaster(self)
        self.static_tf = StaticTransformBroadcaster(self)
        self.create_subscription(Empty, 'takeoff', lambda _: self.flight.takeoff(), 10)
        self.create_subscription(Empty, 'land', lambda _: self.flight.land(), 10)
        self.create_subscription(Empty, 'reset', lambda _: self.flight.reset(), 10)
        self.create_subscription(Twist, 'cmd_vel', self.command, 10)
        self.create_subscription(Odometry, 'odom', self.odometry, qos_profile_sensor_data)
        transforms = []
        # ROS optical axes: z forward, x right, y down.
        for camera, xyz, quat in [
            ('front_camera', (.17, 0., .02), (-.5, .5, -.5, .5)),
            ('bottom_camera', (0., 0., -.055), (-math.sqrt(.5), math.sqrt(.5), 0., 0.))]:
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

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def command(self, msg):
        self.flight.velocity((msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.z), self.now())

    def odometry(self, msg):
        self.flight.odometry(msg.pose.pose.position.z, self.now())
        tf = TransformStamped()
        tf.header = msg.header
        tf.child_frame_id = f'{self.drone_name}/base_link'
        tf.transform.translation.x = msg.pose.pose.position.x
        tf.transform.translation.y = msg.pose.pose.position.y
        tf.transform.translation.z = msg.pose.pose.position.z
        tf.transform.rotation = msg.pose.pose.orientation
        self.tf.sendTransform(tf)

    def update(self):
        enabled, values = self.flight.step(self.now())
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
