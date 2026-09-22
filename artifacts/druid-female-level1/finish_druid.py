import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
OUT=Path('C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1')
scene=bpy.context.scene
haircol=next(c for c in scene.collection.children if c.name.startswith('04 Hair'))
head=bpy.data.objects['Head styling proportions']
hairmats=[bpy.data.materials['Hair • '+str(i)] for i in range(4)]
def strand(name,pts,radius,mat):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'; data.resolution_u=12; data.bevel_depth=radius; data.bevel_resolution=3
    sp=data.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for i,(p,co) in enumerate(zip(sp.bezier_points,pts)):
        p.co=co; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'; p.radius=max(.08,math.sin(math.pi*(i+.3)/(len(pts)+.1))**.45)
    ob=bpy.data.objects.new(name,data); haircol.objects.link(ob); data.materials.append(mat)
    ob.parent=head; ob.matrix_parent_inverse=Matrix.Translation((0,-.009,-1.5))
    return ob
for side in [-1,1]:
    for k in range(35):
        ae=side*(.13+2.95*k/34)
        pmax=1.90-.83*max(0,math.cos(ae))**3
        pts=[]
        for j in range(20):
            t=j/19; p=.05+(pmax-.05)*t; a=ae+.18*side*math.sin(math.pi*t)
            pts.append((.095*math.sin(p)*math.sin(a),.014-.104*math.sin(p)*math.cos(a),1.668+.129*math.cos(p)))
        strand('Sculpted crown hair sweep',pts,.0032,hairmats[k%3])
        strand('Crown strand highlight',[(x,y-.0007,z+.0013) for x,y,z in pts],.0006,hairmats[2])

brow=bpy.data.materials.new('Eyebrows • warm dark blonde'); brow.use_nodes=True
brow.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.105,.05,.018,1)
brow.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
for ob in scene.objects:
    if ob.name.startswith('Eyebrow'):
        ob.data.materials.clear(); ob.data.materials.append(brow)
    if ob.name.startswith('High standing collar'):
        for v in ob.data.vertices:
            if v.co.z>1.43: v.co.z+=(v.co.z-1.43)*.6

# A clean active scene, with the reference packed as an image datablock for authoring.
ref=Path('C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/static/images/characters/druid/female/level1/1_druid_female_level1.png')
im=bpy.data.images.load(str(ref),check_existing=True); im.pack()
scene.render.resolution_percentage=100
scene.cycles.samples=96
scene.render.filepath=str(OUT/'druid_female_level1.png')
scene.camera.location=(.70,-5.5,2.0)
scene.camera.rotation_euler=(Vector((-.075,0,1.01))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene['style']='Stylised game character, approved by user. Static posed sculpt with editable procedural PBR materials.'
for ob in bpy.context.selected_objects: ob.select_set(False)
body=next(o for o in scene.objects if o.name.startswith('Fitted leather cuirass'))
body.select_set(True); bpy.context.view_layer.objects.active=body
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.clip_start=.01
            ar.spaces.active.region_3d.view_perspective='CAMERA'
            ar.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'druid_female_level1.blend'))
result={'saved':str(OUT/'druid_female_level1.blend'),'objects':len(scene.objects),'materials':len({m.name for o in scene.objects if hasattr(o.data,'materials') for m in o.data.materials if m})}
