import sys
import os
from werkzeug.security import generate_password_hash

# Add backend to path to import app
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    email = "ngongocmai242@gmail.com"
    username = "ngocmai"
    new_pass = "123456"
    
    print(f"Checking user: {email}...")
    
    user = User.query.filter_by(email=email).first()
    
    if user:
        print("User found! Resetting password...")
        user.password = generate_password_hash(new_pass)
        user.username = username # Ensure username is set
    else:
        print("User not found. Creating new user...")
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(new_pass),
            role='USER',
            fullname="Ngoc Mai",
            avatar=f"https://ui-avatars.com/api/?name={username}&background=FF9EB5&color=fff"
        )
        db.session.add(user)
        
    db.session.commit()
    print("===========================================")
    print(f"SUCCESS! Login details:")
    print(f"Email:    {email}")
    print(f"Password: {new_pass}")
    print("===========================================")
