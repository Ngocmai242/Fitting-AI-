from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.getcwd(), 'database', 'database_v2.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default='USER')
    fullname = db.Column(db.String(100))
    avatar = db.Column(db.String(500))
    address = db.Column(db.String(200))
    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime)

def check_all_users():
    with app.app_context():
        output = []
        output.append("=== ALL USERS IN DATABASE ===\n")
        
        users = User.query.all()
        for u in users:
            output.append(f"\n--- User ID: {u.id} ---")
            output.append(f"Username: {u.username}")
            output.append(f"Email: {u.email}")
            output.append(f"Phone: {u.phone}")
            output.append(f"Role: {u.role}")
            output.append(f"Status: {u.status}")
            output.append(f"Fullname: {u.fullname}")
            output.append(f"Created: {u.created_at}")
            output.append(f"Password Hash starts with: {u.password[:20]}...")
            output.append(f"Password Hash length: {len(u.password)}")
            
            # Test password verification with common passwords
            test_passwords = ['password', 'password123', 'admin', '12345678']
            for test_pw in test_passwords:
                if check_password_hash(u.password, test_pw):
                    output.append(f"⚠️ WARNING: Password is '{test_pw}'")
                    break
        
        # Write to file
        with open('all_users_debug.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        
        print(f"✅ Found {len(users)} users. Details saved to all_users_debug.txt")

if __name__ == '__main__':
    check_all_users()
