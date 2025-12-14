# Student UI Redesign - Implementation Guide

## Overview

This document details the work completed on the Character page redesign and provides guidance for implementing the remaining pages: **Shop**, **Equipment**, and **Quest**.

**Status:**
- ✅ **Character Page** - Completed and integrated
- ⏳ **Shop Page** - Pending implementation
- ⏳ **Equipment Page** - Pending implementation
- ⏳ **Quest Page** - Pending implementation

---

## What Was Completed

### 1. New Base Template (`base_student.html`)

Created a dedicated base template for student pages with:
- **Tailwind CSS** via CDN (with custom configuration)
- **Google Fonts**: Cinzel (display) and Lato (body)
- **Material Icons** for iconography
- **Dark mode support** (class-based)
- **Custom color palette** matching the design specs
- **Custom scrollbar styles** and utility classes

**Location:** `app/templates/student/base_student.html`

### 2. Shared Header Component (`_student_header.html`)

Created a reusable header component containing:
- **Top bar**: Class name and teacher avatar
- **Clan bar**: Student tabs with HP/PP bars for all classroom members

**Location:** `app/templates/student/_student_header.html`

**Key Features:**
- Displays classroom name or clan name (if character is in a clan)
- Shows all students in the classroom with their HP/PP stats
- Highlights the current student's tab
- Responsive horizontal scrolling for many students

### 3. Character Page Redesign (`character_new.html`)

Redesigned the character page with:
- **Sidebar**: Character stats (HP, PP, XP, GP), navigation buttons, powers grid
- **Main area**: Character model display with background image
- **Party members**: Small character cards for clan members (if in a clan)

**Location:** `app/templates/student/character_new.html`

### 4. Model Updates

**Classroom Model (`app/models/classroom.py`)**
- Added `teacher` relationship: `teacher = db.relationship('User', foreign_keys=[teacher_id], backref='taught_classes')`
- This allows templates to access `classroom.teacher` directly

### 5. Route Updates

**Character Route (`app/routes/student_main.py`)**
- Updated to render `character_new.html` instead of `character.html`
- Added eager loading of teacher relationship
- Ensured `student_profile` is always passed to template context

---

## Architecture & Design Decisions

### Template Structure

All student pages follow this structure:

```html
{% extends "student/base_student.html" %}

{% block title %}Page Name{% endblock %}

{% block content %}
<div class="h-screen flex flex-col overflow-hidden">
    {# Include shared header #}
    {% include "student/_student_header.html" %}
    
    {# Main content area #}
    <div class="flex-1 flex overflow-hidden relative">
        {# Sidebar - shared across all pages #}
        <aside class="w-80 ...">
            {# Character stats (HP, PP, XP, GP) #}
            {# Navigation buttons #}
            {# Page-specific content #}
        </aside>
        
        {# Main content area - page-specific #}
        <main class="flex-1 ...">
            {# Page content #}
        </main>
    </div>
</div>
{% endblock %}
```

### Color Scheme

All colors are defined in Tailwind config and available as utility classes:

- **Primary**: `primary` (`#4f46e5`)
- **HP Red**: `bg-hp-red` (`#ef4444`)
- **PP/AP Blue**: `bg-ap-blue` (`#3b82f6`)
- **XP Yellow**: `bg-xp-yellow` (`#f59e0b`)
- **GP Gold**: `bg-gp-gold` (`#d97706`)
- **Rarity Colors**:
  - Common: `bg-rarity-common` (`#9ca3af`)
  - Rare: `bg-rarity-rare` (`#3b82f6`)
  - Epic: `bg-rarity-epic` (`#a855f7`)
  - Legendary: `bg-rarity-legendary` (`#eab308`)

### Typography

- **Display Font**: `font-display` (Cinzel) - Use for headings, character names
- **Body Font**: `font-body` (Lato) - Use for body text

### Stat Bar Pattern

All stat bars follow this pattern:

```html
<div class="flex items-center">
    <span class="w-8 text-lg font-bold">HP</span>
    {% set max_hp = main_character.total_health %}
    {% set hp_percent = (main_character.health / max_hp * 100) if max_hp > 0 else 0 %}
    <div class="flex-1 h-8 bg-gray-200 rounded-full relative overflow-hidden flex items-center">
        <div class="absolute left-0 top-0 bottom-0 bg-hp-red" style="width: {{ hp_percent }}%"></div>
        <div class="absolute left-1 z-10 w-8 h-6 bg-hp-red rounded-full flex items-center justify-center text-white text-xs font-bold shadow">
            {{ main_character.health }}
        </div>
        <span class="ml-auto mr-2 text-xs text-gray-500 z-10">{{ max_hp }}</span>
    </div>
</div>
```

**Key Points:**
- Use `total_health`/`total_power` (not `max_health`/`max_power`) to include equipment bonuses
- These are `@property` methods on the Character model
- Always check for division by zero

---

## Implementing Remaining Pages

### Page 1: Shop Page

#### Route
- **GET** `/student/shop` - Display shop with items
- **POST** `/student/shop/buy` - Purchase an item

#### Template Location
- Create: `app/templates/student/shop_new.html`

#### Design Reference
- **HTML**: `Ideas/Student UI redesign/Shop Page/code.html`
- **Screenshot**: `Ideas/Student UI redesign/Shop Page/screen.png`

#### Implementation Steps

1. **Create Template Structure**
   ```html
   {% extends "student/base_student.html" %}
   {% include "student/_student_header.html" %}
   ```

2. **Sidebar Content** (similar to Character page)
   - Character stats (HP, PP, XP, GP)
   - Navigation buttons (highlight "Shop")
   - Wallet info at bottom showing current gold

3. **Main Content Area**
   - **Category Filters**: Weapon, Armor, Accessory buttons
   - **Item Grid**: Display items with rarity-colored borders
   - **Item Cards**:
     - Image
     - Name
     - Type & Level requirement
     - Stats (health_bonus, power_bonus, defense_bonus)
     - Price in GP
     - Purchase button (disabled if can't afford/own)

4. **Data Source** (from existing route)
   - `items` list (from route context)
   - Each item has: `id`, `name`, `price`, `category`, `tier` (rarity), `can_buy`, `owned`, etc.

5. **Filtering Logic** (JavaScript)
   - Filter items by category when filter buttons clicked
   - Update grid display accordingly

6. **Purchase Flow**
   - POST to `/student/shop/buy` with `{item_id, item_type}`
   - Update UI on success (remove item or mark as owned, update gold)

#### Key Features to Implement

- **Rarity Borders**: Use `border-rarity-{common|rare|epic|legendary}` classes
- **Category Filtering**: JavaScript to filter `items` array by `category`
- **Purchase Button States**: 
  - Disabled if `!can_buy`
  - Show different text if `owned`
- **Wallet Display**: Show `main_character.gold` at bottom of sidebar

---

### Page 2: Equipment Page

#### Route
- **GET** `/student/character` or create `/student/equipment` route
- **PATCH** `/student/equipment/equip` - Equip an item
- **PATCH** `/student/equipment/unequip` - Unequip an item

#### Template Location
- Create: `app/templates/student/equipment_new.html`

#### Design Reference
- **HTML**: `Ideas/Student UI redesign/Equipment Page/code.html`
- **Screenshot**: `Ideas/Student UI redesign/Equipment Page/screen.png`

#### Implementation Steps

1. **Create Template Structure**
   - Same base structure as Character page
   - Highlight "Equipment" navigation button

2. **Sidebar Content**
   - Character stats
   - Navigation buttons
   - **Stat Changes Panel** at bottom showing total bonuses:
     - Attack (sum of power_bonus)
     - Defense (sum of defense_bonus)

3. **Main Content Area - Inventory Grid**
   - **4-column grid** of inventory items
   - Display items not currently equipped
   - Show item image, rarity border
   - Click to equip (drag-and-drop can be added later)

4. **Character Model with Equipment Slots**
   - Character avatar in center
   - **Equipment slot overlays**:
     - Weapon slot (left side of character)
     - Armor slot (chest area)
     - Accessory slot (right side)
   - Show equipped item icons/images in slots
   - Hover tooltips showing equipment stats

5. **Equip/Unequip Logic**
   - Click inventory item → equip to appropriate slot
   - Click equipped item in slot → unequip
   - Use existing API endpoints:
     - `PATCH /student/equipment/equip` with `{inventory_id, slot}`
     - `PATCH /student/equipment/unequip` with `{inventory_id}`

#### Key Features to Implement

- **Equipment Slot Overlays**: Position absolute divs over character model
- **Inventory Filtering**: Show only `is_equipped=False` items
- **Slot Validation**: Ensure item matches slot type before equipping
- **Real-time Stat Updates**: Update sidebar stats when items equipped/unequipped
- **Visual Feedback**: Highlight selected item, show slot highlight on hover

---

### Page 3: Quest Page

#### Route
- **GET** `/student/quests` - Display quest list and details
- **POST** `/student/quests/start/<quest_id>` - Start a quest
- **POST** `/student/quests/complete/<quest_id>` - Complete/turn in quest

#### Template Location
- Create: `app/templates/student/quests_new.html`

#### Design Reference
- **HTML**: `Ideas/Student UI redesign/Quest Page/code.html`
- **Screenshot**: `Ideas/Student UI redesign/Quest Page/screen.png`

#### Implementation Steps

1. **Create Template Structure**
   - Same base structure with header
   - **Two-column layout**: Quest log sidebar + Main quest details

2. **Sidebar - Quest Log**
   - List of quest cards
   - Each card shows:
     - Quest name
     - Status badge (Active/Ready/New)
     - Progress bar
     - Progress percentage
   - Click quest card to show details in main area

3. **Main Content Area - Quest Details**
   - **Quest Header**:
     - Type badge (Story Quest, Daily, etc.)
     - Time remaining (if deadline exists)
     - Quest title
     - Description (italic, quoted style)
   
   - **Objectives List**:
     - Checkmark for completed objectives
     - Progress number for in-progress
     - Gray for not started
     - Objective text
   
   - **Rewards Section**:
     - XP amount
     - Gold amount
     - Items (if any)
   
   - **Quest Giver Info**:
     - Name (e.g., "Master Archivist")
     - Avatar image
     - Location
   
   - **Action Buttons**:
     - "Continue Quest" (if active) - links to quest activity
     - "Abandon Quest" (if allowed)
     - "Start Quest" (if not started)
     - "Turn In" (if completed)

4. **Data Source** (from existing route)
   - `assigned_quests` list - tuples of (Quest, QuestLog)
   - QuestLog has `status` field: 'not_started', 'in_progress', 'completed'

#### Key Features to Implement

- **Quest Status Logic**:
  - `status == 'in_progress'` → "Active" badge (yellow)
  - `status == 'completed'` → "Ready" badge (green) - can turn in
  - `status == 'not_started'` → "New" badge (gray)
  
- **Progress Calculation**:
  - Parse quest objectives from `quest.completion_criteria` or `quest.objectives`
  - Calculate percentage complete
  - Update progress bar width
  
- **Quest Selection**:
  - JavaScript to show selected quest details
  - Highlight selected quest in sidebar
  
- **Objective Display**:
  - Parse objective data (may be JSON or structured format)
  - Show checkmarks/completion state per objective

---

## Common Patterns & Best Practices

### 1. Sidebar Stats Panel

All pages share the same stats display. Consider extracting to a partial:

**Location**: `app/templates/student/_stats_sidebar.html` (create if needed)

```html
{% if main_character %}
    {# Character header #}
    {# HP, PP, XP, GP bars #}
    {# Navigation buttons #}
{% endif %}
```

### 2. Navigation Button Highlighting

Always highlight the current page's navigation button:

```html
<a href="{{ url_for('student.shop') }}" 
   class="... {{ 'bg-blue-600' if active_page == 'shop' else 'bg-gray-800' }}">
    Shop
</a>
```

Or use a simpler approach - check the current route:

```html
{% set current_route = request.endpoint %}
<a href="{{ url_for('student.shop') }}" 
   class="... {{ 'bg-blue-600' if current_route == 'student.shop' else 'bg-gray-800' }}">
    Shop
</a>
```

### 3. Rarity Color Mapping

Map equipment `rarity` or `tier` values to Tailwind classes:

```python
# In route or template context
RARITY_CLASSES = {
    1: 'rarity-common',
    2: 'rarity-rare', 
    3: 'rarity-epic',
    4: 'rarity-legendary'
}
```

In template:
```html
{% set rarity_class = RARITY_CLASSES.get(item.tier, 'rarity-common') %}
<div class="border-4 border-{{ rarity_class }} ...">
```

### 4. Empty States

Always handle empty states gracefully:

```html
{% if items|length == 0 %}
    <div class="text-center py-12 text-gray-500">
        <p>No items available.</p>
    </div>
{% else %}
    {# Item grid #}
{% endif %}
```

### 5. Loading States

For API calls, show loading indicators:

```javascript
async function purchaseItem(itemId) {
    const button = event.target;
    button.disabled = true;
    button.textContent = 'Purchasing...';
    
    try {
        const response = await fetch('/student/shop/buy', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_id: itemId, item_type: 'equipment'})
        });
        const data = await response.json();
        
        if (data.success) {
            // Update UI
            updateGoldDisplay(data.character.gold);
            markItemAsOwned(itemId);
        } else {
            alert(data.error || 'Purchase failed');
        }
    } catch (error) {
        alert('Error purchasing item');
    } finally {
        button.disabled = false;
        button.textContent = 'Purchase';
    }
}
```

### 6. Error Handling

Always handle errors gracefully in templates:

```html
{% if main_character %}
    {# Show character data #}
{% else %}
    <div class="p-6 text-center">
        <p class="text-gray-500">No character created yet.</p>
        <a href="{{ url_for('student.character_create') }}" 
           class="mt-4 inline-block bg-green-500 ...">
            Create Character
        </a>
    </div>
{% endif %}
```

### 7. Responsive Design

Use Tailwind responsive classes where needed:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    {# Item grid adapts to screen size #}
</div>
```

---

## Testing Checklist

For each page implementation, verify:

- [ ] Page loads without errors
- [ ] Header and clan bar display correctly
- [ ] Sidebar stats are accurate (using `total_health`/`total_power`)
- [ ] Navigation buttons work and highlight correctly
- [ ] Page-specific content displays correctly
- [ ] Empty states handled gracefully
- [ ] API calls work (purchase, equip, start quest, etc.)
- [ ] UI updates after actions (gold decreases, items marked as owned, etc.)
- [ ] Dark mode works (if implemented)
- [ ] Mobile responsiveness (if required)

---

## Route Context Variables

Ensure these variables are available in all route templates:

- `student_profile` - Student model instance
- `main_character` - Active Character instance
- `current_user` - Current User (from Flask-Login)

Additional variables may be needed per page (e.g., `items` for shop, `assigned_quests` for quests).

---

## API Endpoints Reference

### Shop
- `POST /student/shop/buy`
  - Request: `{"item_id": int, "item_type": "equipment"|"ability"}`
  - Response: `{"success": bool, "character": {...}, "item": {...}}`

### Equipment
- `PATCH /student/equipment/equip`
  - Request: `{"inventory_id": int, "slot": str}`
  - Response: `{"success": bool}`
  
- `PATCH /student/equipment/unequip`
  - Request: `{"inventory_id": int}`
  - Response: `{"success": bool}`

### Quests
- `POST /student/quests/start/<quest_id>`
  - Response: `{"success": bool, "quest_log": {...}}`
  
- `POST /student/quests/complete/<quest_id>`
  - Response: `{"success": bool, "rewards": {...}}`

---

## Troubleshooting

### Issue: Teacher avatar not showing
**Solution**: Ensure `classroom.teacher` relationship is loaded. The Classroom model now has this relationship defined.

### Issue: Stats showing incorrect values
**Solution**: Use `total_health`/`total_power` instead of `max_health`/`max_power` to include equipment bonuses.

### Issue: Template not found
**Solution**: Ensure template file is in `app/templates/student/` and route references correct filename.

### Issue: Tailwind classes not applying
**Solution**: Check that `base_student.html` extends properly and Tailwind CDN is loading. Hard refresh browser (Ctrl+Shift+R).

### Issue: Student tabs not showing
**Solution**: Ensure `classroom.student_members` relationship exists and is being accessed correctly. The header template uses `classroom.student_members.all()` to get Student objects.

---

## Next Steps

1. **Implement Shop Page** - Start with template structure, then add filtering and purchase logic
2. **Implement Equipment Page** - Focus on inventory grid and equip/unequip functionality
3. **Implement Quest Page** - Quest log sidebar and quest details display
4. **Extract Shared Components** - Consider creating `_stats_sidebar.html` partial for reuse
5. **Add Animations** - Add smooth transitions for page changes and interactions
6. **Mobile Optimization** - Ensure all pages work on mobile devices
7. **Testing** - Add integration tests for new pages and API interactions

---

## Design Assets Location

All design references are in:
- `Ideas/Student UI redesign/Character Page/`
- `Ideas/Student UI redesign/Shop Page/`
- `Ideas/Student UI redesign/Equipment Page/`
- `Ideas/Student UI redesign/Quest Page/`

Each folder contains:
- `code.html` - HTML structure reference
- `screen.png` - Visual design reference

---

## Additional Documentation

- **API Mapping**: See `docs/student-ui-redesign-mapping.md` for detailed API endpoint mappings
- **Database Structure**: See `.cursor/rules/database-structure.mdc` for model relationships
- **Project Structure**: See `.cursor/rules/project-structure.mdc` for directory layout

---

## Questions or Issues?

If you encounter issues or have questions during implementation:
1. Check existing Character page implementation as a reference
2. Review design HTML files for structure hints
3. Check Flask route code for available context variables
4. Verify database models have required relationships
5. Check browser console for JavaScript errors
6. Check Flask terminal for server-side errors

Good luck with the implementation! 🚀
