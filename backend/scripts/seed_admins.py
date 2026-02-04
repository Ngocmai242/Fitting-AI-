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

def create_or_update_admin(username, password, fullname, email):
    user = User.query.filter_by(username=username).first()
    if user:
        print(f"User '{username}' found. Updating password...")
        user.password = generate_password_hash(password)
        # Ensure role is ADMIN
        if user.role != 'ADMIN':
             user.role = 'ADMIN'
    else:
        print(f"Creating new admin '{username}'...")
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role="ADMIN",
            fullname=fullname,
            avatar=f"https://ui-avatars.com/api/?name={username}&background=0D8ABC&color=fff"
        )
        db.session.add(user)
    
    db.session.commit()
    print(f"Admin '{username}' set with password '{password}'")

with app.app_context():
    create_or_update_admin("admin", "1234", "System Administrator", "admin@aurafit.local")
    create_or_update_admin("mai", "1234", "Mai Admin", "mai@aurafit.local")
    print("--- Admin Seeding Complete ---")
