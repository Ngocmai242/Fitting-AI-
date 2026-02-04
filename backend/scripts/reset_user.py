import sys
import os

# Add parent dir to path so we can import 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # backend
sys.path.append(parent_dir)

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Target User
    email = "ngongocmai242@gmail.com"
    username = "Mai" # fallback
    password = "123456"
    
    # Check if exists
    user = User.query.filter_by(email=email).first()
    
    if user:
        print(f"User {email} found. Resetting password...")
        user.password = generate_password_hash(password)
        db.session.commit()
        print("Password reset successfully to: 123456")
    else:
        print(f"User {email} not found. Creating new user...")
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role="USER",
            fullname="Ngo Ngoc Mai"
        )
        db.session.add(new_user)
        db.session.commit()
        print("User created successfully with password: 123456")
