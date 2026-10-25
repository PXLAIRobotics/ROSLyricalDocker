"""Linear simulated battery, owned by each drone controller."""
import math
import os


def duration(name, default):
    value = float(os.environ.get(name, default))
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be positive and finite')
    return value


class Battery:
    def __init__(self, flight_minutes=30., recharge_seconds=30.):
        if not all(math.isfinite(v) and v > 0 for v in (flight_minutes, recharge_seconds)):
            raise ValueError('Battery durations must be positive and finite')
        self.flight_seconds = flight_minutes * 60
        self.recharge_seconds = recharge_seconds
        self.percentage = 1.
        self.charging = False
        self.airborne = False
        self.last_time = None

    @property
    def can_takeoff(self):
        return not self.charging and self.percentage >= .2

    def update(self, now, airborne):
        # Reset/paused simulation clocks must never create or remove charge.
        dt = 0. if self.last_time is None else max(0., now - self.last_time)
        self.last_time = now
        if self.charging:
            self.percentage = min(1., self.percentage + dt / self.recharge_seconds)
        elif self.airborne:
            self.percentage = max(0., self.percentage - dt / self.flight_seconds)
        self.airborne = airborne
