import os
import time
import random
from flask import Blueprint, request, jsonify, session, send_from_directory, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, Outfit, Product

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
             print(f"DEBUG: Password MATCH for {user.username}") 
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

    # Simulate crawling delay
    time.sleep(2) 
    
    # Mock Crawled Data
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
                shopee_link=shop_url, 
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
        
        return jsonify({
            'message': 'Crawling successful', 
            'count': len(new_db_items),
            'products': crawled_products
        }), 200

    except Exception as e:
        db.session.rollback()
        # Return error as JSON instead of crashing
        return jsonify({'message': f'Server Error: {str(e)}'}), 500

@main_bp.route('/api/tryon', methods=['GET'])
def tryon():
    return jsonify({'status': 'success'}), 200
