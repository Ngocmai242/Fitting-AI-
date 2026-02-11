from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.getcwd(), 'database', 'database_v2.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    password = db.Column(db.String(200))
    role = db.Column(db.String(10))
    status = db.Column(db.String(20))
    fullname = db.Column(db.String(120))

def update_mai_to_user():
    with app.app_context():
        if not os.path.exists(DB_PATH):
            print("CRITICAL: Database file does not exist!")
            return

        # Find user 'mai'
        user = User.query.filter_by(username='mai').first()
        if user:
            print(f"Found user 'mai' with current role: {user.role}")
            print("Updating role to 'USER'...")
            user.role = 'USER'
            db.session.commit()
            print("✓ Successfully updated user 'mai' role to 'USER'")
            
            # Verify
            user = User.query.filter_by(username='mai').first()
            print(f"Verified - New role: {user.role}")
        else:
            print("User 'mai' not found!")

if __name__ == '__main__':
    update_mai_to_user()
