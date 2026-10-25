"""Locally authored hillside orchard and fleet-sized launch terrace."""
import math
import random
import xml.etree.ElementTree as ET
from .model import element

SLOPE = math.radians(8)


def height(x):
    return max(0., (x - 8.) * math.tan(SLOPE))


def model(world, name):
    node = element(world, 'model', name=name)
    element(node, 'static', 'true')
    return element(node, 'link', name='body')


def solid(link, name, kind, dimensions, xyz, color, rotation=(0., 0., 0.), collision=True, visual=True):
    for tag in ('visual', 'collision'):
        if (tag == 'visual' and not visual) or (tag == 'collision' and not collision):
            continue
        node = element(link, tag, name=name)
        element(node, 'pose', ' '.join(str(v) for v in (*xyz, *rotation)))
        geom = element(element(node, 'geometry'), kind)
        if kind == 'box':
            element(geom, 'size', ' '.join(map(str, dimensions)))
        elif kind == 'mesh':
            element(geom, 'uri', dimensions[0])
            element(geom, 'scale', ' '.join([str(dimensions[1])]*3))
        elif kind == 'sphere':
            element(geom, 'radius', dimensions[0])
        else:
            element(geom, 'radius', dimensions[0])
            element(geom, 'length', dimensions[1])
        if tag == 'visual' and color is not None:
            mat = element(node, 'material')
            element(mat, 'ambient', color)
            element(mat, 'diffuse', color)
            element(mat, 'specular', '0.04 0.04 0.04 1')


def orchard_world():
    root = ET.Element('sdf', version='1.10')
    world = element(root, 'world', name='ardrone_world')
    element(world, 'gravity', '0 0 -9.81')
    scene = element(world, 'scene')
    element(scene, 'ambient', '.55 .58 .52 1')
    element(scene, 'background', '.64 .80 .94 1')
    element(scene, 'shadows', 'true')
    sun = element(world, 'light', name='afternoon_sun', type='directional')
    element(sun, 'pose', '0 0 30 0 0 0')
    element(sun, 'diffuse', '.95 .88 .72 1')
    element(sun, 'direction', '-.6 .35 -.9')
    element(sun, 'cast_shadows', 'true')
    ground = model(world, 'meadow')
    solid(ground, 'ground', 'box', (180, 180, 1), (0, 0, -.5), '.34 .43 .20 1')
    hill = model(world, 'orchard_hill')
    solid(hill, 'hillside', 'box', (34, 32, 3), (24, 0, height(24)-1.5/math.cos(SLOPE)),
          '.46 .49 .24 1', rotation=(0, -SLOPE, 0))
    rng = random.Random(27)
    ripeness = (('unripe', '.30 .64 .055 1'), ('turning', '.94 .73 .08 1'),
                ('blushing', '.96 .30 .055 1'), ('ripe', '.74 .025 .018 1'))
    for row in range(8):
        y = (row-3.5)*3.5
        bed = model(world, f'orchard_row_{row+1:02d}')
        solid(bed, 'cultivated_soil', 'box', (30, 1.5, .025), (24, y, height(24)+.02),
              '.35 .25 .15 1', rotation=(0, -SLOPE, 0), collision=False)
        for plant in range(10):
            x = 11 + plant*3.
            z = height(x)
            tree = model(world, f'apple_tree_{row+1:02d}_{plant+1:02d}')
            solid(tree, 'trunk', 'cylinder', (.12, 1.8), (x, y, z+.9), '.30 .19 .10 1', visual=False)
            solid(tree, 'tree_canopy', 'mesh', (f'../meshes/orchard_tree_{(row+plant)%3}.dae', 1.),
                  (x,y,z), None, collision=False)
            crowns = ((-.48, 0., 2.2), (.48, 0., 2.25),
                      (0., -.43, 2.35), (0., .43, 2.3), (0., 0., 2.95))
            for branch, (bx, by, bz) in enumerate(crowns[:4]):
                # Branch axis points from the fork to the lower crown.
                dx, dy, dz = bx, by, bz-1.1
                length = math.sqrt(dx*dx+dy*dy+dz*dz)
                solid(tree, f'branch_{branch}', 'cylinder', (.055, length),
                      (x+dx/2, y+dy/2, z+1.1+dz/2), '.34 .23 .12 1',
                      rotation=(0, math.atan2(math.hypot(dx,dy),dz), math.atan2(dy,dx)),
                      collision=False, visual=False)
            for cluster, (cx, cy, cz) in enumerate(crowns):
                color = rng.choice(('.18 .35 .07 1', '.23 .40 .08 1', '.28 .44 .10 1'))
                solid(tree, f'foliage_{cluster}', 'sphere', (.74,),
                      (x+cx, y+cy, z+cz), color, visual=False)
            # Fruit sits partly inside the lower canopy, with realistic fruit/stem scale.
            # Every tree has all four stages; stage/color is static, not a growth model.
            for apple in range(12):
                cx, cy, cz = crowns[apple % 4]
                angle = math.atan2(cy,cx) + (apple//4-1)*.65 + rng.uniform(-.12,.12)
                down = rng.uniform(-.45, -.1)
                horizontal = math.sqrt(1-down*down)
                ax = x+cx+.70*horizontal*math.cos(angle)
                ay = y+cy+.70*horizontal*math.sin(angle)
                az = z+cz+.70*down
                stage, color = ripeness[(apple+row+plant) % len(ripeness)]
                # The lobed unit mesh gives roughly 6–9 cm fruit diameters.
                radius = rng.uniform(.028,.042)
                solid(tree, f'apple_{stage}_{apple:02d}', 'mesh', (f'../meshes/apple_{stage}.dae', radius),
                      (ax, ay, az), color, collision=False)
                solid(tree, f'apple_stem_{apple:02d}', 'cylinder', (.0018, .022),
                      (ax, ay, az+.74*radius+.009), '.25 .17 .07 1', collision=False)
    # A stone boundary frames the uphill edge.
    wall = model(world, 'hilltop_stone_wall')
    solid(wall, 'wall', 'box', (.45, 32, .65), (40, 0, height(40)+.325), '.56 .54 .46 1')
    ET.indent(root)
    return ET.tostring(root, encoding='unicode')


def add_platforms(world, count, spacing):
    """Return one spawn above each pad; keep platform geometry/count in sync."""
    if not 1 <= count <= 32:
        raise ValueError('Orchard supports 1–32 drone platforms')
    if spacing < 1.2:
        raise ValueError('Orchard platforms require spacing of at least 1.2 m')
    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count/columns)
    length, width = max(12., (rows-1)*spacing+5), max(14., (columns-1)*spacing+5)
    apron = model(world, 'launch_terrace')
    solid(apron, 'gravel', 'box', (length, width, .04), (3-length/2, 0, .02), '.64 .60 .49 1')
    spawns = []
    for i in range(count):
        x, y = -(i//columns)*spacing, ((i % columns)-(columns-1)/2)*spacing
        pad = model(world, f'landing_platform_{i+1:02d}')
        solid(pad, 'platform', 'box', (.95, .95, .18), (x, y, .13), '.18 .23 .27 1')
        solid(pad, 'landing_surface', 'box', (.87, .87, .012), (x, y, .226), '.84 .63 .16 1', collision=False)
        # Orient the H along the aircraft's takeoff heading (+world X).
        for side in (-1, 1):
            solid(pad, f'H_upright_{side}', 'box', (.48, .08, .005),
                  (x, y+side*.18, .235), '.96 .94 .83 1', collision=False)
        solid(pad, 'H_crossbar', 'box', (.08, .36, .005), (x, y, .235), '.96 .94 .83 1', collision=False)
        # The aircraft's feet extend 0.07 m below base_link; spawn 0.02 m above pad.
        spawns.append((x, y, .31))
    return spawns


if __name__ == '__main__':
    print(orchard_world())
