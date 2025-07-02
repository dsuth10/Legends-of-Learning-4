# Implementation Plan: Student Quest Map & Assignment Feature

## Overview and Objectives

The goal is to enable students to view and accept quests through an interactive **Quest Map** interface on the `/student/quests` page. Currently, teachers can create quests (with title, description, type, and rewards) via an existing form, and the student quests page is just a static placeholder. We will replace this placeholder with a dynamic map UI showing quest locations named after quest titles. When a student clicks a quest location, a modal popup will display the quest’s details – including the description (i.e. requirements) and the rewards (gold & XP) – and allow the student to **accept** the quest or mark it **complete** to claim rewards. Students should only be able to view/complete quests, **not edit** them (quest editing remains a teacher-only function). The implementation will involve updates to back-end routes, database interactions (using the existing Quest and QuestLog models), and front-end template/CSS/JS changes, focusing on desktop layout (responsive design for mobile can be deferred as “just desktops” is the target).

## Back-End Changes (Routes & Data Handling)

**1. Load Available Quests for the Student:**
We need to fetch quests from the database and pass them to the student quests template. In the `student_bp.route('/quests')` handler (in `app/routes/student.py`), instead of rendering a static page, query the Quest model for all relevant quests. For now, this can be **all quests** in the system (or filtered to those “available” to the student). We can reuse the approach from the teacher’s quest listing, which pulls all quests from the DB. In future, if quests should be class-specific or level-gated, we can filter by `Quest.is_available()` for the student’s character (which checks level requirements, start/end dates, and prerequisite quests). For now, since the teacher UI doesn’t set availability constraints, listing all created quests is acceptable. Be sure to call `db.session.expire_all()` or similar if needed to refresh data (as done in teacher list route).

**2. Get Student’s Quest Status (QuestLogs):**
Retrieve the current student’s active character and their quest logs to determine which quests are **in progress**, **completed**, or not yet started. The `Student` model relates to `Character`, and each character has `quest_logs` (QuestLog entries) for quests they’ve taken on. We can obtain the student’s main character (as done in other student routes) and load their quest logs into a dictionary for quick lookup. For example:

```python
student_profile = Student.query.filter_by(user_id=current_user.id).first()
main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
quests = Quest.query.all()  # or filter by availability
quest_logs = { log.quest_id: log for log in main_char.quest_logs } if main_char else {}
```

This gives us a mapping of quest IDs to QuestLog objects (if any exist) for that student. We will pass `quests` and `quest_logs` into the `render_template('student/quests.html', ...)` context. Using quest\_logs, the template can identify if a quest is already accepted or completed by the student. (On the student dashboard, for instance, they already list current quests by checking `active_quests = main_character.quest_logs.filter_by(status='in_progress').all()` – we’ll provide similar info to the quests page.)

**3. New Routes for Quest Actions (Accept/Complete):**
We will introduce two new POST routes in the student blueprint for quest interactions:

* **Accept Quest** (e.g. `@student_bp.route('/quests/start/<int:quest_id>', methods=['POST'])`): When a student chooses to start a quest, this handler will create a QuestLog entry for that student’s character and mark it as **in progress**. We’ll fetch the Quest by ID (404 if not found), ensure the student’s character exists, and optionally verify the quest is available (level/date not restrictive). If a QuestLog doesn’t already exist for that quest (enforced by the unique constraint on character\_id+quest\_id), create one. By default, a new QuestLog’s status is `NOT_STARTED`. We can then mark it as started by setting `status = IN_PROGRESS` and recording `started_at`. The QuestLog model provides a `start_quest()` method to do this safely, which we can call after adding the log to the session (it will set status and save). After starting, commit the session and perhaps flash a success message (e.g. “Quest accepted!”). Finally, redirect back to the `/student/quests` page so the UI updates (the quest will now appear as active for the student).

* **Complete Quest** (e.g. `@student_bp.route('/quests/complete/<int:quest_id>', methods=['POST'])`): When the student indicates they’ve fulfilled the quest requirements and clicks “Complete”, this handler will mark the quest as completed and grant rewards. It will look up the QuestLog for that student’s character and the given quest\_id. If found and its status is in progress, call the QuestLog’s `complete_quest()` method. This method internally sets the status to **COMPLETED**, timestamps the completion, and **distributes the reward(s)** to the character. The reward distribution logic will add gold and XP to the character automatically via the Reward model’s `distribute()` (for example, adding gold or calling `character.gain_experience()` as defined in the Reward model). After calling `complete_quest()`, commit the session. We’ll flash a message like “Quest completed! You earned X gold and Y XP.” and redirect back to the quests page (or potentially to the dashboard) so the student can see their updated stats and quest status.

Both routes will be protected by `@login_required` and the `@student_required` decorator (to ensure only logged-in students invoke them). They should also double-check that the current user’s character is eligible to modify that quest (though if quests are global and not class-specific, this mainly means checking the QuestLog exists for that character). By using server-side routes and form submissions, we ensure students cannot manipulate quests beyond starting or completing their own – they have no capability to edit quest definitions (those routes are under the teacher blueprint and require teacher role).

## Front-End: Quest Map UI in Student Template

**1. Quest Map Layout:**
We will update the Jinja2 template at `app/templates/student/quests.html` to present a map graphic with quest locations. First, add a suitable **map image** to the project (for example, `static/images/quest_map.png`). This image could be a fantasy map or classroom-themed map where different locations correspond to different quests. In the template, create a container (e.g. a `<div class="position-relative">`) that displays the map image as a background. For example:

```html
<div class="quest-map position-relative" style="background: url('{{ url_for('static', filename='images/quest_map.png') }}') no-repeat center center; background-size: cover; width: 100%; height:600px;">
    ... quest markers will go here ...
</div>
```

Since we are focusing on desktop, we can use a fixed pixel height (e.g. 600px) or a 100% width container to ensure the map displays well on a typical screen. We won’t prioritize responsive scaling for small screens now (“just desktops”), but we will ensure the map container can scroll or adapt minimally if needed on varying monitor sizes.

**2. Placing Quest Markers (Locations):**
Within the map `<div>`, we will overlay clickable quest name labels at specific coordinates. Each quest from the context will be represented as a “location” on the map. We can absolutely position each quest label by using inline CSS or a CSS class with pre-defined coordinates. For simplicity, define a set of coordinates (top/left percentages or pixels) for each quest. For example, if there are only a few quests, we might manually spread them out: one at top-left, one top-right, one bottom-left, etc. If the number of quests is variable, one approach is to distribute them evenly or in a grid pattern. For instance, use an index to calculate positions (e.g. divide the map into a grid or circle points). In code, this could be done by looping with an index and assigning `style="position:absolute; top: X%; left: Y%;"`. Another quick solution is to maintain a small list/array of coordinate pairs for the first N quests. In a more advanced scenario, quest location coordinates could be stored in the database or configured by the teacher, but that’s not currently available. For now, we’ll hardcode or algorithmically determine positions.

Each quest marker will display the **quest title** (so it looks like a location name on the map). We can style these labels to stand out (perhaps a small icon or underlined text). For example:

```html
<div class="quest-marker position-absolute" style="top:40%; left:15%;">
  <a href="#" data-bs-toggle="modal" data-bs-target="#questModal{{ quest.id }}" class="text-warning fw-bold">
    {{ quest.title }}
  </a>
</div>
```

In this snippet, we give the quest title link a distinctive style (e.g. Bootstrap text-warning for visibility on the map background, and maybe `fw-bold` for bold text). We also attach `data-bs-toggle="modal"` and a `data-bs-target` pointing to a modal with an ID unique to this quest (e.g. `#questModal5` for quest ID 5). Each quest will have its own modal defined (see next step). Using Bootstrap’s modal data attributes allows the modal to open without custom JS, when the link is clicked.

Additionally, we can use CSS for the `.quest-marker` class in `static/css/style.css` to enhance appearance (for example, adding a marker icon or adjusting font-size). For instance, we might add:

```css
.quest-marker a { text-shadow: 1px 1px 2px #000; } /* to improve readability on map */
.quest-marker::before { 
    content: "★"; 
    color: gold; 
    position: absolute; left: -20px; 
    /* A star icon marker left of the text */
}
```

This could put a star icon before the quest name as a marker. These visual tweaks can be adjusted as needed. The key is that the quest name is clearly visible on the map and clickable.

**3. Differentiating Quest Status on the Map:**
Using the quest\_logs data, we can visually indicate if a quest is already in progress or completed for the student:

* **Not Started (Available)**: Show normally (e.g. white/yellow text as location name). This is the default for quests with no QuestLog yet.
* **In Progress**: We might highlight or annotate differently (e.g. append “(Active)” after the name, or use a different color icon). For example, if `quest.id` is in `quest_logs` and `quest_logs[quest.id].status == 'in_progress'`, we could add a CSS class or badge like “(Active)”. This tells the student they have already accepted that quest. We could also disable the "Start" option in the modal for an active quest and only allow completion.
* **Completed**: We can grey out the name or add a checkmark icon to signify it’s done. For instance, a completed quest could be displayed with a class that sets `opacity: 0.5` or a ✔️ icon after the name. We will also disable any action buttons in the modal for completed quests (just show “Completed”). We might optionally remove completed quests from the map to reduce clutter, and list them separately under a “Completed Quests” section below the map. However, to keep the interface unified, it’s acceptable to leave them on the map but clearly marked as finished.

In the template, implement this with Jinja conditions. For example:

```jinja
{% if quest.id in quest_logs %}
   {% set qlog = quest_logs[quest.id] %}
   {% if qlog.status.value == 'completed' %}
       <span class="completed-quest">{{ quest.title }} (Completed)</span>
   {% elif qlog.status.value == 'in_progress' %}
       <span class="active-quest">{{ quest.title }} (Active)</span>
   {% else %}
       {{ quest.title }}
   {% endif %}
{% else %}
   {{ quest.title }}
{% endif %}
```

And wrap the appropriate span or text in the `<a>` link. (The Enum `QuestStatus` is a subclass of str, so comparing `qlog.status` to `'completed'` or using `.value` should work.) We will style `.completed-quest` (e.g. gray and strikethrough) and `.active-quest` (e.g. highlight in a different color) via CSS.

**4. Quest Detail Modal:**
For each quest, define a Bootstrap modal in the template. We will use one modal per quest approach for simplicity. Place these modals in the HTML (typically at the bottom of the page or outside the map container). Each modal gets a unique `id="questModal{{ quest.id }}"`. The modal’s content will include:

* **Header:** Quest title (e.g. `<h5 class="modal-title">{{ quest.title }}</h5>`).

* **Body:** Quest description and any requirements. We will use the quest’s `description` field as the description of the quest, which the teacher inputs when creating the quest. This usually describes what the student needs to do (e.g. “Complete the math worksheet” or “Finish reading chapter 3”). If we had a structured requirements field, we would list those, but currently we rely on the description text. We can format it in a `<p>` tag or list if needed. Next, we show **Rewards**: display the gold and XP rewards for completing the quest. Since rewards are stored in the `Reward` model related to the quest, we’ll retrieve them. For example, we can calculate `gold_reward = quest.rewards.filter_by(type='gold').first()` and `xp_reward = quest.rewards.filter_by(type='experience').first()`. In Jinja, as seen on the teacher’s quest list page, they do a similar lookup to display rewards. We will output something like: *“Rewards:  **{{ gold\_amount }} Gold**, **{{ xp\_amount }} XP**”*. If a reward is 0 (e.g. no gold for that quest), we can omit it or show 0 for completeness. Finally, if quest type (daily/weekly) is relevant, we might note it in the modal (e.g. label it a “Daily Quest” or “Weekly Quest” for flavor), since the quest has a type attribute. This is optional visual info.

* **Footer/Actions:** This is where we include buttons for **Accepting/Starting** or **Completing** the quest. We must tailor these to the quest’s status for the student:

  * If the quest is not yet started by the student (no QuestLog exists): show a button **“Start Quest”** (or “Accept Quest”). This button will trigger the POST to our `/student/quests/start/<id>` route. We can implement it as a simple HTML form inside the modal. For example:

    ```html
    <form method="POST" action="{{ url_for('student.start_quest', quest_id=quest.id) }}">
      <button type="submit" class="btn btn-success">Start Quest</button>
    </form>
    ```

    This form posts to the route which creates the QuestLog and redirects back. We use a form + submit button (rather than a link) to ensure it’s a POST (like how the teacher delete uses a form). Only include this if not started.
  * If the quest is already in progress for the student (`qlog.status == in_progress`): show a **“Mark Complete”** button. This should post to the `/student/quests/complete/<id>` route. Similarly:

    ```html
    <form method="POST" action="{{ url_for('student.complete_quest', quest_id=quest.id) }}">
      <button type="submit" class="btn btn-primary">Complete Quest</button>
    </form>
    ```

    We use a primary button to indicate the completion action. When clicked, it will mark the quest completed and grant rewards. After redirect, that quest’s status will be completed.
  * If the quest is already completed (`qlog.status == completed`): we do not show any actionable button. Instead, we can show a non-clickable note like **"✅ Quest Completed"** or disable the button. The modal can still show the details (in case students want to review what they did), but clearly no action is available. Possibly use a muted text or just omit footer buttons entirely for completed quests.

  Ensure that students cannot see any edit fields here – all information is displayed in plain text or labels, satisfying the requirement that *“students should not be able to edit the quest.”* The modal content for description and rewards is read-only. There are no input elements except the hidden form submissions for actions we allow. This preserves quest integrity (only teachers have access to create/edit quests via their separate interface).

By using one modal per quest with a static ID, the `data-bs-target` on each quest link will automatically trigger the correct modal. Bootstrap’s JS (already included via `bootstrap.bundle.min.js` in base.html) will handle showing/hiding modals when links are clicked. We do not need custom JavaScript for basic functionality. However, if needed, we can add JS in the template’s extra script block (using the `{% block super_extra_js %}` in base.html) to perhaps enhance user experience (for example, to dynamically update the map markers without full page reload after an action, or to confirm before marking complete). Initially, a full page refresh on form submit is fine – the app will redirect back to `/student/quests`, and the updated quest status and student XP/Gold will be reflected (the student’s gold/XP changes will be visible on their dashboard or profile; we might also update the navbar or dashboard summary if present).

**5. Template Structure:**
The updated `student/quests.html` might be structured as follows:

* A heading, e.g. **“Your Quests”** as in the placeholder.

* The map container `<div>` with all quest markers (each containing the quest link as described).

* Possibly a legend or note explaining that clicking a location opens quest details.

* After the map section, we can optionally list quests by category:

  * **Active Quests:** list quest titles currently in progress (with perhaps a “Complete” button as alternative to clicking map again).
  * **Completed Quests:** list titles of finished quests (for record). This duplicates info that could be on the map, but improves clarity. For example, a simple `<ul>` of completed quest names can be shown below the map.
  * However, these textual lists are optional since the map + modal interface covers the functionality. If the map UI is clear enough, we may skip separate lists to avoid redundancy. The important part is that the student can see which quests are active or done (either via the map labels or by these lists). The placeholder text did mention showing available, active, and completed quests in one place, so implementing a sectioned list below the map for Active and Completed quests could be a good complement for usability. We can reuse the logic from the dashboard to list active quests with status. Completed quests can be listed similarly by filtering QuestLogs with status completed for that student.

* Include all the quest modals (hidden by default). Ensure each modal has the required structure: a `.modal-dialog` and `.modal-content` wrapper, with a close button in the header (`data-bs-dismiss="modal"` attribute) so students can exit the popup without taking action if they just wanted to read details.

Here’s a condensed example of one quest modal in Jinja2 (for illustration):

```html
<div class="modal fade" id="questModal{{ quest.id }}" tabindex="-1" aria-labelledby="questModalLabel{{ quest.id }}" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="questModalLabel{{ quest.id }}">{{ quest.title }}</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <p>{{ quest.description }}</p>
        <p><strong>Rewards:</strong> {{ quest.rewards.filter_by(type='gold').first().amount or 0 }} Gold, {{ quest.rewards.filter_by(type='experience').first().amount or 0 }} XP</p>
        {% if quest.id in quest_logs %}
          {% set qlog = quest_logs[quest.id] %}
          {% if qlog.status.value == 'completed' %}
            <p class="text-success"><em>This quest is completed.</em></p>
          {% elif qlog.status.value == 'in_progress' %}
            <p class="text-info"><em>This quest is in progress.</em></p>
          {% endif %}
        {% endif %}
      </div>
      <div class="modal-footer">
        {% if quest.id not in quest_logs %}
          <!-- Not started: show Start button -->
          <form method="post" action="{{ url_for('student.start_quest', quest_id=quest.id) }}">
            <button type="submit" class="btn btn-success">Start Quest</button>
          </form>
        {% elif quest_logs[quest.id].status.value == 'in_progress' %}
          <!-- In progress: show Complete button -->
          <form method="post" action="{{ url_for('student.complete_quest', quest_id=quest.id) }}">
            <button type="submit" class="btn btn-primary">Mark Complete</button>
          </form>
        {% else %}
          <!-- Completed: no action -->
          <button class="btn btn-secondary" disabled>Completed</button>
        {% endif %}
      </div>
    </div>
  </div>
</div>
```

*(The above is illustrative; actual code will be refined for brevity and to ensure the reward lookup doesn’t repeat queries excessively. We might compute reward amounts in Python and pass them in context to the template for efficiency.)*

This modal will be triggered by the quest’s link on the map thanks to the matching `data-bs-target`. The student can read what they need to do in the **description** and see what they’ll get upon completion (gold/XP). They can then click **Start** to accept the quest. Later, after doing the task in real life (e.g. completing homework), they can reopen this modal (the quest would now show as Active on the map) and click **Complete Quest** to finish it. The system will then reward them accordingly.

## Ensuring No Student Edits & Role Separation

We will verify that students cannot modify quest definitions:

* The student quests page will **not include any form inputs for quest title/description/type** – those are display-only. Students only interact through the controlled “Start” and “Complete” actions. The underlying routes will not allow changing quest content, only creating or updating QuestLog status. This maintains the rule that only teachers design quests.
* The existing teacher quest creation/edit UI remains untouched and only accessible to teacher accounts. We won’t expose those links to students. (For instance, on the student side, we will not include anything like an “Edit” or “Delete” button that the teacher sees in their quest table.)
* Even if a student manually tries to navigate to teacher URLs, the `@student_required` vs `@login_required` logic will prevent access (or the menu navigation doesn’t show those links at all for students). Thus, the integrity of quests is safe.

Additionally, when implementing the new student routes, ensure to **check permissions**: use the current user’s ID and character to fetch/modify QuestLogs, so one student cannot affect another’s quests (this is largely enforced by using `current_user` and their own character data).

## Desktop UI Considerations

Since we are targeting desktop use, we can assume a decent screen width for the map. We might set the map container to a fixed width (e.g. 800-1000px) or full width of a container. If the map image is large, we can scale it down via CSS as shown (background-size: cover or a max-width). We should test the interface on a typical desktop resolution (e.g. 1080p) to ensure quest labels are positioned correctly and are readable. If a quest title is long, we might truncate or wrap it on the map to avoid overlap. We should also test the modal behavior – Bootstrap modals center on the screen; multiple modals can be openable but we will likely only open one at a time via the map links.

No separate mobile design will be done now, but as a note, if needed later the map section could degrade to a simple list of quests on narrow screens (or a smaller scrollable map).

## Implementation Steps Summary

To implement this feature in the current codebase, the steps are:

1. **Back-end Preparation:** Modify the `/student/quests` view function in `app/routes/student.py` to query quests and the student’s quest logs, then pass them to the template. Also add two new route handlers in this file for starting and completing quests (POST requests), using QuestLog methods to update status and reward the student. Use `login_required` and `student_required` on these routes for security.

2. **Database Model Usage:** Utilize the existing Quest and QuestLog models. No schema changes are required – quests and quest logs are already defined. The logic will create QuestLog entries when starting quests and update them when completing. The reward distribution is handled by calling the model methods (which ensures gold/XP are added to the character).

3. **Template Update:** Overhaul `app/templates/student/quests.html`. Introduce the map section with a background image (ensure to add the image file to `static/images`). Loop over `quests` and output each as a positioned name on the map. Add conditional styling or labels for quest status (available/active/completed). Below or within the map container, include the Bootstrap modals for each quest’s details. Populate each modal with the quest’s title, description, and reward info, and the appropriate action buttons (Start/Complete) or completed notice. The template should extend `base.html` so it inherits the nav and includes Bootstrap’s CSS/JS for modal support.

4. **Static Assets and Styling:** Add the quest map image to the static files. Update `static/css/style.css` if needed to style `.quest-marker` (e.g. making quest names more visible over the map) and any status indicators (like `.active-quest` or `.completed-quest` classes). Ensure the CSS works in both light and dark modes (the app supports a dark mode toggle, meaning our text colors should consider background – using Bootstrap’s text-warning or text-success classes, which the dark mode CSS will adjust accordingly, is helpful). If necessary, include a small custom script in `main.js` or via the template to handle any dynamic behavior (for example, we could listen for the form submission responses to perhaps highlight the completed quest without full reload – not required, but an enhancement).




