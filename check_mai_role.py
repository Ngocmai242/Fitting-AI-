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

def check_specific_user():
    with app.app_context():
        if not os.path.exists(DB_PATH):
            with open('user_check_output.txt', 'w') as f:
                f.write("CRITICAL: Database file does not exist!")
            return

        output_lines = []
        
        # Check for user 'mai'
        user = User.query.filter_by(username='mai').first()
        if user:
            output_lines.append("User 'mai' found:")
            output_lines.append(f" - ID: {user.id}")
            output_lines.append(f" - Username: {user.username}")
            output_lines.append(f" - Email: {user.email}")
            output_lines.append(f" - Role: {user.role}")
            output_lines.append(f" - Status: {user.status}")
            output_lines.append(f" - Fullname: {user.fullname}")
        else:
            output_lines.append("User 'mai' not found!")
            
        # Show all users
        output_lines.append("\nAll users:")
        users = User.query.all()
        for u in users:
            output_lines.append(f" - {u.username} | Role: {u.role} | Status: {u.status}")
        
        # Write to file
        with open('user_check_output.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        print("Output written to user_check_output.txt")

if __name__ == '__main__':
    check_specific_user()
