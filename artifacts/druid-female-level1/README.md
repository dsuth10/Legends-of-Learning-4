# Female druid — level 1

Stylised interpretation of the supplied female druid illustration, modelled in Blender 5.2.1 LTS. The back is inferred from the single front-view reference.

## Deliverables

- `druid_female_level1.blend`: editable character, procedural materials, packed reference image, studio lights and camera. Open the **Druid • Level 1** scene. The pre-existing scene is preserved separately.
- `druid_female_level1.png`: 1200 × 1600 transparent RGBA portrait.
- `druid_three_quarter.png` and `druid_back.png`: additional transparent inspection renders.
- `model_report.json`: measured geometry and render details.

The model includes individual hair locks, shaped facial features, layered shoulder armour, corset lacing, a split coat, boots, articulated fingers and a carved staff with emissive amber filaments. Seven named collections organise the parts. Dimensions use metres.

Leather, suede, cloth, wood and metal use editable procedural PBR node materials, including colour variation and bump detail. They are stored in the Blender file and require no external texture downloads. The reference image is packed for authoring and is not rendered as a background.

## Scope

This is a static, posed, high-detail character model in a stylised game-art look. It is not rigged or optimised for a real-time game. The evaluated mesh has roughly two million triangles, mainly from smooth curves and subdivision. Game deployment would require retopology/decimation, UV unwrapping, texture baking and, if animation is wanted, rigging. No claim of exact facial likeness is made.

## Verification

The saved Blender file was opened in a separate background Blender process and rendered from front, three-quarter and rear angles. Clothing intersections and rear hair coverage were refined after visual inspection. No floor or scenery is present in the character scene; rendered images use a transparent world.

## Authoring scripts

The included Python scripts record the build and refinement stages. `blender_bridge.py` submits an explicitly selected script to the Blender Lab extension at localhost:9876. These are authoring scripts, not an automatically rerun pipeline; repeated refinement runs can accumulate changes. The delivered `.blend` is the final editable source.

To rerender the final source from PowerShell in the repository directory:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background 'artifacts\druid-female-level1\druid_female_level1.blend' --python 'artifacts\druid-female-level1\render_deliverables.py'
```
