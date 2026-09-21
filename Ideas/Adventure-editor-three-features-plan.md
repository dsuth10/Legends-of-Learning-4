Good news up front: **all three features are almost entirely front-end work** — the backend schemas and PATCH endpoints already support them. Here's a brief plan per feature.

---

# 1. In-UI adventure metadata editing

**What the user can change in the editor:** title, description, theme, background image, end semantics (`all` vs `any` end nodes), and (already wired) the share toggle.

### Backend status — done

- `PATCH /teacher/adventures/{id}` with `AdventureUpdateSchema` already accepts: `title`, `description`, `background_image_url`, `theme`, `width`, `height`, `is_public`, `end_semantics`
- `POST /teacher/adventures/{id}/background` already accepts file upload with MIME/extension/magic-byte validation

### UI work

1. Add a **collapsible "Adventure settings" panel** above the canvas (Bootstrap accordion or modal) in `app/templates/teacher/adventure_editor.html`:
   - Title (text), Description (textarea), Theme (select), End semantics (select: All / Any)
   - Background image: file input → uploads to `/background`, then preview thumbnail
2. In `static/js/adventure_editor.js`:
   - Bind inputs to a single **"Save settings" button** that fires one `PATCH /teacher/adventures/{id}` with only changed fields (Pydantic schema uses `exclude_unset=True`)
   - Use `aria-live="polite"` toast for save confirmation
3. After save, refresh page header (title) and canvas background CSS variable

### Recommended approach

**Modal dialog** triggered by a "⚙ Settings" button next to Refresh/Publish/Assign. Keeps the canvas focused on map-building and avoids cluttering the toolbar. Single PATCH on Save is simpler than per-field auto-save and matches how the API expects it.

### Risks

- Background image preview needs the URL returned by the upload endpoint reflected immediately
- Inline-editing the title in the page header is tempting but doubles the bind surface — prefer the modal first

### Tests

- Extend `tests/test_adventure_routes_teacher.py` with a single `test_patch_adventure_full_metadata` round-trip if not already present (it likely is — check before adding)
- Manual: edit title → reload page → header reflects new title

**Effort:** ~2–3 hours

---

# 2. Drag-to-reposition nodes

**What the user gets:** click-and-drag any node on the canvas to move it; coordinates persist.

### Backend status — done

- `PATCH /teacher/adventures/{id}/nodes/{node_id}` accepts `x` and `y` floats (≥ 0)
- Bumps `adventure.version` if published (already correct behavior)

### UI work — `static/js/adventure_editor.js` only

1. In `renderGraph()`, attach `mousedown` on each node `<g>` instead of just `click`
2. Track drag state at module level: `dragging = { nodeId, startClientX, startClientY, startNodeX, startNodeY, moved }`
3. On `mousedown` (left button): record start, set CSS `cursor: grabbing`, prevent native selection
4. On `mousemove` (on `svg`): translate the `<g>` via `setAttribute('transform', ...)` and update connected edge endpoints in-place (no full re-render — too laggy)
5. On `mouseup`:
   - If `moved < 4px` → treat as click (preserve existing inspector/connect behavior)
   - Else → **debounced PATCH** with rounded `x`, `y`; on success, no re-render needed (we already moved the SVG); on failure, snap back
6. Clamp coordinates to canvas bounds (`0 ≤ x ≤ adventure.width`, same for y)
7. Disable drag in **connect mode** and when `canEdit === false`

### Recommended approach

**Pointer events + transient SVG translate during drag, single PATCH on drop.**

- Don't PATCH on every mousemove — would hammer the server
- Don't re-render the whole graph on each move — would be janky
- Use a `4px` drag threshold so clicks still work for inspector/connect-mode
- Consider `requestAnimationFrame` to throttle move handlers if performance is tight

### Risks

- Edge endpoints must update during drag, not just on drop, or the user sees lines disconnect mid-drag
- Touch / pen input: stick to **pointer events** (not `mousedown`/`touchstart`) for one code path that handles both
- Drag conflicts with edge-click — solved by the click-vs-drag threshold

### Tests

- API test for `PATCH .../nodes/{id}` with `x`/`y` already exists (or trivially add)
- Manual: drag node, refresh page, position persists; drag with `Connect nodes` active does nothing

**Effort:** ~3–4 hours (the trickiest of the three — pointer event edge cases)

---

# 3. Quiz nodes — attach a question set in the UI

**What the user gets:** select a quiz node → dropdown of *their* question sets (mirroring the monster picker for battle nodes).

### Backend status — mostly done

- `AdventureNode.question_set_id` FK exists and is wired into `NodeCreateSchema` / `NodeUpdateSchema`
- Publish validation already warns `QUIZ_NO_QUESTION_SET`

**One missing endpoint:** there's no JSON endpoint to list a teacher's question sets for the editor picker.

### Backend work — small

Add `GET /teacher/adventures/question-sets` (or similar) in `app/routes/adventures/teacher.py`:

```python
@adventures_teacher_bp.route("/question-sets", methods=["GET"])
@login_required
@teacher_required
def list_question_sets():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        return _json_ok({"question_sets": []})
    sets = (QuestionSet.query
            .filter_by(teacher_id=teacher.id, is_active=True)
            .order_by(QuestionSet.title).all())
    return _json_ok({"question_sets": [
        {"id": s.id, "title": s.title, "question_count": s.questions.count()}
        for s in sets
    ]})
```

Note the `QuestionSet.teacher_id` references the legacy `Teacher` table, not `User.id` — lookup must go via `Teacher.query.filter_by(user_id=current_user.id)`. Cache the result on the request for safety.

### UI work

1. In `app/routes/adventures/teacher.py` `read_adventure()`, alongside `monster_options`, build `question_set_options` (same shape) and pass to the template — saves an extra fetch on first render
2. Template `adventure_editor.html` → pass to `AdventureEditor.init({ ... questionSets: ... })`
3. In `renderNodeInspector()`, mirror the battle-node branch:

```js
if (node.node_type === "quiz") {
  // dropdown of question sets, "— pick question set —" default
}
```

4. Save handler: include `question_set_id` in the PATCH payload when the quiz select changes
5. Show a small "Manage question sets" link to `/teacher/education/...` so teachers know where to create new sets

### Recommended approach

**Server-side-render the dropdown options into the page (like monsters)** plus the GET endpoint for completeness/future use. Single render path = one less round trip; the GET endpoint keeps options open for refresh-after-create flows later.

### Risks

- Teacher must have at least one question set to populate the dropdown — show an empty-state message linking to the Education area when the list is empty
- Question sets aren't shareable across teachers — a cloned adventure's quiz nodes may reference a `question_set_id` the new owner doesn't own; on render, show "Question set unavailable (clone or pick your own)"

### Tests

- Add `test_quiz_node_can_attach_question_set` in `tests/test_adventure_routes_teacher.py`: PATCH a quiz node with `question_set_id`, GET graph, assert it's there
- Add `test_list_question_sets_filters_by_teacher` to ensure isolation

**Effort:** ~2 hours

---

## Recommended sequencing

| Order | Feature | Why |
|------:|---------|-----|
| **1** | Quiz question sets | Smallest, unlocks the only currently-broken node type, mirrors existing monster picker (low-risk pattern reuse) |
| **2** | Metadata editing | Quick win for teacher polish (title/description/background actually visible to students); pure form work |
| **3** | Drag-reposition | Highest payoff for editor feel, but trickiest — schedule after the simpler wins |

## Cross-cutting recommendations

- **Keep the inspector pattern.** All three features should reuse `renderNodeInspector` / a new "Adventure settings" modal — avoid scattering input handlers across the template.
- **One PATCH per save click**, not per keystroke. The Pydantic schemas already honor `exclude_unset`, so partial payloads are idempotent and cheap.
- **`adventure.version` bump on published adventures is already handled in the routes** — no extra work for drag or metadata edits.
- **Add a tiny shared `apiPatch` helper** in `adventure_editor.js` that surfaces validation errors to the existing `#editor-validation` banner — all three features need that.
- **Tests:** each feature should add 1–2 route tests + a manual smoke step appended to `specs/001-adventures-map-system/quickstart.md` section 4.

**Total effort estimate: ~7–9 hours of focused work**, mostly JS, with one short Python route addition for the question-sets list.

Want me to start with #1 (quiz question sets) since it's the smallest and unblocks an existing node type?
