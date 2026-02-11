import os
import time
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, session, send_from_directory, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, Outfit, Product

# Add project root to path to import data_engine
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from data_engine.crawler.shopee import crawl_shop_url
    CRAWLER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import crawler: {e}. Ensure 'playwright' is installed.")
    CRAWLER_AVAILABLE = False
    def crawl_shop_url(url, limit=50): return []


main_bp = Blueprint('main', __name__)

# --- Serve Frontend Routes ---
@main_bp.route('/')
def serve_index():
    return send_from_directory(current_app.static_folder, 'index.html')

@main_bp.route('/<path:path>')
def serve_static(path):
    return send_from_directory(current_app.static_folder, path)

# --- API Routes ---

@main_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    print(f"\n=== REGISTRATION ATTEMPT ===")
    print(f"Username: {data.get('username')}")
    print(f"Email: {data.get('email')}")
    print(f"Phone: {data.get('phone')}")
    
    # Clean input
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip() if data.get('phone') else ''
    password = data.get('password', '').strip()
    
    # Check if user already exists
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        print(f"ERROR: User already exists - {existing_user.username}")
        return jsonify({'message': 'User already exists'}), 400
    
    try:
        hashed_pw = generate_password_hash(password)
        print(f"Password hashed successfully")
        
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            password=hashed_pw,
            role=data.get('role', 'USER'),
            status=data.get('status', 'Active'),
            fullname=data.get('fullname', username).strip(), # Use provided fullname or fallback to username
            avatar = f"https://ui-avatars.com/api/?name={username}&background=FF9EB5&color=fff",
            created_at=datetime.utcnow()
        )
        
        # Don't auto-promote to admin based on username
        # Don't auto-promote to admin based on username
        if username.lower() == 'admin':
            new_user.role = 'ADMIN'
            print(f"Setting role to ADMIN for user: admin")
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"✅ USER CREATED SUCCESSFULLY:")
        print(f"   - ID: {new_user.id}")
        print(f"   - Username: {new_user.username}")
        print(f"   - Role: {new_user.role}")
        print(f"   - Status: {new_user.status}")
        print(f"=========================\n")
        
        return jsonify({'message': 'Registered successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ REGISTRATION ERROR: {str(e)}")
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500


@main_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_input = data.get('login_input', '').strip()
    password = data.get('password', '').strip()
    
    print(f"DEBUG LOGIN Attempt: Input='{login_input}', PwLen={len(password)}")
    
    user = User.query.filter(
        (User.username == login_input) | 
        (User.email == login_input) |
        (User.phone == login_input)
    ).first()
    
    if user:
        print(f"DEBUG: User found: {user.username}, ID: {user.id}")
        if check_password_hash(user.password, password):
             # Improved Status Check (Handle None/Null/Case)
             user_status = str(user.status).strip().lower() if user.status else 'active'
             if user_status != 'active':
                 return jsonify({'message': 'Your account has been blocked. Please contact admin.'}), 403

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
        else:
             return jsonify({'message': 'Invalid password. Please try again.'}), 401
    
    return jsonify({'message': 'The account does not exist. Please log in again.'}), 404

@main_bp.route('/api/profile', methods=['GET', 'POST', 'PUT'])
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
            # We serve static from frontend/
            upload_folder = os.path.join(current_app.static_folder, 'uploads')
            
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

@main_bp.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    user_list = []
    for u in users:
        # Check if status/created_at attributes exist (migration safety)
        status = getattr(u, 'status', 'Active')
        created = getattr(u, 'created_at', None)
        created_str = created.strftime('%Y-%m-%d') if created else '2025-01-01'

        user_list.append({
            'id': u.id,
            'username': u.username,
            'fullname': u.fullname,
            'email': u.email,
            'role': u.role,
            'status': status,
            'created_at': created_str, 
            'avatar': u.avatar
        })
    return jsonify(user_list), 200

@main_bp.route('/api/users/<int:id>', methods=['PATCH', 'DELETE'])
def manage_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if request.method == 'PATCH':
        data = request.json
        if 'role' in data: user.role = data['role']
        if 'status' in data and data['status']: 
            clean_status = str(data['status']).strip()
            if clean_status: # Only update if not empty
                user.status = clean_status
        if 'fullname' in data and data['fullname']: user.fullname = data['fullname'].strip()
        if 'email' in data and data['email']: user.email = data['email'].strip()
        
        # New: Username and Password support
        if 'username' in data and data['username']: 
            clean_username = data['username'].strip()
            existing = User.query.filter(User.username == clean_username, User.id != user.id).first()
            if existing:
                return jsonify({'message': 'Username already taken'}), 400
            user.username = clean_username

        if 'password' in data and data['password']:
            clean_pw = data['password'].strip()
            if len(clean_pw) > 0:
                user.password = generate_password_hash(clean_pw)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Account updated successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Database error: {str(e)}'}), 500

    if request.method == 'DELETE':
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'message': 'User deleted'}), 200
        except:
            db.session.rollback()
            return jsonify({'message': 'Error deleting user'}), 500

@main_bp.route('/api/outfits', methods=['GET', 'POST', 'DELETE'])
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

@main_bp.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json
    shop_url = data.get('url')
    
    if not shop_url:
        return jsonify({'message': 'Missing URL'}), 400

    if not CRAWLER_AVAILABLE:
        return jsonify({
            'message': 'Crawler dependencies missing. Server cannot crawl. Please run: pip install playwright && playwright install'
        }), 500

    try:
        # Perform Crawling (Synchronous for simplicity)
        print(f"Starting crawl for: {shop_url}")
        crawled_products = crawl_shop_url(shop_url, limit=50) # Limit to 50 as requested
        
        if not crawled_products:
             return jsonify({'message': 'Crawling completed but no products found. Check URL or try again.'}), 404

        # Return crawled data for review instead of saving immediately
        return jsonify({
            'message': 'Crawling successful', 
            'count': len(crawled_products),
            'products': crawled_products
        }), 200

    except Exception as e:
        print(f"Crawl Error: {e}")
        return jsonify({'message': f'Server Error during crawl: {str(e)}'}), 500

@main_bp.route('/api/crawl/save', methods=['POST'])
def save_crawled_products():
    data = request.json
    products_to_save = data.get('products', [])
    
    if not products_to_save:
        return jsonify({'message': 'No products to save'}), 400

    new_db_items = []
    saved_count = 0
    
    try:
        for item in products_to_save:
            # Check if product already exists (by link)
            existing = Product.query.filter_by(shopee_link=item['shopee_link']).first()
            if not existing:
                new_prod = Product(
                    name=item['name'],
                    image_path=item['image'],
                    shopee_link=item['shopee_link'], 
                    price=item['price'],
                    category=item.get('category', 'Uncategorized'),
                    sub_category=item.get('sub_category', 'General'),
                    gender=item.get('gender', 'Unisex'),
                    material=item.get('material', 'Chưa xác định'),
                    style=item.get('style', 'Casual'),
                    details=item.get('details', ''),
                    shop_name=item.get('shop_name', 'Shopee Store'),
                    is_active=True
                )
                new_db_items.append(new_prod)
                saved_count += 1
        
        if new_db_items:
            db.session.add_all(new_db_items)
            db.session.commit()
            
        return jsonify({'message': f'Successfully saved {saved_count} new products.', 'saved_count': saved_count}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Save Crawl Error: {e}")
        return jsonify({'message': f'Database error: {str(e)}'}), 500

@main_bp.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'GET':
        products = Product.query.limit(100).all()
        return jsonify([{
            'id': p.id,
            'name': p.name, 
            'image': p.image_path,
            'price': p.price,
            'category': p.category,
            'shopee_link': p.shopee_link
        } for p in products]), 200

    if request.method == 'POST':
        data = request.json
        new_prod = Product(
            name=data.get('name'),
            image_path=data.get('image'),
            shopee_link=data.get('shopee_link'),
            price=data.get('price', 0),
            category=data.get('category', 'Uncategorized'),
            style=data.get('style', 'Casual'),
            shop_name=data.get('shop_name', 'Manual Entry')
        )
        db.session.add(new_prod)
        db.session.commit()
        return jsonify({'message': 'Product added manually'}), 201

@main_bp.route('/api/products/<int:id>', methods=['GET', 'DELETE', 'PUT'])
def product_detail(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'message': 'Product not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': product.id,
            'name': product.name,
            'image': product.image_path,
            'price': product.price,
            'category': product.category,
            'sub_category': product.sub_category,
            'style': product.style,
            'shop_name': product.shop_name,
            'shopee_link': product.shopee_link
        }), 200

    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200

    if request.method == 'PUT':
        data = request.json
        if 'name' in data: product.name = data['name']
        if 'price' in data: product.price = data['price']
        if 'image' in data: product.image_path = data['image']
        if 'shopee_link' in data: product.shopee_link = data['shopee_link']
        if 'category' in data: product.category = data['category']
        if 'sub_category' in data: product.sub_category = data['sub_category']
        if 'style' in data: product.style = data['style']
        if 'shop_name' in data: product.shop_name = data['shop_name']
        
        db.session.commit()
        return jsonify({'message': 'Product updated successfully'}), 200


@main_bp.route('/api/tryon', methods=['GET'])
def tryon():
    return jsonify({'status': 'success'}), 200
