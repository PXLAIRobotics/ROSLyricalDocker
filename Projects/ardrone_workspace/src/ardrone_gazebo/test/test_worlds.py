from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from ardrone_gazebo.simulation import WORLDS, bridges, build_world

WORLDS_DIR = Path(__file__).resolve().parents[1] / 'worlds'


@pytest.mark.parametrize('world', WORLDS)
def test_world_is_self_contained_and_fleet_is_isolated(world):
    names = ['ardrone_1', 'ardrone_2']
    root = ET.fromstring(build_world(WORLDS_DIR, world, names))
    assert not list(root.iter('include'))
    assert not list(root.iter('mesh'))
    assert not list(root.iter('script'))
    for texture in root.iter('albedo_map'):
        assert Path(texture.text).is_file()
    assert len(root.findall('./world/model')) >= 3
    for name in names:
        model = root.find(f'./world/model[@name="{name}"]')
        assert len(model.findall('joint')) == 4
        topics = [e.text for e in model.iter('topic')]
        assert len(topics) == 3 and all(t.startswith(f'/{name}/') for t in topics)
        assert all(e.text == name for e in model.iter('robotNamespace'))
    topics = [b['ros_topic_name'] for b in bridges(names)]
    assert len(topics) == len(set(topics)) == 17
    assert topics.count('/clock') == 1


def test_no_render_sensors_when_cameras_disabled():
    root = ET.fromstring(build_world(WORLDS_DIR, 'empty', ['solo'], cameras=False))
    assert len(root.findall('.//sensor')) == 1
    assert not root.findall('.//plugin[@name="gz::sim::systems::Sensors"]')
    assert len(bridges(['solo'], False)) == 5


@pytest.mark.parametrize('names,spacing', [(['a', 'a'], 1.5), (['bad/name'], 1.5),
                                           (['a'], .1), (['a'], float('nan'))])
def test_invalid_spawn_configuration(names, spacing):
    with pytest.raises(ValueError):
        build_world(WORLDS_DIR, 'empty', names, spacing)
