import math
import pytest
from ardrone_gazebo.disturbance import Disturbance


def test_disabled_and_inactive_preserve_commands():
    command = (.3, -.1, .2, .4)
    assert Disturbance().apply(command, 5, 0, True) == command
    assert Disturbance(True).apply(command, 5, 0, False) == command


def test_wind_world_frame_and_saturation():
    d = Disturbance(True, 0., .2, 0.)
    assert d.apply((0., 0., .3, .4), 0, math.pi/2, True) == pytest.approx((0., -.2, .3, .4))
    assert d.apply((2., -2., 0., 0.), 0, 0, True) == (2., -2., 0., 0.)


def test_drift_is_bounded_repeatable_and_distinct_for_each_drone():
    d = Disturbance(True, .08, 0., 0., 'ardrone_1')
    same = Disturbance(True, .08, 0., 0., 'ardrone_1')
    other = Disturbance(True, .08, 0., 0., 'ardrone_2')
    zero = (0.,)*4
    samples = [d.apply(zero, i*.05, 0, True) for i in range(1000)]
    assert all(abs(v) <= .08 for sample in samples for v in sample[:2])
    assert samples[0] != samples[100]
    assert d.apply(zero, 0, 0, True) == same.apply(zero, 0, 0, True) == samples[0]
    assert samples[0] != other.apply(zero, 0, 0, True)
    assert max(abs(a-b) for a, b in zip(samples[0], samples[1])) < .01


@pytest.mark.parametrize('kwargs', [dict(drift_speed=-1), dict(drift_speed=math.nan),
    dict(wind_x=math.inf), dict(wind_y=.51), dict(disturbances='false')])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        Disturbance(**kwargs)
