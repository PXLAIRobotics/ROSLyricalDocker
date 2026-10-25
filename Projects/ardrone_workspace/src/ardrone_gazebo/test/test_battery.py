import math
import pytest
from ardrone_gazebo.battery import Battery, duration


def test_airtime_pause_sorties_and_clock_reset():
    b = Battery()
    b.update(100, False)
    b.update(1000, True)  # takeoff, ground time costs nothing
    assert b.percentage == 1.
    b.update(1900, False)  # 15 minutes airborne
    assert b.percentage == .5
    b.update(2900, True)
    assert b.percentage == .5
    b.update(2900, True)  # paused clock
    b.update(0, True)  # reset does not refill
    assert b.percentage == .5
    b.update(180, False)
    assert b.percentage == pytest.approx(.4)


def test_threshold_and_recharge_progress():
    b = Battery(flight_minutes=1, recharge_seconds=10)
    b.percentage = .2
    assert b.can_takeoff
    b.percentage = .1999
    assert not b.can_takeoff
    b.update(0, False)
    b.charging = True
    b.update(4, False)
    assert b.percentage == pytest.approx(.5999)
    assert not b.can_takeoff
    b.update(20, False)
    assert b.percentage == 1.
    b.charging = False
    assert b.can_takeoff


def test_depletion_clamps_at_zero():
    b = Battery(flight_minutes=1)
    b.update(0, True)
    b.update(1000, False)
    assert b.percentage == 0.
    assert not b.can_takeoff


@pytest.mark.parametrize('value', ['0', '-1', 'nan', 'inf', 'oops'])
def test_bad_environment(monkeypatch, value):
    monkeypatch.setenv('ARDRONE_FLIGHT_TIME_MINUTES', value)
    with pytest.raises(ValueError):
        duration('ARDRONE_FLIGHT_TIME_MINUTES', 30.)


def test_environment_default_and_override(monkeypatch):
    monkeypatch.delenv('ARDRONE_FLIGHT_TIME_MINUTES', raising=False)
    assert duration('ARDRONE_FLIGHT_TIME_MINUTES', 30.) == 30.
    monkeypatch.setenv('ARDRONE_FLIGHT_TIME_MINUTES', '12.5')
    assert duration('ARDRONE_FLIGHT_TIME_MINUTES', 30.) == 12.5


@pytest.mark.parametrize('value', [0., -1., math.inf, math.nan])
def test_invalid_durations(value):
    with pytest.raises(ValueError):
        Battery(value)
    with pytest.raises(ValueError):
        Battery(recharge_seconds=value)
