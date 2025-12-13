# Equipment Data System Documentation

## Overview
This document explains the structure and management of the hardcoded equipment data system for the Legends of Learning shop. It covers how to add or modify equipment items, the relationship between equipment data and image assets, and important conventions—especially the use of "Sorcerer" (not "Mage") for class restrictions.

---

## Equipment Data Structure
Equipment items are defined in a Python module (e.g., `equipment_data.py`) as a list of dictionaries, each representing an item. Each entry should include the following fields:

| Field              | Type     | Required | Description                                                                 |
|--------------------|----------|----------|-----------------------------------------------------------------------------|
| `id`               | int/str  | Yes      | Unique identifier for the equipment item                                    |
| `name`             | str      | Yes      | Name of the equipment item                                                  |
| `description`      | str      | Yes      | Description of the item                                                     |
| `type`             | str      | Yes      | Equipment type: `weapon`, `armor`, `accessory`                             |
| `slot`             | str      | Yes      | Equipment slot: e.g., `MAIN_HAND`, `CHEST`, `RING`                         |
| `class_restriction`| str/list | No       | Restricts item to a class or classes: `Warrior`, `Sorcerer`, `Druid`       |
| `level_requirement`| int      | No       | Minimum character level required to use the item                            |
| `cost`             | int      | Yes      | Gold cost of the item                                                      |
| `health_bonus`     | int      | No       | Bonus to health stat                                                       |
| `power_bonus`   | int      | No       | Bonus to power stat                                                     |
| `defense_bonus`    | int      | No       | Bonus to defense stat                                                      |
| `rarity`           | str      | No       | Rarity label (e.g., `common`, `rare`, `epic`)                              |
| `image_url`        | str      | Yes      | Path to the item's image (relative to `static/` assets)                    |

> **Note:** The schema is extensible. You may add new fields as needed, but document them clearly.

---

## Adding or Modifying Equipment Items
1. **Open** the `equipment_data.py` module (usually in `app/models/`).
2. **Locate** the list or dictionary where equipment items are defined (e.g., `EQUIPMENT_DATA`).
3. **Add a new dictionary** for each new item, or modify an existing one. Ensure all required fields are present.
4. **Set `class_restriction` to one of:**
   - `"Warrior"`
   - `"Sorcerer"` (use this for magic-users; do NOT use `"Mage"`)
   - `"Druid"`
   - Or a list, e.g., `["Warrior", "Druid"]`
5. **Choose an appropriate image** and set the `image_url` field (see below).
6. **Save** the file. On app restart, the equipment table will be updated to match the hardcoded data.

---

## Example Equipment Entries
### Sorcerer-Specific Item
```python
{
    "id": 101,
    "name": "Sorcerer's Staff",
    "description": "A staff imbued with arcane power, usable only by Sorcerers.",
    "type": "weapon",
    "slot": "MAIN_HAND",
    "class_restriction": "Sorcerer",  # Use 'Sorcerer', not 'Mage'
    "level_requirement": 3,
    "cost": 250,
    "health_bonus": 0,
    "power_bonus": 0,
    "defense_bonus": 2,
    "rarity": "rare",
    "image_url": "static/equipment/sorcerer_staff.png"
}
```

### Multi-Class Item
```python
{
    "id": 102,
    "name": "Enchanted Cloak",
    "description": "A cloak that can be worn by Sorcerers or Druids.",
    "type": "armor",
    "slot": "CHEST",
    "class_restriction": ["Sorcerer", "Druid"],
    "level_requirement": 2,
    "cost": 180,
    "health_bonus": 10,
    "defense_bonus": 3,
    "rarity": "uncommon",
    "image_url": "static/equipment/enchanted_cloak.png"
}
```

---

## Image Asset Guidelines
- All equipment images should be placed in the `static/equipment/` directory (or as configured in your project).
- Use clear, descriptive filenames (e.g., `sorcerer_staff.png`).
- Ensure the `image_url` in each equipment entry matches the relative path to the image.
- Optimise images for web (small file size, appropriate dimensions).
- If an image is missing, the UI may display a placeholder or broken image icon.

---

## Troubleshooting
- **Item not appearing in shop:**
  - Check that all required fields are present and valid.
  - Ensure the item's `class_restriction` matches the character's class.
  - Verify the `image_url` is correct and the image file exists.
  - Confirm the app was restarted after editing `equipment_data.py`.
- **Image not displaying:**
  - Check the file path and filename for typos.
  - Ensure the image is in the correct directory and accessible by the web server.
- **Class restriction not working:**
  - Make sure you use `"Sorcerer"` (not `"Mage"`).
  - For multi-class items, use a list of class names.
- **Legacy items referencing 'Mage':**
  - Update all such entries to use `"Sorcerer"`.
  - Rename any images or descriptions as needed.

---

## Migration Notes: 'Mage' → 'Sorcerer'
- The magic-user class is now called `Sorcerer` throughout the system.
- Update any old equipment entries, image filenames, and UI labels from `Mage` to `Sorcerer`.
- If you encounter legacy data or code referencing `Mage`, refactor it to use `Sorcerer` for consistency.
- Example: `"Mage Staff"` → `"Sorcerer Staff"`, `class_restriction: "Mage"` → `class_restriction: "Sorcerer"`

---

## Naming Guidelines for Sorcerer Equipment
- Use "Sorcerer" in item names and descriptions for clarity (e.g., "Sorcerer's Wand").
- Avoid using "Mage" in any new equipment entries.
- Be consistent with naming conventions across all equipment types.

---

## Adding New Equipment: Quick Checklist
- [ ] Add a new dictionary entry in `equipment_data.py` with all required fields
- [ ] Use `"Sorcerer"` for magic-user class restrictions
- [ ] Place the image in `static/equipment/` and set the correct `image_url`
- [ ] Restart the app to populate the Equipment table
- [ ] Test in the shop and character equipment UI

---

## Contact & Further Help
For questions or to report issues with the equipment data system, contact the project maintainers or refer to the main project documentation. 