import bpy
from mathutils import Matrix
scene=bpy.context.scene
head=bpy.data.objects['Head styling proportions']
for ob in head.children:
    ob.matrix_parent_inverse=Matrix.Translation((0,-.009,-1.5))
bpy.context.view_layer.update()
scene.render.filepath='C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1/druid_preview_v3.png'
bpy.ops.wm.save_as_mainfile(filepath='C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1/druid_female_level1.blend')
result={'head_transform_corrected':True}
