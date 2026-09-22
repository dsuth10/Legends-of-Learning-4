import bpy, math
from mathutils import Matrix
OUT='C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1/'
scene=bpy.context.scene
col=next(c for c in scene.collection.children if c.name.startswith('04 Hair'))
head=bpy.data.objects['Head styling proportions']
for k in range(32):
    a=math.pi*.52+math.pi*.96*k/31
    pts=[]
    for j in range(24):
        t=j/23
        x=(.092+.008*math.sin(t*math.tau*2+k*.4))*math.sin(a)
        y=.016+(.09+.008*math.sin(t*math.tau*2+k*.3))*(-math.cos(a))
        z=1.69-.26*t+.012*math.sin(t*math.tau*2+k*.5)
        pts.append((x,y,z))
    data=bpy.data.curves.new('Back flowing hair lock','CURVE'); data.dimensions='3D'; data.bevel_depth=.0065; data.bevel_resolution=3; data.resolution_u=10
    sp=data.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for j,(p,co) in enumerate(zip(sp.bezier_points,pts)):
        p.co=co; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'; p.radius=1 if j<19 else max(.06,(23-j)/4)
    ob=bpy.data.objects.new('Back flowing hair lock',data); col.objects.link(ob); data.materials.append(bpy.data.materials['Hair • '+str(k%3)])
    ob.parent=head; ob.matrix_parent_inverse=Matrix.Translation((0,-.009,-1.5))
for ob in scene.objects:
    if 'trouser leg' in ob.name:
        for v in ob.data.vertices:
            if v.co.z>.87:
                t=min(1,(v.co.z-.87)/.1); v.co.x*=1-.17*t; v.co.y*=1-.2*t
    if ob.name.startswith('Sculpted corset overlay'):
        ob.scale.x=1.055; ob.scale.y=1.055
    if ob.name.startswith('Fitted leather cuirass'):
        for v in ob.data.vertices:
            if v.co.z<1.21:
                v.co.x*=.94; v.co.y*=.94
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=OUT+'druid_female_level1.blend')
result={'rear_hair_and_clothing_intersections_corrected':True}
