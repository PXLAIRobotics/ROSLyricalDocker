"""Generate reusable, self-contained leaf/branch and lobed apple COLLADA assets."""
import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET


def add(a,b): return tuple(x+y for x,y in zip(a,b))
def mul(a,s): return tuple(x*s for x in a)
def sub(a,b): return add(a,mul(b,-1))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a): return mul(a,1/max(1e-12,math.sqrt(sum(x*x for x in a))))


class Mesh:
    def __init__(self, colors):
        self.colors=colors
        self.faces={key:[] for key in colors}

    def triangle(self, material, a,b,c, normals=None):
        normal=unit(cross(sub(b,a),sub(c,a)))
        self.faces[material].append(((a,b,c), normals or (normal,)*3))

    def tube(self, start, end, r1, r2, material='bark', sides=10):
        axis=unit(sub(end,start))
        u=unit(cross(axis,(0,1,0)))
        v=cross(axis,u)
        rings=[]
        for center,radius in ((start,r1),(end,r2)):
            rings.append([add(center,add(mul(u,radius*math.cos(i*math.tau/sides)),
                                        mul(v,radius*math.sin(i*math.tau/sides)))) for i in range(sides)])
        for i in range(sides):
            j=(i+1)%sides
            self.triangle(material,rings[0][i],rings[0][j],rings[1][i])
            self.triangle(material,rings[0][j],rings[1][j],rings[1][i])
        for i in range(1,sides-1):
            self.triangle(material,rings[1][0],rings[1][i],rings[1][i+1])

    def save(self,path):
        ns='http://www.collada.org/2005/11/COLLADASchema'
        root=ET.Element('COLLADA',xmlns=ns,version='1.4.1')
        asset=ET.SubElement(root,'asset')
        ET.SubElement(asset,'created').text='2026-10-25T00:00:00Z'
        ET.SubElement(asset,'modified').text='2026-10-25T00:00:00Z'
        ET.SubElement(asset,'unit',name='meter',meter='1')
        ET.SubElement(asset,'up_axis').text='Z_UP'
        effects=ET.SubElement(root,'library_effects');materials=ET.SubElement(root,'library_materials')
        for name,color in self.colors.items():
            effect=ET.SubElement(effects,'effect',id=name+'-effect')
            technique=ET.SubElement(ET.SubElement(effect,'profile_COMMON'),'technique',sid='common')
            phong=ET.SubElement(technique,'phong')
            for key,value in [('ambient',color),('diffuse',color),('specular',(0.04,.04,.04,1))]:
                ET.SubElement(ET.SubElement(phong,key),'color').text=' '.join(map(str,value))
            mat=ET.SubElement(materials,'material',id=name,name=name)
            ET.SubElement(mat,'instance_effect',url='#'+name+'-effect')
        geometries=ET.SubElement(root,'library_geometries')
        visual=ET.SubElement(ET.SubElement(root,'library_visual_scenes'),'visual_scene',id='Scene')
        node=ET.SubElement(visual,'node',id='Tree')
        for name,faces in self.faces.items():
            if not faces: continue
            ident=name+'-geometry'
            mesh=ET.SubElement(ET.SubElement(geometries,'geometry',id=ident),'mesh')
            for label,index in [('positions',0),('normals',1)]:
                source_id=ident+'-'+label
                source=ET.SubElement(mesh,'source',id=source_id)
                values=[v for face in faces for point in face[index] for v in point]
                ET.SubElement(source,'float_array',id=source_id+'-array',count=str(len(values))).text=' '.join(f'{v:.5f}' for v in values)
                accessor=ET.SubElement(ET.SubElement(source,'technique_common'),'accessor',source='#'+source_id+'-array',count=str(len(values)//3),stride='3')
                for axis in 'XYZ': ET.SubElement(accessor,'param',name=axis,type='float')
            vertices=ET.SubElement(mesh,'vertices',id=ident+'-vertices')
            ET.SubElement(vertices,'input',semantic='POSITION',source='#'+ident+'-positions')
            triangles=ET.SubElement(mesh,'triangles',material=name,count=str(len(faces)))
            ET.SubElement(triangles,'input',semantic='VERTEX',source='#'+ident+'-vertices',offset='0')
            ET.SubElement(triangles,'input',semantic='NORMAL',source='#'+ident+'-normals',offset='1')
            ET.SubElement(triangles,'p').text=' '.join(f'{i} {i}' for i in range(len(faces)*3))
            instance=ET.SubElement(node,'instance_geometry',url='#'+ident)
            bindings=ET.SubElement(ET.SubElement(instance,'bind_material'),'technique_common')
            ET.SubElement(bindings,'instance_material',symbol=name,target='#'+name)
        ET.SubElement(ET.SubElement(root,'scene'),'instance_visual_scene',url='#Scene')
        ET.indent(root)
        ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def tree_mesh(seed):
    rng=random.Random(seed)
    mesh=Mesh({'bark':(.25,.17,.105,1),'bark_light':(.34,.24,.15,1),
               'vein':(.30,.40,.12,1), 'underside':(.19,.29,.08,1),
               **{f'leaf{i}':color for i,color in enumerate(((.12,.24,.035,1),(.18,.32,.045,1),
                   (.24,.38,.06,1),(.29,.42,.085,1),(.21,.34,.07,1)))}})
    trunk=[(0,0,0),(.04,-.03,.7),(-.025,.035,1.25),(.065,.02,1.8),(.1,.06,2.65)]
    for i in range(4):
        mesh.tube(trunk[i],trunk[i+1],.14-i*.026,.115-i*.026,sides=14)
    # Narrow raised bark ridges follow the irregular trunk.
    for i in range(12):
        a=i*math.tau/12
        for j in range(3):
            start=add(trunk[j],(.13*math.cos(a),.13*math.sin(a),0))
            end=add(trunk[j+1],((.11-j*.024)*math.cos(a+.04),(.11-j*.024)*math.sin(a+.04),0))
            mesh.tube(start,end,.008,.005,'bark_light',5)
    crowns=[(-.48,0,2.2),(.48,0,2.25),(0,-.43,2.35),(0,.43,2.3),(0,0,2.95)]
    for group,center in enumerate(crowns):
        mesh.tube(trunk[2],center,.065,.025,sides=9)
        tips=[]
        for twig in range(9):
            angle=rng.uniform(0,math.tau)
            tip=add(center,(math.cos(angle)*rng.uniform(.35,.7),math.sin(angle)*rng.uniform(.35,.7),rng.uniform(-.3,.45)))
            mesh.tube(add(center,(0,0,-.18)),tip,.023,.004,sides=6)
            tips.append(tip)
        for leaf in range(210):
            tip=tips[leaf%len(tips)]
            pos=add(tip,(rng.gauss(0,.16),rng.gauss(0,.16),rng.gauss(0,.13)))
            angle=rng.uniform(0,math.tau)
            u=(math.cos(angle),math.sin(angle),rng.uniform(-.65,.65));u=unit(u)
            v=unit(cross(u,(rng.uniform(-.3,.3),rng.uniform(-.3,.3),1)))
            n=unit(cross(u,v));length=rng.uniform(.16,.27);width=length*rng.uniform(.28,.40)
            # A pointed, folded leaf blade with a raised central vein.
            points=[add(pos,mul(u,-length/2)), add(pos,add(mul(u,-length*.12),mul(v,width))),
                    add(pos,add(mul(u,length*.23),mul(v,width*.7))), add(pos,mul(u,length/2)),
                    add(pos,add(mul(u,length*.23),mul(v,-width*.7))),
                    add(pos,add(mul(u,-length*.12),mul(v,-width)))]
            mid=add(pos,mul(n,.018));material=f'leaf{rng.randrange(5)}'
            for j in range(6):
                a,b=points[j],points[(j+1)%6]
                mesh.triangle(material,a,b,mid)
                mesh.triangle('underside',b,a,mid)
            mesh.triangle('vein',points[0],add(mid,mul(v,.003)),points[3])
    return mesh


def apple_mesh(color):
    mesh=Mesh({'skin':color})
    def point(i,j):
        phi=math.pi*i/12;theta=math.tau*j/20
        r=math.sin(phi)*(1+.055*math.cos(5*theta))*(1+.08*math.cos(phi))
        z=.92*math.cos(phi)-.18*math.exp(-(phi/.22)**2)+.10*math.exp(-((phi-math.pi)/.22)**2)
        return (r*math.cos(theta),r*math.sin(theta),z)
    for i in range(12):
        for j in range(20):
            a,b,c,d=point(i,j),point(i,j+1),point(i+1,j),point(i+1,j+1)
            if i>0:mesh.triangle('skin',a,c,b,tuple(unit(v) for v in (a,c,b)))
            if i<11:mesh.triangle('skin',b,c,d,tuple(unit(v) for v in (b,c,d)))
    return mesh


def generate(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for i in range(3):tree_mesh(41+i).save(directory/f'orchard_tree_{i}.dae')
    for stage,color in [('unripe',(.30,.64,.055,1)),('turning',(.94,.73,.08,1)),
                        ('blushing',(.96,.30,.055,1)),('ripe',(.74,.025,.018,1))]:
        apple_mesh(color).save(directory/f'apple_{stage}.dae')


if __name__ == '__main__':
    import sys
    generate(sys.argv[1])
