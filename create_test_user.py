from app import create_app, db
from app.models.user import User, UserRole

app = create_app()
with app.app_context():
    # Check if user already exists
    if User.query.filter_by(username='testuser').first():
        print('Test user already exists.')
    else:
        user = User(
            username='testuser',
            email='test@example.com',
            role=UserRole.TEACHER,
            is_active=True
        )
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        print('Test user created!') 