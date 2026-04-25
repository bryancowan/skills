# Text-to-3D Prompting Guide (Meshy, Tripo, Rodin)

## Overview
Text-to-3D tools generate meshes from a text description. Output quality depends on style keyword + clear subject + key features + material + technical spec. Always specify intended export format and use case (game engine, 3D printing, web).

## Tool selection
- **Meshy**: best for game assets and teams. Game-asset prompts work best here.
- **Tripo**: fastest for clean topology. Use for rapid prototyping and concept assets.
- **Rodin**: highest quality for photorealistic prompts. Slower and more expensive.

## Key principles
- Lead with style keyword: `low-poly`, `realistic`, `stylized cartoon`, `voxel`, `PBR`.
- Then subject + key features + primary material + texture detail.
- Negative prompt is supported on all three — use it for: "no background, no base, no floating parts, no extra limbs".
- Specify export use: game engine (GLB/FBX), 3D printing (STL), web (GLB).
- For characters: specify A-pose or T-pose if the model will be rigged.

## Template

```
Style: [low-poly / realistic / stylized cartoon / voxel / PBR]
Subject: [main object or character]
Key Features: [distinguishing details, count of major parts]
Material: [primary material — wood, metal, fabric, ceramic, organic]
Texture Detail: [smooth / weathered / hand-painted / photorealistic]
Pose (characters only): [A-pose / T-pose / action pose]
Negative: no background, no base, no floating parts, no extra limbs

Export Use: [Unity GLB / Unreal FBX / 3D printing STL / web GLB]
Polycount Target: [low: <5k / mid: 5-20k / high: 20k+]
```

## Example (Meshy, game asset)
```
Style: stylized cartoon, low-poly
Subject: medieval wooden treasure chest with iron banding
Key Features: hinged lid, padlock on front, four iron corner brackets, slightly weathered
Material: oak wood with darkened iron fittings
Texture Detail: hand-painted, slight wear on edges
Negative: no background, no base, no floating parts, no chains, no extra locks

Export Use: Unity GLB
Polycount Target: low (<3k)
```

## Anti-patterns
- No style keyword → tool defaults to a generic "realistic" interpretation, often poor quality
- Vague material ("wood") → ignores grain, color, finish
- No negative prompt → floating debris, extra bases, background geometry
- No export target → mesh may not import cleanly into target engine
- Skipping pose for characters → model arrives in unusable pose for rigging
