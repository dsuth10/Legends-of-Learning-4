import os

base_dir = "app/routes/teacher"
files = [
    "students_list.py",
    "students_crud.py",
    "students_import.py",
    "students_unassigned.py",
    "students_characters.py",
    "students_api.py",
]

template = '''"""
{desc}
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
'''

descriptions = {
    "students_list.py": "Handles listing, searching, and filtering students for teachers.",
    "students_crud.py": "Handles editing, removing, and toggling status of individual students.",
    "students_import.py": "Handles importing and exporting students (CSV upload, preview, confirm).",
    "students_unassigned.py": "Handles unassigned students: list, reassign, delete.",
    "students_characters.py": "Handles character management for students (view, batch actions, inventory, equipment, stats).",
    "students_api.py": "API endpoints for batch actions, stats, inventory, equipment, etc.",
}

os.makedirs(base_dir, exist_ok=True)

for fname in files:
    path = os.path.join(base_dir, fname)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(template.format(desc=descriptions[fname]))
        print(f"Created {path}")
    else:
        print(f"{path} already exists") 