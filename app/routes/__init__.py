from .main import main_bp
from .teacher import teacher_bp
from .auth import auth_bp
from .student import student_bp
from .clan import clan_api

def init_app(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(clan_api)

