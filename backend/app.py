import os
import random
import time
from datetime import datetime
from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

# Configure Flask to serve static files from ../frontend
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.secret_key = 'super_secret_key_for_session_management'
# CORS is now less critical but kept for safety
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- Serve Frontend Routes ---
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

# Database Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'database_v2.db') # Updated to v2 to force schema refresh
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default='USER')
    
    # Simple profile fields directly in User for demo simplicity
    fullname = db.Column(db.String(100))
    avatar = db.Column(db.String(500), default='https://ui-avatars.com/api/?name=User&background=FF9EB5&color=fff')
    address = db.Column(db.String(200))
    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(500))
    shopee_link = db.Column(db.String(2000))
    price = db.Column(db.Float)
    category = db.Column(db.String(50)) # top/bottom/dress/accessory
    sub_category = db.Column(db.String(50))
    style = db.Column(db.String(50))
    color = db.Column(db.String(50))
    shop_name = db.Column(db.String(100))
    crawl_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Outfit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500))
    body_type = db.Column(db.String(50))
    style = db.Column(db.String(50))
    shop_link = db.Column(db.String(500))

# Initialize DB
with app.app_context():
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    db.create_all()
    
    # Seed data if empty
    if not Outfit.query.first():
        seed_outfits = [
            Outfit(name='Summer Floral Dress', image_url='https://images.unsplash.com/photo-1572804013427-4d7ca7268217?w=500', style='Casual', shop_link='https://shopee.vn/dress1', body_type='Hourglass'),
            Outfit(name='Office Blazer Set', image_url='https://images.unsplash.com/photo-1487222477894-8943e31ef7b2?w=500', style='Office', shop_link='https://lazada.vn/suit1', body_type='Rectangle'),
        ]
        db.session.add_all(seed_outfits)
        db.session.commit()

    # Seed Admin User if not exists
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
        print(">>> Default Admin User Create: admin / admin")

# --- Routes ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter((User.username == data.get('username')) | (User.email == data.get('email'))).first():
        return jsonify({'message': 'User already exists'}), 400
    
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'],
        email=data['email'],
        phone=data.get('phone'),
        password=hashed_pw,
        role='USER',
        fullname=data.get('username'), # Default fullname to username
        avatar = f"https://ui-avatars.com/api/?name={data.get('username')}&background=FF9EB5&color=fff"
    )
    if data['username'].lower() == 'admin':
        new_user.role = 'ADMIN'
        
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_input = data.get('login_input')
    password = data.get('password')
    
    user = User.query.filter(
        (User.username == login_input) | 
        (User.email == login_input) |
        (User.phone == login_input)
    ).first()
    
    print(f"Login attempt for: {login_input}") # Debug
    if user:
        if check_password_hash(user.password, password):
             print("Password match!") 
             session['user_id'] = user.id
             return jsonify({
                'message': 'Login successful', 
                'role': user.role, 
                'username': user.username,
                'fullname': user.fullname,
                'user_id': user.id,
                'avatar': user.avatar,
                'email': user.email,
                'phone': user.phone,
                'address': user.address,
                'gender': user.gender,
                'dob': user.dob
            }), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/profile', methods=['GET', 'POST', 'PUT'])
def profile():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'message': 'Missing user_id'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        return jsonify({
            'success': True,
            'profile': {
                'id': user.id,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'fullname': user.fullname,
                'phone': user.phone,
                'address': user.address,
                'gender': user.gender,
                'dob': user.dob,
                'avatar': user.avatar,
                'role': user.role
            }
        }), 200

    # POST/PUT
    user_id = None
    data = {}
    
    if request.is_json:
        data = request.json
        user_id = data.get('user_id')
    else:
        user_id = request.form.get('user_id')
        data = request.form

    if not user_id:
        return jsonify({'message': 'Unauthorized'}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    if 'fullname' in data: user.fullname = data['fullname']
    if 'email' in data: user.email = data['email']
    if 'phone' in data: user.phone = data['phone']
    if 'address' in data: user.address = data['address']
    if 'gender' in data: user.gender = data['gender']
    if 'dob' in data: user.dob = data['dob']
    
    # Handle File Upload
    if 'avatar_file' in request.files:
        file = request.files['avatar_file']
        if file.filename != '':
            upload_folder = os.path.join(app.root_path, 'static', 'uploads') # This might need adjustment if served from frontend folder? No, app.root_path is backend.
            # But we serve static from ../frontend
            # Let's save to ../frontend/uploads for direct access
            upload_folder = os.path.join(app.root_path, '..', 'frontend', 'uploads')
            
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filename = f"avatar_{user_id}_{int(time.time())}.png"
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Since we serve root from frontend, URL is /uploads/filename
            user.avatar = f"/uploads/{filename}"

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Database commit failed'}), 500
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'profile': {
            'id': user.id,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'fullname': user.fullname,
            'phone': user.phone,
            'address': user.address,
            'gender': user.gender,
            'dob': user.dob,
            'avatar': user.avatar,
            'role': user.role
        }
    }), 200

@app.route('/api/outfits', methods=['GET', 'POST', 'DELETE'])
def outfits():
    if request.method == 'GET':
        outfits = Outfit.query.all()
        return jsonify([{
            'id': o.id, 'name': o.name, 'image': o.image_url, 
            'style': o.style, 'shop_link': o.shop_link, 'body_type': o.body_type
        } for o in outfits]), 200

    if request.method == 'POST':
        data = request.json
        new_outfit = Outfit(
            name=data['name'], image_url=data['image'],
            style=data['style'], shop_link=data.get('shop_link', ''),
            body_type=data.get('body_type', 'General')
        )
        db.session.add(new_outfit)
        db.session.commit()
        return jsonify({'message': 'Outfit added'}), 201

    if request.method == 'DELETE':
        oid = request.args.get('id')
        outfit = Outfit.query.get(oid)
        if outfit:
            db.session.delete(outfit)
            db.session.commit()
            return jsonify({'message': 'Deleted'}), 200
        return jsonify({'message': 'Not found'}), 404

@app.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json
    shop_url = data.get('url')
    
    if not shop_url:
        return jsonify({'message': 'Missing URL'}), 400

    # Simulate crawling delay
    time.sleep(2) 
    
    # Mock Crawled Data (In real world, this would use Selenium/BS4)
    crawled_products = [
        {
            'name': 'Áo thun cotton nữ form rộng',
            'image': 'https://down-vn.img.susercontent.com/file/vn-11134207-7r98o-lzsi76r3m825ff', 
            'price': 150000,
            'category': 'top',
            'sub_category': 't-shirt',
            'style': 'casual',
            'shop_name': 'CoolMate Official'
        },
        {
            'name': 'Quần Jean ống rộng lưng cao',
            'image': 'https://down-vn.img.susercontent.com/file/vn-11134207-7r98o-lzsi77c7x9j3ba',
            'price': 320000,
            'category': 'bottom',
            'sub_category': 'jeans',
            'style': 'streetwear',
            'shop_name': 'CoolMate Official'
        },
        {
            'name': 'Váy hoa nhí vintage hàn quốc',
            'image': 'https://down-vn.img.susercontent.com/file/cn-11134207-7r98o-lzsi78k9y1p4cd',
            'price': 250000,
            'category': 'dress',
            'sub_category': 'midi dress',
            'style': 'vintage',
            'shop_name': 'CoolMate Official'
        }
    ]
    
    new_db_items = []
    
    try:
        for item in crawled_products:
            new_prod = Product(
                name=item['name'],
                image_path=item['image'],
                shopee_link=shop_url, # Linking back to source
                price=item['price'],
                category=item['category'],
                sub_category=item['sub_category'],
                style=item['style'],
                shop_name=item['shop_name'],
                is_active=True
            )
            new_db_items.append(new_prod)
            
        db.session.add_all(new_db_items)
        db.session.commit()
        print(f"Successfully saved {len(new_db_items)} items for URL: {shop_url}")
        
        return jsonify({
            'message': 'Crawling successful', 
            'count': len(new_db_items),
            'products': crawled_products
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"CRAWL ERROR: {str(e)}")
        # Return error as JSON instead of crashing
        return jsonify({'message': f'Server Error: {str(e)}'}), 500

@app.route('/api/tryon', methods=['GET'])
def tryon():
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5050)
