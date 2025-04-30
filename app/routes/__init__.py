from .main import main_bp
from .teacher import teacher_bp
from .auth import auth_bp

def init_app(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(auth_bp)

