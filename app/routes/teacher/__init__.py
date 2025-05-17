from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from app.models import db
from app.models.classroom import Classroom
from app.models.character import Character
from app.models.clan import Clan
from app.models.quest import Quest
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from werkzeug.security import generate_password_hash
import csv
from io import TextIOWrapper
from werkzeug.utils import secure_filename
from app.models.classroom import class_students
import random, string
from app.models.student import Student
import io
import json
import logging
from app.models.equipment import Equipment, Inventory, EquipmentType, EquipmentSlot
from app.models.audit import EventType
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import os
from flask_jwt_extended import jwt_required
from app.models.clan_progress import ClanProgressHistory
from app.services.clan_metrics import calculate_clan_metrics
from .blueprint import teacher_bp, teacher_required, student_required

__all__ = [
    'teacher_bp',
    'teacher_required',
    'student_required',
]

from . import classes  # noqa: F401
from . import students  # noqa: F401
from . import profile  # noqa: F401
from . import clan  # noqa: F401
from . import misc  # noqa: F401
from . import students_list  # noqa: F401
from . import students_crud  # noqa: F401
from . import students_import  # noqa: F401
from . import students_unassigned  # noqa: F401
from . import students_characters  # noqa: F401
from . import students_api  # noqa: F401

# All duplicated route blocks have been removed from this file.
# All teacher routes are now handled in their respective submodules.