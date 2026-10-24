#!/usr/bin/env python3
"""Recreate the Noetic layouts; run explicitly with a ROSNoeticDocker checkout.

No checkout is needed to build or run the committed generated worlds.
Original floor artwork is retained, while external obstacle meshes are replaced
by their primitive collision geometry (or a documented local approximation).
"""
import argparse
from copy import deepcopy
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def add(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, tag, attrs)
    node.text = text
    return node


def ground(world):
    model = add(world, 'model', name='ground_plane')
    add(model, 'static', 'true')
    link = add(model, 'link', name='ground')
    for kind in ('visual', 'collision'):
        obj = add(link, kind, name='ground')
        plane = add(add(obj, 'geometry'), 'plane')
        add(plane, 'normal', '0 0 1')
        add(plane, 'size', '100 100')
        if kind == 'visual':
            mat = add(obj, 'material')
            add(mat, 'ambient', '0.6 0.6 0.6 1')
            add(mat, 'diffuse', '0.6 0.6 0.6 1')


def base():
    sdf = ET.Element('sdf', version='1.10')
    world = add(sdf, 'world', name='ardrone_world')
    add(world, 'gravity', '0 0 -9.81')
    scene = add(world, 'scene')
    add(scene, 'ambient', '0.5 0.5 0.5 1')
    add(scene, 'background', '0.7 0.8 0.9 1')
    light = add(world, 'light', name='sun', type='directional')
    add(light, 'pose', '0 0 10 0 0 0')
    add(light, 'diffuse', '0.8 0.8 0.8 1')
    add(light, 'direction', '-0.5 0.1 -0.9')
    ground(world)
    return sdf, world


def save(root, path):
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='unicode', xml_declaration=True)


def convert(checkout, destination):
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'textures').mkdir(exist_ok=True)
    save(base()[0], destination / 'empty.sdf')
    sources = checkout / 'Projects/catkin_ws_src'
    for name, package in [('summerforall', 'summerforall'), ('sternformost', 'sternformost'),
                          ('rommel', 'sternformost'), ('glasshouse', 'pxl_drones_week')]:
        original = ET.parse(sources / package / 'worlds' / f'{name}.world').getroot().find('world')
        root, world = base()
        for old in original.findall('model'):
            model_name = old.get('name')
            if model_name == 'ground_plane':
                continue
            model = add(world, 'model', name=model_name)
            add(model, 'static', 'true')
            add(model, 'pose', old.findtext('pose', '0 0 0 0 0 0'))
            if model_name in ('summerforall', 'sternformost', 'glasshouse'):
                texture = sources / package / 'models' / model_name / 'materials/textures' / f'{model_name}.png'
                shutil.copy2(texture, destination / 'textures' / texture.name)
                link = add(model, 'link', name='floor_map')
                # Match source plane's dimensions and UV convention.
                for kind in ('visual', 'collision'):
                    obj = add(link, kind, name='map')
                    obj.append(deepcopy(old.find(f'link/{kind}/geometry')))
                    if kind == 'visual':
                        mat = add(obj, 'material')
                        add(mat, 'diffuse', '1 1 1 1')
                        add(mat, 'ambient', '1 1 1 1')
                        metal = add(add(mat, 'pbr'), 'metal')
                        add(metal, 'albedo_map', f'textures/{texture.name}')
                        add(metal, 'metalness', '0')
                        add(metal, 'roughness', '1')
                continue
            # Recreate scenery from collision primitives, keeping the source poses.
            for index, old_link in enumerate(old.findall('link')):
                link = add(model, 'link', name=f'part_{index}')
                add(link, 'pose', old_link.findtext('pose', '0 0 0 0 0 0'))
                for j, collision in enumerate(old_link.findall('collision')):
                    geometry = deepcopy(collision.find('geometry'))
                    if geometry is None:
                        continue
                    if geometry.find('mesh') is not None:
                        # These few meshes have no bundled collision primitives.
                        geometry = ET.Element('geometry')
                        box = add(geometry, 'box')
                        size = '0.5 0.5 0.5'
                        if 'turtlebot' in model_name:
                            size = '0.28 0.30 0.15'
                        elif 'rover' in model_name:
                            size = '1.2 0.8 0.6'
                        add(box, 'size', size)
                    for kind in ('collision', 'visual'):
                        obj = add(link, kind, name=f'shape_{j}')
                        add(obj, 'pose', collision.findtext('pose', '0 0 0 0 0 0'))
                        obj.append(deepcopy(geometry))
                        if kind == 'visual':
                            color = '0.55 0.55 0.55 1'
                            if 'cardboard' in model_name:
                                color = '0.65 0.42 0.20 1'
                            elif 'cone' in model_name:
                                color = '1 0.3 0.02 1'
                            elif 'tree' in model_name:
                                color = '0.2 0.45 0.12 1'
                            mat = add(obj, 'material')
                            add(mat, 'diffuse', color)
                            add(mat, 'ambient', color)
        save(root, destination / f'{name}.sdf')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    convert(args.checkout, Path(__file__).resolve().parents[1] / 'src/ardrone_gazebo/worlds')
