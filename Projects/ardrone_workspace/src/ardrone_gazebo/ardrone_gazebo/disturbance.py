"""Bounded, repeatable hover drift and world-frame wind-like velocity bias."""
import math
import random


class Disturbance:
    def __init__(self, disturbances=False, drift_speed=.08, wind_x=.1, wind_y=0., seed='ardrone'):
        if not isinstance(disturbances, bool):
            raise ValueError('disturbances must be a boolean')
        if not math.isfinite(drift_speed) or not 0 <= drift_speed <= .5:
            raise ValueError('drift_speed must be between 0 and 0.5 m/s')
        if not all(math.isfinite(v) and abs(v) <= .5 for v in (wind_x, wind_y)):
            raise ValueError('wind_x and wind_y must be between -0.5 and 0.5 m/s')
        self.enabled = disturbances
        self.drift_speed = drift_speed
        self.wind = (wind_x, wind_y)
        rng = random.Random(seed)
        self.phases = [rng.uniform(0., math.tau) for _ in range(4)]

    def apply(self, values, now, yaw, active):
        if not self.enabled or not active or not all(math.isfinite(v) for v in (now, yaw)):
            return values
        # Smooth, bounded multi-frequency drift, evaluated in simulation time.
        # No integration state: pause and rewind are repeatable, independent of tick rate.
        dx, dy = (self.drift_speed * (.65 * math.sin(now * .7 + self.phases[i])
                  + .35 * math.sin(now * 1.9 + self.phases[i+2])) for i in range(2))
        wx, wy = self.wind[0] + dx, self.wind[1] + dy
        c, s = math.cos(yaw), math.sin(yaw)
        x, y, z, angular = values
        return (max(-2., min(2., x + c*wx + s*wy)),
                max(-2., min(2., y - s*wx + c*wy)), z, angular)
