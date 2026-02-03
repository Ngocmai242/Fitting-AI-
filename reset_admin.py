from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os

# Setup minimal Flask app to access DB
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'database_v2.db')
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

def reset_admin():
    with app.app_context():
        # Find existing admin
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            db.session.delete(admin)
            db.session.commit()
            print("Deleted old admin user.")
        
        # Create new admin
        new_admin = User(
            username='admin',
            email='admin@aurafit.com',
            password=generate_password_hash('admin'), # Password is 'admin'
            role='ADMIN',
            fullname='System Administrator'
        )
        db.session.add(new_admin)
        db.session.commit()
        print("SUCCESS: Admin user reset.")
        print("Username: admin")
        print("Password: admin")

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
    else:
        reset_admin()
