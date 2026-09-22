import bpy, json
from pathlib import Path
OUT=Path('C:/Users/dsuth/Documents/Code Projects/Legends-of-Learning-4/artifacts/druid-female-level1')
checks={}
for name in ['druid_female_level1.png','druid_three_quarter.png','druid_back.png']:
    im=bpy.data.images.load(str(OUT/name),check_existing=False)
    alpha=im.pixels[:][3::4]
    checks[name]={'dimensions':list(im.size),'channels':im.channels,'alpha_min':min(alpha),'alpha_max':max(alpha)}
    bpy.data.images.remove(im)
(OUT/'image_checks.json').write_text(json.dumps(checks,indent=2))
result=checks
