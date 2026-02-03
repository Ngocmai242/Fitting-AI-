from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
# MATCHING APP.PY PATH EXACTLY
BASE_DIR = os.path.abspath(os.path.join(os.getcwd(), 'backend')) # Assuming running from root g:\1
DB_PATH = os.path.join(os.getcwd(), 'database', 'database_v2.db')

print(f"Checking DB at: {DB_PATH}")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    password = db.Column(db.String(200)) # Hashed
    role = db.Column(db.String(10))

def check_users():
    with app.app_context():
        if not os.path.exists(DB_PATH):
            print("CRITICAL: Database file does not exist!")
            return

        users = User.query.all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f" - ID: {u.id} | User: {u.username} | Email: {u.email} | Role: {u.role}")

if __name__ == '__main__':
    check_users()
