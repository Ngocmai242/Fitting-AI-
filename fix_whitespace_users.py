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

def fix_usernames_with_whitespace():
    with app.app_context():
        output = []
        output.append("=== Fixing Usernames with Whitespace ===\n")
        
        users = User.query.all()
        fixed_count = 0
        
        for user in users:
            original_username = user.username
            original_fullname = user.fullname
            original_email = user.email
            trimmed_username = original_username.strip() if original_username else None
            trimmed_fullname = original_fullname.strip() if original_fullname else None
            trimmed_email = original_email.strip() if original_email else None
            
            needs_fix = False
            
            if original_username != trimmed_username:
                output.append(f"User ID {user.id}: Username has whitespace")
                output.append(f"  Original: '{original_username}'")
                output.append(f"  Trimmed: '{trimmed_username}'")
                user.username = trimmed_username
                needs_fix = True
            
            if original_fullname != trimmed_fullname:
                output.append(f"User ID {user.id}: Fullname has whitespace")
                output.append(f"  Original: '{original_fullname}'")
                output.append(f"  Trimmed: '{trimmed_fullname}'")
                user.fullname = trimmed_fullname
                needs_fix = True
            
            if original_email != trimmed_email:
                output.append(f"User ID {user.id}: Email has whitespace")
                output.append(f"  Original: '{original_email}'")
                output.append(f"  Trimmed: '{trimmed_email}'")
                user.email = trimmed_email
                needs_fix = True
            
            if needs_fix:
                fixed_count += 1
        
        if fixed_count > 0:
            try:
                db.session.commit()
                output.append(f"\n✅ Fixed {fixed_count} users")
            except Exception as e:
                db.session.rollback()
                output.append(f"\n❌ Error: {str(e)}")
        else:
            output.append("\n✅ No users need fixing")
        
        # Show final state
        output.append("\n=== Current Users ===")
        users = User.query.all()
        for u in users:
            output.append(f"ID {u.id}: '{u.username}' | '{u.email}' | Role: {u.role}")
        
        # Write to file
        with open('fix_whitespace_output.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        
        print(f"✅ Processed {len(users)} users. Details saved to fix_whitespace_output.txt")

if __name__ == '__main__':
    fix_usernames_with_whitespace()
