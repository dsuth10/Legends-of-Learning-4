"""Reference-led female druid, editable meshes and procedural PBR materials.
Run in Blender 5.2. Dimensions are metres. Front is -Y.
"""
import bpy
import math
import random
from mathutils import Vector
from pathlib import Path

random.seed(29)
OUT = Path('C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1')
scene = bpy.data.scenes.new('Druid • Level 1')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
groups = {}
for label in ['01 Anatomy', '02 Leather armour', '03 Cloth and coat', '04 Hair', '05 Staff', '06 Fine details', '07 Studio']:
    col = bpy.data.collections.new(label)
    scene.collection.children.link(col)
    groups[label[:2]] = col

def move(obj, group):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    groups[group].objects.link(obj)
    return obj

def material(name, colour, rough=.5, metal=0, grain=0, scale=100):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*colour, 1)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if grain:
        tex = nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = scale
        tex.inputs['Detail'].default_value = 3
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = .18
        ramp.color_ramp.elements[0].color = (*(c*.58 for c in colour), 1)
        ramp.color_ramp.elements[1].position = .82
        ramp.color_ramp.elements[1].color = (*(min(c*1.24,1) for c in colour), 1)
        links.new(tex.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs[0], bs.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .24
        bump.inputs['Distance'].default_value = grain
        links.new(tex.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs[0], bs.inputs['Normal'])
    return mat

skin = material('Skin • warm ivory', (.57,.315,.205), .47, grain=.00035, scale=160)
skin.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value = .09
lip = material('Lips • muted rose', (.34,.115,.085), .48)
shadow = material('Facial crease', (.105,.036,.023), .7)
ivory = material('Eyes • warm white', (.69,.66,.53), .24)
iris = material('Iris • hazel', (.115,.105,.035), .27)
pupil = material('Pupils', (.009,.006,.004), .16)
leather = material('Cuirass • worn chestnut leather', (.19,.063,.027), .42, grain=.0012, scale=150)
leather_dark = material('Straps • dark oxblood leather', (.073,.025,.014), .46, grain=.0008, scale=130)
coatmat = material('Coat • weathered russet suede', (.255,.095,.037), .8, grain=.001, scale=210)
lining = material('Coat lining • charcoal umber', (.036,.030,.020), .91, grain=.0006, scale=220)
cloth = material('Undertunic • grey olive linen', (.135,.128,.085), .88, grain=.0008, scale=230)
pants = material('Trousers • dark moss twill', (.054,.059,.039), .85, grain=.0008, scale=210)
gold = material('Old brass • chased edges', (.43,.27,.105), .36, .72, grain=.00035, scale=95)
steel = material('Armour • burnished bronze', (.17,.137,.088), .42, .65, grain=.0005, scale=135)
thread = material('Stitching • flax', (.39,.28,.15), .85)
hairmats = [material('Hair • '+str(i), c, .38, grain=.00015, scale=170) for i,c in enumerate([(.43,.245,.091),(.60,.38,.16),(.72,.48,.235),(.34,.175,.055)])]
wood = material('Staff • carved ash', (.105,.052,.019), .57, grain=.001, scale=45)
glow = material('Staff • amber magic', (1,.45,.035), .25)
bs = glow.node_tree.nodes.get('Principled BSDF')
bs.inputs['Emission Color'].default_value = (1,.28,.012,1)
bs.inputs['Emission Strength'].default_value = 4

def mesh(name, verts, faces, mat, group, sub=0, solid=0):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob=bpy.data.objects.new(name,data)
    groups[group].objects.link(ob)
    if mat: data.materials.append(mat)
    for p in data.polygons: p.use_smooth=True
    if sub:
        mod=ob.modifiers.new('Smooth tailoring', 'SUBSURF'); mod.levels=sub; mod.render_levels=sub
    if solid:
        mod=ob.modifiers.new('Material thickness','SOLIDIFY'); mod.thickness=solid
    return ob

def uv(name, pos, size, mat, group='01', seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=20, location=pos)
    ob=bpy.context.object; ob.name=name
    ob.scale=size; ob.data.materials.append(mat)
    for p in ob.data.polygons: p.use_smooth=True
    return move(ob,group)

def curve(name, pts, radius, mat, group='06', cyclic=False, radii=None):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'; data.resolution_u=12
    data.bevel_depth=radius; data.bevel_resolution=3
    sp=data.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for i,(p,co) in enumerate(zip(sp.bezier_points,pts)):
        p.co=co; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'
        if radii: p.radius=radii[i]
    sp.use_cyclic_u=cyclic
    ob=bpy.data.objects.new(name,data); groups[group].objects.link(ob); data.materials.append(mat)
    return ob

def limb(name, pts, widths, depths, mat, group='03', n=24):
    verts=[]
    for j,pt in enumerate(pts):
        p=Vector(pt)
        axis=Vector(pts[min(j+1,len(pts)-1)])-Vector(pts[max(j-1,0)])
        axis.normalize(); v=Vector((0,1,0)); u=v.cross(axis).normalized(); v=axis.cross(u).normalized()
        for i in range(n):
            a=2*math.pi*i/n
            verts.append(p+u*(widths[j]*math.cos(a))+v*(depths[j]*math.sin(a)))
    faces=[tuple(range(n-1,-1,-1))]
    for j in range(len(pts)-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.append(tuple((len(pts)-1)*n+i for i in range(n)))
    return mesh(name,verts,faces,mat,group,sub=2)

def torso(name, rings, mat, group='02', detail=0):
    n=64; verts=[]
    for z,rx,ry in rings:
        for i in range(n):
            a=2*math.pi*i/n
            x=rx*math.sin(a); y=-ry*math.cos(a)
            if detail and math.cos(a)>0:
                y-= .022*math.exp(-((abs(x)-.074)/.055)**2-((z-1.322)/.063)**2)*math.cos(a)**2
            verts.append((x,y,z))
    faces=[]
    for j in range(len(rings)-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return mesh(name,verts,faces,mat,group,sub=2,solid=.003)

# Legs, practical boots, layered cloth folds.
for side in [-1,1]:
    x=side*.087
    limb(('Left' if side<0 else 'Right')+' trouser leg',[(x,0,.17),(x,0,.21),(x,.01,.35),(x,.022,.47),(x,.025,.53),(x,.005,.68),(x,0,.88),(side*.075,0,1.025)], [.042,.045,.054,.061,.061,.069,.081,.084],[.047,.05,.054,.064,.064,.073,.085,.083], pants)
    limb('Tall leather boot',[(x,-.005,.035),(x,-.004,.065),(x,0,.18),(x,.007,.28),(x,.012,.37),(x,.012,.39)], [.049,.052,.041,.046,.052,.053],[.057,.057,.046,.047,.051,.052],leather_dark,'02')
    uv('Rounded boot toe',(x,-.055,.057),(.055,.11,.045),leather_dark,'02')
    uv('Boot sole',(x,-.045,.022),(.057,.116,.017),lining,'02')
    for z in [.22,.34,.39]:
        curve('Boot cuff piping',[(x+.053*math.sin(t),.008-.053*math.cos(t),z+.005*math.sin(2*t)) for t in [i*math.tau/32 for i in range(32)]],.003,gold,cyclic=True)
    for k in range(6):
        z=.26+k*.017
        curve('Boot lacing',[(x-.027,-.046,z),(x+.028,-.047,z+.014)],.0015,thread)
    for z in [.43,.455,.49,.61,.67,.72]:
        curve('Trouser fold',[(x-.044,-.028,z+.012),(x,-.06,z),(x+.041,-.029,z+.007)],.004,pants,'03')

# Split skirt: wrap-around back and two articulated front panels.
def coat_surface(name, start,end, mat):
    verts=[]; rows=18; cols=64
    for j in range(rows):
        t=j/(rows-1); z=1.048-.935*t
        rx=.15+.155*t; ry=.094+.087*t
        for i in range(cols):
            a=start+(end-start)*i/(cols-1)
            fold=(.005+.011*t)*math.sin(a*15+.4*t)+.004*t*math.sin(a*29)
            verts.append(((rx+fold)*math.sin(a),-(ry+fold)*math.cos(a),z+.026*t*t*math.cos(a*5)))
    faces=[(j*cols+i,j*cols+i+1,(j+1)*cols+i+1,(j+1)*cols+i) for j in range(rows-1) for i in range(cols-1)]
    ob=mesh(name,verts,faces,mat,'03',sub=1,solid=.004)
    ob.data.materials.append(lining); ob.modifiers[-1].material_offset=1
    for col in [0,cols-1]: curve('Coat bound edge',[verts[j*cols+col] for j in range(rows)],.0035,leather_dark)
    return ob
coat_surface('Long split travelling coat',.58,math.tau-.58,coatmat)
for side in [-1,1]:
    pts=[]
    for j in range(18):
        t=j/17; z=1.04-.91*t; x=side*(.085+.08*t); y=-.103-.075*t
        pts.extend([(x-side*.025,y-.004*math.sin(j),z),(x+side*.025,y+.008,z+.003)])
    ob=mesh('Embroidered hanging front facing',pts,[(2*j,2*j+1,2*j+3,2*j+2) for j in range(17)],leather,'03',sub=2,solid=.003)
    for j in range(15):
        t=(j+.5)/17; x=side*(.085+.08*t); z=1.04-.91*t; y=-.114-.075*t
        curve('Facing vine embroidery',[(x,y,z+.021),(x+side*.012,y,z+.01),(x,y,z),(x-side*.009,y,z-.012)],.0012,thread)

torso('Linen torso under armour',[(1.01,.123,.082),(1.12,.113,.08),(1.30,.17,.105),(1.395,.164,.073),(1.44,.069,.053)],cloth,'03')
torso('Fitted leather cuirass',[(1.045,.119,.088),(1.085,.121,.084),(1.155,.103,.078),(1.22,.117,.087),(1.30,.148,.099),(1.34,.159,.092),(1.382,.15,.075),(1.397,.14,.068)],leather,detail=1)
torso('Sculpted corset overlay',[(1.025,.13,.091),(1.055,.121,.087),(1.12,.104,.082),(1.175,.108,.084),(1.20,.113,.087)],leather_dark)
for side in [-1,1]:
    for x in [.03,.058,.082,.101]:
        curve('Corset raised boning',[(side*x*1.17,-.094*math.sqrt(max(.1,1-(x/.14)**2)),1.043),(side*x,-.091*math.sqrt(max(.1,1-(x/.13)**2)),1.12),(side*x*1.08,-.102*math.sqrt(max(.1,1-(x/.14)**2)),1.196)],.0024,gold)
    curve('Breastplate contour',[(side*.01,-.100,1.224),(side*.072,-.116,1.259),(side*.127,-.105,1.312),(side*.124,-.079,1.377)],.003,gold)
    curve('Breastplate seam',[(side*.041,-.095,1.218),(side*.101,-.105,1.269),(side*.144,-.077,1.333)],.0018,thread)
for j in range(7):
    z=1.055+j*.02
    for side in [-1,1]: uv('Corset brass eyelet',(side*.023,-.095,z),(.0038,.002,.0038),gold,'06',16)
    if j<6:
        curve('Cross laced corset',[(-.023,-.099,z),(.024,-.100,z+.020)],.0019,thread)
        curve('Cross laced corset',[(.023,-.098,z),(-.024,-.10,z+.020)],.0019,thread)

# Hip belt following the armour, with riveted tabs.
verts=[]
for i in range(65):
    a=math.tau*i/64; x=.148*math.sin(a); y=-.111*math.cos(a); z=1.028-.09*x
    verts.extend([(x,y,z-.023),(x,y,z+.023)])
mesh('Wide diagonal leather belt',verts,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(64)],leather_dark,'02',sub=1,solid=.004)
curve('Belt buckle',[(-.033,-.119,1.005),(.032,-.119,1.005),(.032,-.119,1.05),(-.033,-.119,1.05)],.004,gold,cyclic=True)
curve('Buckle tongue',[(0,-.123,1.006),(0,-.123,1.045)],.0025,gold)
for side in [-1,1]:
    for j in range(3):
        x=side*(.05+j*.035); z=.976+j*.006; y=-.108+j*.01
        plate=mesh('Overlapping hip armour tab',[(x-.026,y,z+.042),(x+.026,y,z+.042),(x+.034,y-.009,z-.022),(x,y-.02,z-.038),(x-.032,y-.009,z-.022)],[(0,1,2,3,4)],leather,'02',solid=.005)
        bevel=plate.modifiers.new('Rounded plate edges','BEVEL'); bevel.width=.004; bevel.segments=3
        for dx in [-.017,.017]: uv('Hip rivet',(x+dx,y-.007,z+.022),(.003,.002,.003),gold,'06',16)

# Neck and sculpted face.
limb('Neck',[(0,.003,1.405),(0,.003,1.435),(0,.009,1.48),(0,.012,1.535)], [.048,.045,.039,.047],[.04,.038,.038,.042],skin,'01')
torso('High standing collar',[(1.39,.073,.055),(1.411,.060,.051),(1.454,.052,.045),(1.467,.052,.044)],leather_dark)
for side in [-1,1]: curve('Collar gold edge',[(side*.007,-.05,1.394),(side*.038,-.039,1.445),(side*.05,-.022,1.468)],.002,gold)
profile=[(1.500,.013,.019,.018),(1.51,.033,.039,.022),(1.53,.052,.057,.038),(1.555,.067,.066,.049),(1.585,.077,.071,.063),(1.615,.086,.074,.077),(1.645,.087,.069,.085),(1.671,.085,.071,.088),(1.704,.084,.073,.089),(1.735,.076,.069,.078),(1.763,.055,.049,.057),(1.781,.012,.010,.013)]
def interp(z,k):
    for i in range(len(profile)-1):
        if profile[i][0]<=z<=profile[i+1][0]:
            t=(z-profile[i][0])/(profile[i+1][0]-profile[i][0]); return profile[i][k]*(1-t)+profile[i+1][k]*t
    return profile[-1][k]
verts=[]; nr=75; ns=96
for j in range(nr):
    z=1.5+.281*j/(nr-1); rx=interp(z,1); front=interp(z,2); back=interp(z,3)
    for i in range(ns):
        a=math.tau*i/ns; x=rx*math.sin(a); c=math.cos(a); y=-(front if c>0 else back)*c+.009
        if c>0:
            y-=c**6*(.007*math.exp(-((abs(x)-.047)/.022)**2-((z-1.614)/.023)**2)+.006*math.exp(-((abs(x)-.040)/.027)**2-((z-1.672)/.012)**2))
            y+=c**6*.008*math.exp(-((abs(x)-.041)/.020)**2-((z-1.651)/.010)**2)
            y-=c**8*.004*math.exp(-(x/.03)**2-((z-1.547)/.015)**2)
        verts.append((x,y,z))
faces=[(j*ns+i,j*ns+(i+1)%ns,(j+1)*ns+(i+1)%ns,(j+1)*ns+i) for j in range(nr-1) for i in range(ns)]
mesh('Face • shaped jaw cheeks brow and eye sockets',verts,faces,skin,'01',sub=1)
for side in [-1,1]:
    uv('Ear',(side*.085,.005,1.623),(.017,.012,.03),skin)
    uv('Ear concha',(side*.091,-.006,1.623),(.007,.003,.018),lip)
    x=side*.0405
    uv('Eyeball',(x,-.0615,1.650),(.023,.013,.0105),ivory)
    uv('Hazel iris',(x,-.0735,1.650),(.008,.0026,.008),iris)
    uv('Pupil',(x,-.0757,1.650),(.0037,.0012,.0047),pupil)
    uv('Eye glint',(x-.0022,-.077,1.653),(.0017,.0008,.0017),ivory,'01',16)
    for upper in [True,False]:
        pts=[]
        for j in range(13):
            t=j/12; dx=-.022+.044*t; zz=(.009 if upper else -.006)*math.sin(math.pi*t)
            pts.append((x+dx,-.063-.010*math.sin(math.pi*t),1.650+zz+side*dx*.06))
        curve('Upper eyelid' if upper else 'Lower eyelid',pts,.0026,skin,'01')
        if upper: curve('Fine upper lash line',[(a,b-.0015,c-.0007) for a,b,c in pts],.0009,shadow,'01')
    curve('Brow ridge',[(side*.018,-.064,1.674),(side*.039,-.069,1.68),(side*.061,-.055,1.674)],.004,skin,'01')
    curve('Eyebrow',[(side*.020,-.069,1.676),(side*.035,-.073,1.68),(side*.049,-.069,1.678),(side*.063,-.058,1.672)],.0027,hairmats[3],'01',radii=[.7,1,.85,.2])
    uv('Nose wing',(side*.009,-.076,1.609),(.008,.008,.0055),skin)
    uv('Nostril',(side*.008,-.081,1.607),(.003,.0017,.0018),shadow)
# Nose is a tapered continuous mesh rather than a sphere.
limb('Nose bridge and tip',[(0,-.061,1.671),(0,-.067,1.653),(0,-.077,1.627),(0,-.089,1.615),(0,-.086,1.608)], [.006,.006,.007,.010,.006],[.006,.007,.009,.009,.004],skin,'01')
curve('Upper lip',[(-.022,-.059,1.575),(-.011,-.065,1.578),(0,-.066,1.576),(.011,-.065,1.578),(.022,-.059,1.575)],.0035,lip,'01',radii=[.15,.85,.7,.85,.15])
curve('Lower lip',[(-.021,-.060,1.573),(0,-.066,1.570),(.021,-.060,1.573)],.0041,lip,'01',radii=[.1,1,.1])
curve('Mouth separation',[(-.021,-.063,1.574),(0,-.070,1.574),(.021,-.063,1.574)],.0009,shadow,'01')

# Sleeves follow the asymmetric reference pose, the left hand grips the staff.
armdata=[(-1,[(-.158,.005,1.382),(-.189,.003,1.343),(-.224,-.005,1.27),(-.265,-.025,1.19),(-.318,-.055,1.188),(-.383,-.077,1.228),(-.426,-.08,1.238)]), (1,[(.158,.005,1.382),(.189,.006,1.34),(.212,.005,1.25),(.243,-.014,1.17),(.266,-.028,1.10),(.291,-.045,1.014),(.299,-.05,.987)])]
for side,pts in armdata:
    limb('Linen sleeve • '+str(side),pts,[.058,.058,.05,.046,.042,.032,.029],[.061,.06,.048,.045,.043,.033,.029],cloth)
    # Bracer lies along the last forearm segment.
    start=Vector(pts[-3]); end=Vector(pts[-1]); axis=end-start
    brpts=[start+axis*t for t in [.04,.08,.84,.94]]
    limb('Embossed leather forearm bracer',brpts,[.047,.048,.035,.034],[.046,.047,.035,.034],leather,'02')
    for t in [.08,.27,.78,.92]:
        p=start+axis*t; ax=axis.normalized(); u=Vector((0,1,0)).cross(ax).normalized(); v=ax.cross(u)
        r=.048*(1-t)+.034*t
        curve('Bracer edge and retaining straps',[p+r*(math.cos(a)*u+math.sin(a)*v) for a in [j*math.tau/32 for j in range(32)]],.003,gold,cyclic=True)
    for k in range(5):
        t=k/5; p=Vector(pts[2]).lerp(Vector(pts[3]),t)
        curve('Sleeve gathered wrinkle',[(p.x-.027,p.y-.036,p.z+.01),(p.x,p.y-.049,p.z),(p.x+.027,p.y-.031,p.z-.008)],.003,cloth,'03')

# Layered shoulder pauldrons: shell patches and scalloped rims.
for side in [-1,1]:
    for layer in range(3):
        verts=[]; rows=9; cols=25
        cx=side*(.156+layer*.009); cz=1.395-layer*.025
        for j in range(rows):
            p=.14+(1.32-.14)*j/(rows-1)
            for i in range(cols):
                a=-math.pi*.60+math.pi*1.20*i/(cols-1)
                verts.append((cx+side*.088*math.sin(p)*math.cos(a),.086*math.sin(p)*math.sin(a),cz+.049*math.cos(p)))
        faces=[(j*cols+i,j*cols+i+1,(j+1)*cols+i+1,(j+1)*cols+i) for j in range(rows-1) for i in range(cols-1)]
        mesh('Layered shoulder plate',verts,faces,steel if layer==0 else leather,'02',sub=1,solid=.006)
        curve('Pauldron chased rim',verts[-cols:],.003,gold)
        for k in [2,6,12,18,22]: uv('Shoulder rivet',Vector(verts[-cols+k])+Vector((0,0,.004)),(.0038,.0038,.0038),gold,'06',16)

# Hands: individual fingers with joint shaping.
uv('Left gripping palm',(-.449,-.079,1.237),(.032,.025,.041),skin)
for j in range(4):
    z=1.214+j*.014
    limb('Left curled finger '+str(j),[(-.435,-.10,z),(-.46,-.117,z),(-.480,-.100,z-.002),(-.479,-.082,z-.005)], [.007,.007,.006,.0055],[.007,.007,.006,.0055],skin,'01',16)
limb('Left opposing thumb',[(-.429,-.074,1.257),(-.436,-.11,1.27),(-.461,-.115,1.258)],[.010,.009,.007],[.011,.01,.007],skin,'01',16)
uv('Right palm',(.309,-.054,.946),(.027,.02,.047),skin)
for j in range(4):
    x=.291+j*.013; z=.922+(abs(j-1.5))*.005
    limb('Right finger '+str(j),[(x,-.06,z),(x+.004,-.065,z-.028),(x+.002,-.077,z-.049),(x-.003,-.079,z-.052)],[.0065,.006,.0053,.0038],[.0065,.006,.005,.0038],skin,'01',16)
    uv('Fingernail',(x+.001,-.082,z-.045),(.0035,.001,.007),thread,'06',16)
limb('Right thumb',[(.291,-.059,.958),(.277,-.071,.937),(.275,-.078,.918)],[.010,.008,.006],[.009,.008,.006],skin,'01',16)

# Druid talisman and oak-leaf filigree.
curve('Necklace chain',[(-.043,-.04,1.46),(-.032,-.061,1.40),(0,-.094,1.373),(.032,-.061,1.40),(.043,-.04,1.46)],.0015,gold)
uv('Amber amulet',(0,-.101,1.367),(.010,.005,.016),gold,'06')
uv('Amber inset',(0,-.107,1.367),(.0065,.003,.010),wood,'06')
for z in [1.342,1.235]:
    for side in [-1,1]:
        for j in range(3):
            x=side*(.005+j*.006); zz=z+j*.008
            curve('Oak leaf breastplate ornament',[(x,-.108,zz),(x+side*.009,-.11,zz+.003),(x+side*.005,-.11,zz+.013),(x,-.108,zz)],.0016,gold)

# Hair cap, sculpted waves and fine strand highlights.
verts=[]; rows=20; cols=96
for j in range(rows):
    t=j/(rows-1)
    for i in range(cols):
        a=math.tau*i/cols
        front=max(0,math.cos(a))
        pmax=1.90-.83*front**3
        p=.015+(pmax-.015)*t
        verts.append((.092*math.sin(p)*math.sin(a),.014-.100*math.sin(p)*math.cos(a),1.668+.126*math.cos(p)))
mesh('Scalp with swept hairline',verts,[(j*cols+i,j*cols+(i+1)%cols,(j+1)*cols+(i+1)%cols,(j+1)*cols+i) for j in range(rows-1) for i in range(cols)],hairmats[0],'04',sub=1)
for side in [-1,1]:
    for k in range(29):
        t=k/28; rootx=side*(.006+.027*t); rootz=1.785-.040*t
        endz=1.425+.11*t+.02*math.sin(k)
        pts=[]
        for j in range(16):
            u=j/15
            x=side*(.014+.084*math.sin(u*math.pi*.69)+.008*math.sin(u*math.pi*5+k*.5))
            if j==0: x=rootx
            y=(-.058+.088*t)*(1-u)+(-.020+.067*t)*u-.008*math.sin(u*math.pi*6+k*.8)
            z=rootz+(endz-rootz)*u+.012*math.sin(u*math.pi*4+k*.6)
            pts.append((x,y,z))
        radius=.0068+.002*math.sin(k*2)**2
        radii=[.6]+[1]*11+[.85,.65,.4,.06]
        curve('Swept wavy blonde lock',pts,radius,hairmats[k%4],'04',radii=radii)
        for fine in [-1,1]:
            pp=[(x+fine*.0025,y-.005,z+.001) for x,y,z in pts]
            curve('Individual golden strand',pp,.0007,hairmats[2 if k%3 else 0],'04',radii=radii)
    # Face-framing curls stay outside the cheek silhouette.
    for k in range(5):
        pts=[]
        for j in range(28):
            u=j/27; a=u*math.tau*2.3+k*.45
            pts.append((side*(.088+.008*k+.011*math.sin(a)),-.026-.027*u+.011*math.cos(a),1.687-.285*u))
        curve('Face framing ringlet',pts,.0058,hairmats[(k+1)%3],'04',radii=[1]*(len(pts)-3)+[.65,.35,.05])
# Longer over-shoulder braided curl on the staff side.
for k in range(3):
    pts=[]
    for j in range(44):
        u=j/43; a=u*math.tau*4+k*math.tau/3
        pts.append((-.101-.033*u+.010*math.sin(a),-.064-.047*u+.009*math.cos(a),1.57-.237*u))
    curve('Interwoven shoulder braid',pts,.007,hairmats[k],'04',radii=[1]*40+[.8,.6,.3,.08])
curve('Braid binding',[(-.135,-.11,1.36),(-.143,-.12,1.348),(-.135,-.127,1.34),(-.127,-.115,1.348)],.0025,gold,cyclic=True)

# Ash staff with helical carving, a brass lotus cage and floating amber crystal.
sx=-.463; sy=-.082
limb('Ash staff shaft',[(sx,sy,.02),(sx+.005,sy,.10),(sx,sy,.58),(sx,sy,1.23),(sx+.002,sy,1.51),(sx,sy,1.57)],[.012,.014,.011,.013,.014,.017],[.012,.014,.011,.013,.014,.017],wood,'05')
for k in range(2):
    pts=[]
    for j in range(240):
        u=j/239; a=u*math.tau*15+k*math.pi
        pts.append((sx+.014*math.sin(a),sy+.014*math.cos(a),.09+1.43*u))
    curve('Spiral carved staff binding',pts,.0024,leather,'05')
for z in [.045,.060,.075,1.52,1.55,1.58]:
    curve('Staff brass collar',[(sx+.018*math.sin(a),sy+.018*math.cos(a),z) for a in [j*math.tau/32 for j in range(32)]],.003,gold,'05',True)
for k in range(6):
    a=k*math.tau/6
    curve('Lotus crown tine',[(sx,sy,1.58),(sx+.023*math.cos(a),sy+.023*math.sin(a),1.64),(sx+.046*math.cos(a),sy+.046*math.sin(a),1.69),(sx+.026*math.cos(a),sy+.026*math.sin(a),1.665)],.004,gold,'05',radii=[1,1,.15,.1])
verts=[(sx,sy,1.98),(sx,sy,1.86)]
for j in range(6):
    a=j*math.tau/6; verts.append((sx+.018*math.cos(a),sy+.018*math.sin(a),1.91))
crystal=mesh('Faceted amber staff crystal',verts,[(0,2+j,2+(j+1)%6) for j in range(6)]+[(1,2+(j+1)%6,2+j) for j in range(6)],gold,'05')
for p in crystal.data.polygons: p.use_smooth=False
for k in range(3):
    pts=[]
    for j in range(44):
        u=j/43; a=u*math.tau*2+k*math.tau/3; r=.020*(math.sin(math.pi*u)**.7)
        pts.append((sx+r*math.sin(a),sy+r*math.cos(a),1.64+.26*u))
    curve('Rising amber spell filament',pts,.0028,glow,'05',radii=[.15]+[1]*40+[.7,.4,.05])
for j in range(13):
    z=1.65+random.random()*.25
    uv('Floating ember',(sx+random.uniform(-.036,.036),sy+random.uniform(-.022,.022),z),(.0017,.0017,.003),glow,'05',12)

# Studio illumination only; transparent world and no floor geometry.
world=bpy.data.worlds.new('Transparent studio illumination'); scene.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.22,.28,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.35
def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name,pos,power,colour,size):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.color=colour; data.shape='DISK'; data.size=size
    ob=bpy.data.objects.new(name,data); groups['07'].objects.link(ob); ob.location=pos; aim(ob,(0,0,1))
area('Key • large warm softbox',(-2,-3,3.3),230,(1,.83,.66),2.0)
area('Fill • cool softbox',(2,-2,2.2),150,(.68,.80,1),1.8)
area('Rim • hair light',(0,1.3,2.6),260,(1,.79,.49),1.4)
data=bpy.data.cameras.new('Portrait camera'); cam=bpy.data.objects.new('Portrait camera',data); groups['07'].objects.link(cam)
cam.location=(.45,-5.5,2.14); aim(cam,(-.075,0,1.01)); data.type='ORTHO'; data.ortho_scale=2.21; data.lens=70; scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=48; scene.cycles.use_denoising=True
scene.render.resolution_x=1200; scene.render.resolution_y=1600; scene.render.resolution_percentage=60
scene.render.film_transparent=True; scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(OUT/'druid_preview.png')
scene.view_settings.view_transform='AgX'
scene['reference']='static/images/characters/druid/female/level1/1_druid_female_level1.png'
scene['notes']='Single-view reference interpretation. Procedural materials; static posed model; no animation rig. Metres. No background mesh.'
for screen in bpy.data.screens:
    for spacearea in screen.areas:
        if spacearea.type=='VIEW_3D':
            spacearea.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'druid_female_level1.blend'))
result={'scene':scene.name,'objects':len(scene.objects),'blend':str(OUT/'druid_female_level1.blend')}
