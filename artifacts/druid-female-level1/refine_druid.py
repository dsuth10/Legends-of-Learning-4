import bpy, math, bmesh
from pathlib import Path
from mathutils import Vector
OUT=Path('C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1')
scene=bpy.context.scene

# Keep the underlayer inside the outer leather shells.
ob=next(o for o in scene.objects if o.name.startswith('Linen torso under armour'))
ob.scale.x=.80; ob.scale.y=.72
coat=next(o for o in scene.objects if o.name.startswith('Long split travelling coat'))
bm=bmesh.new(); bm.from_mesh(coat.data); bmesh.ops.reverse_faces(bm,faces=list(bm.faces)); bm.to_mesh(coat.data); bm.free()

# Slightly larger head and eyes for a readable game-character proportion.
head=bpy.data.objects.get('Head styling proportions') or bpy.data.objects.new('Head styling proportions',None)
scene.collection.objects.link(head); head.location=(0,.009,1.5)
face_prefixes=('Face •','Ear','Eyeball','Hazel iris','Pupil','Eye glint','Upper eyelid','Lower eyelid','Fine upper lash','Brow ridge','Eyebrow','Nose','Nostril','Upper lip','Lower lip','Mouth separation')
for ob in list(scene.objects):
    is_hair=any(c.name.startswith('04 Hair') for c in ob.users_collection)
    if is_hair or ob.name.startswith(face_prefixes):
        world=ob.matrix_world.copy(); ob.parent=head; ob.matrix_world=world
head.scale=(1.10,1.08,1.075)

# Recess eyeballs, soften their contrast and broaden the coloured iris.
for ob in scene.objects:
    if ob.name.startswith('Eyeball'):
        ob.location.y+=.0025; ob.scale.z*=.80
    elif ob.name.startswith('Hazel iris'):
        ob.scale.x*=1.17; ob.scale.z*=1.08
        ob.location.y+=.0013
    elif ob.name.startswith('Pupil'):
        ob.scale.x*=1.15; ob.location.y+=.001
    elif ob.name.startswith('Eye glint'):
        ob.location.y+=.001
    elif ob.name.startswith('Face framing ringlet'):
        pts=ob.data.splines[0].bezier_points
        for j in range(5):
            t=j/5
            pts[j].co.x*=.77+.23*t
            pts[j].co.y+=.012*(1-t)

# Make curls less pale and tune materials towards the warm leather reference.
for mat in bpy.data.materials:
    if mat.name.startswith('Hair •'):
        for node in mat.node_tree.nodes:
            if node.type=='VALTORGB':
                for el in node.color_ramp.elements:
                    c=el.color[:]; el.color=(c[0]*.78,c[1]*.69,c[2]*.58,1)
    if mat.name.startswith('Eyes •'):
        mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.40,.36,.28,1)

scene.render.resolution_percentage=70
scene.render.filepath=str(OUT/'druid_preview_v2.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'druid_female_level1.blend'))
result={'refined':True}
