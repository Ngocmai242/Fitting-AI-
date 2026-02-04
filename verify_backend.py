import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app import create_app, db
    print("Import successful")
    
    app = create_app()
    print("App created successfully")
    
    with app.app_context():
        # Try to query logic
        from app.models import User
        user_count = User.query.count()
        print(f"Database connection successful. User count: {user_count}")
        
    print("VERIFICATION SUCCESS")
except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    sys.exit(1)
