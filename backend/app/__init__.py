import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app():
    # Use absolute path for robustness
    # We want to serve static files from ../frontend relative to this file
    # backend/app/__init__.py -> .../frontend
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, '..', '..', 'frontend')
    frontend_dir = os.path.abspath(frontend_dir)

    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    app.secret_key = 'super_secret_key_for_session_management'
    
    # Allow CORS with credentials for local development
    # Wildcard '*' with supports_credentials=True is invalid in modern browsers
    CORS(app, resources={r"/*": {"origins": [
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5500", 
        "http://127.0.0.1:5500",
        "http://localhost:5050",
        "http://127.0.0.1:5050"
    ]}}, supports_credentials=True)

    # Database Config
    # backend/app/../../database/database_v2.db
    db_path = os.path.join(base_dir, '..', '..', 'database', 'database_v2.db')
    db_path = os.path.abspath(db_path)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        # Imports to register models and routes
        from . import models, routes
        
        # Ensure DB dir exists
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path))
            
        db.create_all()
        
        # Seed Data (Optional, kept from original)
        seed_data()

    # Register Blueprint or import routes directly
    # Since we are using a simple app structure with global app instance in routes (usually),
    # but here we are using factory pattern.
    # To keep it simple and compatible with the original monolithic style refactor:
    # We will import routes which will register themselves to 'current_app' or use 'app' from a blueprint.
    # Let's use Blueprint for routes to be clean.
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

def seed_data():
    from .models import Outfit, User, Product
    from werkzeug.security import generate_password_hash
    
    # Seed Outfits
    if not Outfit.query.first():
        seed_outfits = [
            Outfit(name='Summer Floral Dress', image_url='https://images.unsplash.com/photo-1572804013427-4d7ca7268217?w=500', style='Casual', shop_link='https://shopee.vn/dress1', body_type='Hourglass'),
            Outfit(name='Office Blazer Set', image_url='https://images.unsplash.com/photo-1487222477894-8943e31ef7b2?w=500', style='Office', shop_link='https://lazada.vn/suit1', body_type='Rectangle'),
        ]
        db.session.add_all(seed_outfits)
        db.session.commit()

    # Seed Admin
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@aurafit.com',
            password=generate_password_hash('admin'),
            role='ADMIN',
            fullname='System Administrator',
            avatar='https://ui-avatars.com/api/?name=Admin&background=0D8ABC&color=fff'
        )
        db.session.add(admin_user)
        db.session.commit()
