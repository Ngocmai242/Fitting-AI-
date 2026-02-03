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
    address = db.Column(db.String(200)) # Missing fields in prev definition caused error? No, sqlite is loose. 
    # Actually need to match model exactly or SQLAlchemy might complain if inserting.
    # Let's trust the columns exist.
    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20))

def create_mai():
    with app.app_context():
        # Check if mai exists using filter_by
        existing = User.query.filter_by(username='mai').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        
        user_mai = User(
            username='mai',
            email='mai@example.com',
            password=generate_password_hash('admin'), # PASSWORD IS 'admin'
            role='ADMIN',
            fullname='Mai Admin',
            avatar='https://ui-avatars.com/api/?name=Mai&background=random'
        )
        db.session.add(user_mai)
        db.session.commit()
        print("SUCCESS: User 'mai' created with password 'admin'")

if __name__ == '__main__':
    create_mai()
