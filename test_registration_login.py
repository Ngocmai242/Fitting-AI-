from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
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
    avatar = db.Column(db.String(500), default='https://ui-avatars.com/api/?name=User&background=FF9EB5&color=fff')
    address = db.Column(db.String(200))
    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def test_create_and_login():
    with app.app_context():
        output = []
        
        # Test data
        test_username = "testuser123"
        test_email = "testuser123@example.com"
        test_password = "password123"
        
        output.append("=== Testing User Registration and Login ===\n")
        
        # 1. Delete test user if exists
        existing = User.query.filter_by(username=test_username).first()
        if existing:
            output.append(f"♻️ Deleting existing test user...")
            db.session.delete(existing)
            db.session.commit()
        
        # 2. Create new user (simulating registration)
        output.append(f"📝 Creating new user: {test_username}")
        hashed_pw = generate_password_hash(test_password)
        
        new_user = User(
            username=test_username,
            email=test_email,
            phone="0123456789",
            password=hashed_pw,
            role='USER',
            status='Active',
            fullname=test_username,
            avatar=f"https://ui-avatars.com/api/?name={test_username}&background=FF9EB5&color=fff",
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            output.append(f"✅ User created successfully! ID: {new_user.id}")
        except Exception as e:
            output.append(f"❌ Error creating user: {e}")
            db.session.rollback()
            with open('test_output.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(output))
            return
        
        # 3. Test login (simulating login attempt)
        output.append(f"\n🔐 Testing login with username: {test_username}")
        user = User.query.filter(
            (User.username == test_username) | 
            (User.email == test_username) |
            (User.phone == test_username)
        ).first()
        
        if user:
            output.append(f"✅ User found in database")
            output.append(f"   - ID: {user.id}")
            output.append(f"   - Username: {user.username}")
            output.append(f"   - Email: {user.email}")
            output.append(f"   - Role: {user.role}")
            output.append(f"   - Status: {user.status}")
            output.append(f"   - Created: {user.created_at}")
            
            if check_password_hash(user.password, test_password):
                output.append(f"✅ Password verification successful!")
                
                # Check status
                user_status = str(user.status).strip().lower() if user.status else 'active'
                if user_status != 'active':
                    output.append(f"❌ Account is blocked (Status: {user.status})")
                else:
                    output.append(f"✅ Account is active - Login would succeed!")
            else:
                output.append(f"❌ Password verification failed!")
        else:
            output.append(f"❌ User not found in database!")
        
        # 4. Show all users
        output.append(f"\n📋 All users in database:")
        all_users = User.query.all()
        for u in all_users:
            output.append(f"   - {u.username} | {u.email} | Role: {u.role} | Status: {u.status}")
        
        # Write to file
        with open('test_output.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        
        print("✅ Test completed. Results saved to test_output.txt")

if __name__ == '__main__':
    test_create_and_login()
