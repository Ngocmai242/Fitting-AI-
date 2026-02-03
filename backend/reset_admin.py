from app import app, db, User
from werkzeug.security import generate_password_hash

def reset_admin_password():
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            print("Admin user found. Resetting password...")
            admin.password = generate_password_hash('admin')
            admin.role = 'ADMIN' # Ensure role is correct
            db.session.commit()
            print("SUCCESS: Admin password reset to 'admin'.")
        else:
            print("Admin user not found. Creating new admin...")
            new_admin = User(
                username='admin',
                email='admin@aurafit.com',
                password=generate_password_hash('admin'),
                role='ADMIN'
            )
            db.session.add(new_admin)
            db.session.commit()
            print("SUCCESS: New admin user created with password 'admin'.")

if __name__ == "__main__":
    reset_admin_password()
