"""Simulation-time flight state machine, independent of ROS for testing."""
import math


class Flight:
    def __init__(self, height=1.0, timeout=0.5):
        if not math.isfinite(height) or height <= 0.15:
            raise ValueError('takeoff_height must be finite and greater than 0.15 m')
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('command_timeout must be positive and finite')
        self.height, self.timeout = height, timeout
        self.state = 'landed'
        self.z = None
        self.ground = None
        self.odom_time = None
        self.command_time = None
        self.command = (0., 0., 0., 0.)
        self.last_time = None

    def odometry(self, z, now):
        if not math.isfinite(z):
            return
        self.z, self.odom_time = z, now
        if self.state == 'landed':
            self.ground = z

    def takeoff(self):
        if self.state == 'landed' and self.z is not None:
            self.state = 'taking_off'
            self.command_time = None

    def land(self):
        if self.state in ('taking_off', 'flying'):
            self.state = 'landing'
            self.command_time = None

    def reset(self):
        # AR.Drone reset is an emergency motor stop, not a teleport.
        self.state = 'emergency'
        self.command_time = None

    def velocity(self, values, now):
        if self.state != 'flying' or not all(math.isfinite(v) for v in values):
            return
        self.command = tuple(max(-limit, min(limit, value))
                             for value, limit in zip(values, (2., 2., 1., 1.5)))
        self.command_time = now

    def step(self, now):
        zero = (0., 0., 0., 0.)
        if self.last_time is not None and now < self.last_time:
            self.__init__(self.height, self.timeout)
        self.last_time = now
        fresh = self.odom_time is not None and 0 <= now - self.odom_time < 0.5
        if self.state == 'emergency':
            if fresh and self.ground is not None and self.z <= self.ground + 0.025:
                self.state = 'landed'
            return False, zero
        if self.state == 'landed' or not fresh:
            # Hover on lost feedback; never keep replaying a motion command.
            return self.state != 'landed', zero
        altitude = self.z - self.ground
        if self.state == 'taking_off':
            error = self.height - altitude
            if abs(error) < 0.06:
                self.state = 'flying'
            return True, (0., 0., max(-0.3, min(0.6, error * 1.5)), 0.)
        if self.state == 'landing':
            if altitude < 0.025:
                self.state = 'landed'
                return False, zero
            return True, (0., 0., -min(0.4, max(0.12, altitude)), 0.)
        if self.command_time is None or not 0 <= now - self.command_time < self.timeout:
            return True, zero
        return True, self.command
