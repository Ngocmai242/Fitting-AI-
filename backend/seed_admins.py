from app import app, db, User
from werkzeug.security import generate_password_hash

def seed_admins():
    with app.app_context():
        # Admin 1
        if not User.query.filter_by(username='mai').first():
            admin1 = User(
                username='mai',
                email='mai@admin.aurafit',
                password=generate_password_hash('1234'),
                role='ADMIN'
            )
            db.session.add(admin1)
            print("Added admin: mai")

        # Admin 2
        if not User.query.filter_by(username='admin').first():
            admin2 = User(
                username='admin',
                email='admin@admin.aurafit',
                password=generate_password_hash('1234'),
                role='ADMIN'
            )
            db.session.add(admin2)
            print("Added admin: admin")
        
        try:
            db.session.commit()
            print("Admins seeded successfully!")
        except Exception as e:
            print(f"Error seeding admins: {e}")
            db.session.rollback()

if __name__ == '__main__':
    seed_admins()
