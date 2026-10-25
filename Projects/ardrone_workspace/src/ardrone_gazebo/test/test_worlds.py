from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
import pytest
from ardrone_gazebo.simulation import WORLDS, bridges, build_world

WORLDS_DIR = Path(__file__).resolve().parents[1] / 'worlds'


@pytest.mark.parametrize('world', WORLDS)
def test_world_is_self_contained_and_fleet_is_isolated(world):
    names = ['ardrone_1', 'ardrone_2']
    root = ET.fromstring(build_world(WORLDS_DIR, world, names))
    assert not list(root.iter('include'))
    meshes = list(root.iter('mesh'))
    assert len(meshes) == len(names) + (80*13 if world == 'orchard' else 0)
    for mesh in meshes:
        uri = urlparse(mesh.findtext('uri'))
        assert uri.scheme == 'file'
        assert Path(unquote(uri.path)).is_file()
    assert not list(root.iter('script'))
    for texture in root.iter('albedo_map'):
        assert Path(texture.text).is_file()
    assert len(root.findall('./world/model')) >= 3
    for name in names:
        model = root.find(f'./world/model[@name="{name}"]')
        assert len(model.findall('joint')) == 4
        assert len(model.findall('.//visual')) == 1
        assert model.find('link/visual').get('name') == 'original_ardrone'
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


@pytest.mark.parametrize('count', [1, 10, 32])
def test_orchard_platforms_match_fleet_and_spawn_height(count):
    names = [f'ardrone_{i+1}' for i in range(count)]
    world = ET.fromstring(build_world(WORLDS_DIR, 'orchard', names, cameras=False)).find('world')
    pads = [m for m in world.findall('model') if m.get('name').startswith('landing_platform_')]
    assert len(pads) == count
    positions = []
    for i, name in enumerate(names):
        aircraft = world.find(f'model[@name="{name}"]')
        x, y, z, *_ = map(float, aircraft.findtext('pose').split())
        pad = world.find(f'model[@name="landing_platform_{i+1:02d}"]')
        px, py, pz, *_ = map(float, pad.findtext('link/collision/pose').split())
        assert (x, y) == (px, py)
        assert z-.07 > pz+.18/2
        assert x <= 0  # clear of the hill, which begins around x=8
        positions.append((x, y))
    assert len(set(positions)) == count
    assert len([m for m in world.findall('model') if m.get('name').startswith('apple_tree_')]) == 80
    hill = world.find('model[@name="orchard_hill"]/link/collision')
    assert float(hill.findtext('pose').split()[4]) < 0


def test_orchard_rejects_overlapping_platforms_and_excessive_fleet():
    with pytest.raises(ValueError):
        build_world(WORLDS_DIR, 'orchard', ['one', 'two'], spacing=.9)
    with pytest.raises(ValueError):
        build_world(WORLDS_DIR, 'orchard', [f'drone_{i}' for i in range(33)])


def test_orchard_generated_landscape_matches_bundled_world():
    from ardrone_gazebo.orchard import orchard_world
    assert (WORLDS_DIR/'orchard.sdf').read_text().strip() == orchard_world()


def test_orchard_keeps_stone_wall_without_cypresses():
    root = ET.fromstring(build_world(WORLDS_DIR, 'orchard', ['ardrone'], cameras=False))
    assert not any(m.get('name').startswith('cypress_') for m in root.findall('./world/model'))
    wall = root.find('./world/model[@name="hilltop_stone_wall"]')
    assert wall is not None
    assert wall.find('link/visual/geometry/box') is not None
    assert wall.find('link/collision/geometry/box') is not None


def test_orchard_apples_have_all_four_ripeness_stages():
    root = ET.parse(WORLDS_DIR/'orchard.sdf')
    trees = [m for m in root.findall('./world/model') if m.get('name').startswith('apple_tree_')]
    for tree in trees:
        fruits = [v for v in tree.findall('link/visual') if v.get('name').startswith('apple_')
                  and not v.get('name').startswith('apple_stem_')]
        assert len(fruits) == 12
        assert {v.get('name').split('_')[1] for v in fruits} == {'unripe', 'turning', 'blushing', 'ripe'}
        assert len({v.findtext('material/diffuse') for v in fruits}) == 4
        assert len(tree.findall('link/collision[@name="trunk"]')) == 1
        assert tree.find('link/visual[@name="tree_canopy"]/geometry/mesh') is not None
        assert all(v.find('geometry/mesh') is not None for v in fruits)
        assert not tree.findall('link/visual[@name="trained_branch"]')


def test_orchard_meshes_have_real_leaf_and_bark_geometry():
    ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
    for variant in range(3):
        root = ET.parse(WORLDS_DIR.parent/'meshes'/f'orchard_tree_{variant}.dae')
        triangles = root.findall('.//c:triangles', ns)
        assert sum(int(t.get('count')) for t in triangles) > 12000
        materials = {t.get('material') for t in triangles}
        assert {'bark', 'bark_light', 'vein', 'underside', 'leaf0'} <= materials
