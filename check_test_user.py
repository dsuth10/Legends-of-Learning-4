"""Diagnostic script to check test user credentials."""
from app import create_app, db
from app.models.user import User, UserRole

app = create_app()
with app.app_context():
    print("=" * 60)
    print("Checking test user credentials...")
    print("=" * 60)
    
    # Check if testuser exists
    user = User.query.filter_by(username='testuser').first()
    
    if not user:
        print("\n[ERROR] User 'testuser' does NOT exist in the database!")
        print("\nTo create the test user, run:")
        print("  python create_test_user.py")
        print("\nOr create it manually with:")
        print("  from app import create_app, db")
        print("  from app.models.user import User, UserRole")
        print("  app = create_app()")
        print("  with app.app_context():")
        print("      user = User(username='testuser', email='test@example.com', role=UserRole.TEACHER, is_active=True)")
        print("      user.set_password('testpassword')")
        print("      db.session.add(user)")
        print("      db.session.commit()")
    else:
        print(f"\n[OK] User 'testuser' EXISTS")
        print(f"   - ID: {user.id}")
        print(f"   - Email: {user.email}")
        print(f"   - Role: {user.role.value}")
        print(f"   - Is Active: {user.is_active}")
        print(f"   - Password Hash: {user.password_hash[:20]}...")
        
        # Test password
        print("\n" + "-" * 60)
        print("Testing password 'testpassword':")
        if user.check_password('testpassword'):
            print("[OK] Password 'testpassword' is CORRECT")
        else:
            print("[ERROR] Password 'testpassword' is INCORRECT")
            print("\nThe password hash might have been set incorrectly.")
            print("You may need to reset the password:")
            print("  user.set_password('testpassword')")
            print("  db.session.commit()")
        
        # Test other common passwords
        test_passwords = ['password', '123', 'test', 'admin']
        print("\n" + "-" * 60)
        print("Testing other common passwords:")
        for pwd in test_passwords:
            if user.check_password(pwd):
                print(f"  [WARNING] Password '{pwd}' also works!")
    
    # List all users
    print("\n" + "=" * 60)
    print("All users in database:")
    print("=" * 60)
    all_users = User.query.all()
    if not all_users:
        print("  No users found in database.")
    else:
        for u in all_users:
            print(f"  - {u.username} ({u.email}) - Role: {u.role.value} - Active: {u.is_active}")
    
    print("\n" + "=" * 60)

