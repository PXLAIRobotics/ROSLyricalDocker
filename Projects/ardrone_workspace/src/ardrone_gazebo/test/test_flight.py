import math
import pytest
from ardrone_gazebo.flight import Flight


def airborne():
    flight = Flight()
    flight.odometry(.08, 0)
    flight.takeoff()
    flight.odometry(1.08, .1)
    flight.step(.1)
    assert flight.state == 'flying'
    return flight


def test_takeoff_requires_feedback_and_commands_are_gated():
    flight = Flight()
    flight.takeoff()
    flight.velocity((1., 0., 0., 0.), 0)
    assert flight.step(0) == (False, (0., 0., 0., 0.))
    flight.odometry(.08, .1)
    flight.takeoff()
    enabled, velocity = flight.step(.1)
    assert enabled and velocity[2] > 0 and velocity[0] == 0


def test_timeout_limits_and_invalid_commands():
    flight = airborne()
    flight.velocity((20., -20., 5., 5.), .1)
    assert flight.step(.2) == (True, (2., -2., 1., 1.5))
    flight.velocity((math.nan, 0., 0., 0.), .2)
    assert flight.step(.3)[1][0] == 2
    flight.odometry(1.08, .7)
    assert flight.step(.7) == (True, (0., 0., 0., 0.))


def test_stale_feedback_stops_motion_and_clock_rewind_disarms():
    flight = airborne()
    flight.velocity((1., 0., 0., 0.), .4)
    assert flight.step(.7)[1] == (0., 0., 0., 0.)
    assert flight.step(0)[0] is False
    assert flight.state == 'landed' and flight.z is None


def test_landing_ignores_new_velocity_and_takeoff():
    flight = airborne()
    flight.land()
    flight.takeoff()
    flight.velocity((1., 0., 1., 0.), .2)
    assert flight.step(.2)[1][2] < 0
    flight.odometry(.09, .3)
    assert flight.step(.3)[0] is False
    assert flight.state == 'landed'


def test_emergency_disarms_until_ground_contact():
    flight = airborne()
    flight.reset()
    flight.takeoff()
    assert flight.step(.2)[0] is False
    assert flight.state == 'emergency'
    flight.odometry(.08, .3)
    flight.step(.3)
    assert flight.state == 'landed'


@pytest.mark.parametrize('height,timeout', [(0., .5), (1., 0.), (math.nan, .5), (1., math.inf)])
def test_invalid_configuration(height, timeout):
    with pytest.raises(ValueError):
        Flight(height, timeout)
