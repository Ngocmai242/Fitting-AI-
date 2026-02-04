import sys
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    print(">>> DEBUGGING LOGIN <<<")
    
    # 1. Define Test Credentials
    email = "ngongocmai242@gmail.com"
    raw_pass = "123456"
    
    # 2. Get User from DB
    user = User.query.filter_by(email=email).first()
    
    if not user:
        print(f"ERROR: User {email} NOT FOUND in DB!")
        print(f"DB Path: {app.config['SQLALCHEMY_DATABASE_URI']}")
    else:
        print(f"User found: {user.username} (ID: {user.id})")
        print(f"Stored Hash: {user.password}")
        
        # 3. Check Hash Locally
        is_match = check_password_hash(user.password, raw_pass)
        print(f"Local Hash Check (pass='{raw_pass}'): {'MATCH' if is_match else 'FAIL'}")
        
        # 4. Force Reset if Fail
        if not is_match:
            print("Hash mismatch! Resetting password now...")
            user.password = generate_password_hash(raw_pass)
            db.session.commit()
            print("Password reset committed.")
            
            # Re-check
            is_match_2 = check_password_hash(user.password, raw_pass)
            print(f"Re-check after reset: {'MATCH' if is_match_2 else 'FAIL'}")

    # 5. Test API Endpoint using Flask Test Client
    print("\n>>> TESTING API ENDPOINT <<<")
    client = app.test_client()
    response = client.post('/api/login', json={
        'login_input': email,
        'password': raw_pass
    })
    
    print(f"API Response Code: {response.status_code}")
    print(f"API Response Body: {response.get_json()}")
    
    if response.status_code == 200:
        print("LOGIN SUCCESS via API Simulation")
    else:
        print("LOGIN FAILED via API Simulation")
