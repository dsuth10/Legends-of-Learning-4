from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    print("WARNING: This will drop and recreate all tables. All data will be lost!")
    db.drop_all()
    db.create_all()
    print("Database tables dropped and recreated.") 