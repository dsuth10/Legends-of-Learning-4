# Character Images Structure

This directory contains all character images for the Legends of Learning game. The structure is organized as follows:

```
characters/
├── warrior/              # Warrior class images
│   ├── male/            # Male warrior variants
│   │   ├── level1/      # Level 1 male warriors (3 options)
│   │   ├── level2/      # Level 2 male warriors (3 options)
│   │   └── level3/      # Level 3 male warriors (3 options)
│   └── female/          # Female warrior variants
│       ├── level1/      # Level 1 female warriors (3 options)
│       ├── level2/      # Level 2 female warriors (3 options)
│       └── level3/      # Level 3 female warriors (3 options)
├── sorcerer/            # Sorcerer class images
│   ├── male/           # Male sorcerer variants
│   │   ├── level1/     # Level 1 male sorcerers (3 options)
│   │   ├── level2/     # Level 2 male sorcerers (3 options)
│   │   └── level3/     # Level 3 male sorcerers (3 options)
│   └── female/         # Female sorcerer variants
│       ├── level1/     # Level 1 female sorcerers (3 options)
│       ├── level2/     # Level 2 female sorcerers (3 options)
│       └── level3/     # Level 3 female sorcerers (3 options)
└── druid/              # Druid class images
    ├── male/          # Male druid variants
    │   ├── level1/    # Level 1 male druids (3 options)
    │   ├── level2/    # Level 2 male druids (3 options)
    │   └── level3/    # Level 3 male druids (3 options)
    └── female/        # Female druid variants
        ├── level1/    # Level 1 female druids (3 options)
        ├── level2/    # Level 2 female druids (3 options)
        └── level3/    # Level 3 female druids (3 options)
```

## Image Naming Convention
Each image should follow this naming pattern:
```
{option_number}_{class}_{gender}_level{level}.png
```

Example:
- `1_warrior_male_level1.png`
- `2_sorcerer_female_level2.png`
- `3_druid_male_level3.png`

## Image Specifications
- Format: PNG with transparency
- Resolution: 256x256 pixels
- Color Mode: RGB
- File Size: Optimized for web (target < 100KB per image)

## Total Images Required
- 3 classes (warrior, sorcerer, druid)
- 2 genders (male, female)
- 3 levels (1, 2, 3)
- 3 options per combination
- Total: 3 × 2 × 3 × 3 = 54 unique character images

## Level Progression
- Level 1: Basic appearance
- Level 2: Enhanced appearance with additional details
- Level 3: Advanced appearance with special effects/glow

## Character Class Themes
- Warrior: Armor and weapons
- Sorcerer: Magical effects and robes
- Druid: Nature elements and organic materials 