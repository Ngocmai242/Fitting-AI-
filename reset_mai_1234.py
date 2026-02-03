from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os

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

def reset_mai_1234():
    with app.app_context():
        # Clean up old mai
        existing = User.query.filter_by(username='mai').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            print("Deleted old mai user.")
        
        # Create new mai with password '1234'
        user_mai = User(
            username='mai',
            email='mai@example.com',
            password=generate_password_hash('1234'), # 4 characters!
            role='ADMIN',
            fullname='Mai Admin',
            avatar='https://ui-avatars.com/api/?name=Mai&background=ff00cc&color=fff'
        )
        db.session.add(user_mai)
        db.session.commit()
        print("SUCCESS: User 'mai' created with password '1234'")

if __name__ == '__main__':
    reset_mai_1234()
