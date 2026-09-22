import bpy, json
from mathutils import Vector
from pathlib import Path
OUT=Path('C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1')
scene=bpy.context.scene
scene.render.filepath=str(OUT/'druid_female_level1.png')
bpy.ops.render.render(write_still=True)
scene.render.resolution_percentage=65
scene.cycles.samples=48
for name,pos in [('three_quarter',(3,-5,2.0)),('back',(2.5,5,2.0))]:
    scene.camera.location=pos
    scene.camera.rotation_euler=(Vector((-.06,0,1.02))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('druid_'+name+'.png'))
    bpy.ops.render.render(write_still=True)
deps=bpy.context.evaluated_depsgraph_get()
triangles=0
for ob in scene.objects:
    if ob.type in {'MESH','CURVE'}:
        ev=ob.evaluated_get(deps); me=ev.to_mesh()
        if me:
            me.calc_loop_triangles(); triangles+=len(me.loop_triangles)
        ev.to_mesh_clear()
(OUT/'model_report.json').write_text(json.dumps({'scene':scene.name,'objects':len(scene.objects),'evaluated_triangles':triangles,'render_size':[1200,1600],'transparent_background':scene.render.film_transparent,'rigged':False,'textures':'Procedural PBR node materials stored in blend; no external texture dependencies','unit':'metre'},indent=2))
