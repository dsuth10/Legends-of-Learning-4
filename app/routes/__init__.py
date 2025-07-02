from .main import main_bp
from .teacher import teacher_bp
from .auth import auth_bp
from app.routes.student_main import student_bp
from .clan import clan_api
from .teacher.quests import teacher_quests_bp
from app.routes.student.abilities import bp as abilities_bp

def init_app(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(clan_api)
    app.register_blueprint(teacher_quests_bp)
    app.register_blueprint(abilities_bp)

