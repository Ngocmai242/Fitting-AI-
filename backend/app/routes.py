import csv
import io
import os
import time
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    send_from_directory,
    session,
)
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import (
    Category,
    Color,
    ItemType,
    Occasion,
    Outfit,
    Product,
    Season,
    Style,
    User,
)

# Add project root to path to import data_engine
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import crawlers independently
try:
    from data_engine.crawler.shopee import crawl_shop_url as crawl_shopee
except ImportError as e:
    print(f"Could not import shopee crawler: {e}")
    def crawl_shopee(url, limit=50): return []

try:
    from data_engine.crawler.lazada import crawl_lazada_shop_url as crawl_lazada
except ImportError as e:
    # Lazada is optional
    def crawl_lazada(url, limit=50): return []

CRAWLER_AVAILABLE = True # Always True now since we use requests


main_bp = Blueprint('main', __name__)

# ──────────────────────────────────────────────────────────────────────────────
# Canonical clothing taxonomy (for AI training)
# ──────────────────────────────────────────────────────────────────────────────

# Map từ ai_category (FeatureExtractor) → (main_group, sub_category) theo schema bạn đưa
CANONICAL_CLOTHING_MAP = {
    # Tops
    "Top_Tshirt": ("tops", "t_shirt"),
    "Top_Shirt": ("tops", "shirt"),
    "Top_Tanktop": ("tops", "tank_top"),
    "Top_Croptop": ("tops", "crop_top"),
    "Top_Polo": ("tops", "shirt"),
    "Top_Sweater": ("tops", "sweater"),      # gồm cả hoodie/cardigan trong rules hiện tại
    # Outerwear (xem như tops trong schema đơn giản)
    "Outer_Blazer": ("tops", "blazer"),
    "Outer_Jacket": ("tops", "jacket"),
    "Outer_Coat": ("tops", "jacket"),
    # Bottoms
    "Bottom_Jeans": ("bottoms", "jeans"),
    "Bottom_Formal_Trousers": ("bottoms", "trousers"),
    "Bottom_Shorts": ("bottoms", "shorts"),
    "Bottom_Jogger": ("bottoms", "trousers"),
    "Bottom_Skirt": ("dresses_skirts", "skirt"),
    "Bottom_LongSkirt": ("dresses_skirts", "skirt"),
    # Dresses & one-piece
    "Dress": ("dresses_skirts", "dress"),
    "Jumpsuit": ("dresses_skirts", "dress"),
    # Sets & sleepwear
    "Set_Sleepwear": ("sleepwear_homewear", "pajama_set"),
    "Matching_set": ("clothing_sets", "top_bottom_set"),
}


def map_to_canonical_clothing(ai_category: str, item_type_raw: str, shopee_cat: str | None = None):
    """
    Map từ taxonomy AI hiện tại (ai_category, item_type) sang schema CLOTHING-ONLY bạn mô tả.
    Trả về (item_type_name, category_name) hoặc (None, None) nếu không map được.
    """
    key = (ai_category or "").strip()
    if key in CANONICAL_CLOTHING_MAP:
        return CANONICAL_CLOTHING_MAP[key]

    # Fallback nhẹ theo item_type nếu cần mở rộng sau này
    it = (item_type_raw or "").strip().lower()
    if not it:
        return None, None

    if it == "top":
        return "tops", "t_shirt"
    if it == "bottom":
        return "bottoms", "trousers"
    if it == "dress":
        return "dresses_skirts", "dress"
    if it == "set":
        return "clothing_sets", "top_bottom_set"

    return None, None

def get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance

# --- Serve Frontend Routes ---
@main_bp.route('/')
def serve_index():
    return send_from_directory(current_app.static_folder, 'index.html')

@main_bp.route('/<path:path>')
def serve_static(path):
    return send_from_directory(current_app.static_folder, path)

# --- API Routes ---

@main_bp.route('/api/classify', methods=['POST'])
def classify_by_name():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'message': 'name required'}), 400
    try:
        from data_engine.feature_engine import FeatureExtractor
        feats = FeatureExtractor.extract(name, '')
        ai_category = feats.get('category', 'Other')
        ai_item_type = feats.get('item_type', '')
        it_name, sub_cat = map_to_canonical_clothing(ai_category=ai_category, item_type_raw=ai_item_type)
        return jsonify({
            'ai_item_type': ai_item_type,
            'ai_category': ai_category,
            'item_type': it_name,
            'category': sub_cat
        }), 200
    except Exception as e:
        return jsonify({'message': f'classification error: {e}'}), 500

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
        desired_role = str(data.get('role', 'USER')).upper()
        # Only allow creating non-USER roles if current session user is ADMIN
        can_set_role = False
        sid = session.get('user_id')
        if sid:
            admin_user = User.query.get(sid)
            if admin_user and admin_user.role == 'ADMIN':
                can_set_role = True
        final_role = desired_role if (desired_role != 'USER' and can_set_role) else 'USER'

        new_user = User(
            username=username,
            email=email,
            phone=phone,
            password=hashed_pw,
            role=final_role,
            status='Active',
            fullname=data.get('fullname', username).strip(), # Use provided fullname or fallback to username
            avatar = f"https://ui-avatars.com/api/?name={username}&background=FF9EB5&color=fff",
            created_at=datetime.utcnow()
        )
                
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
        return jsonify({'message': 'Thiếu URL'}), 400

    # Component check (optional, since we use requests now)
    pass 

    try:
        # Gọi crawler tương ứng
        current_app.logger.info(f"[CRAWL] Bắt đầu crawl: {shop_url}")
        
        if 'lazada.vn' in shop_url:
            current_app.logger.info("Detect Lazada URL")
            crawled_products = crawl_lazada(shop_url, limit=50)
        else:
            current_app.logger.info("Detect Shopee URL (or default)")
            crawled_products = crawl_shopee(shop_url, limit=50)
        
        if not crawled_products:
            return jsonify({
                'message': 'Crawl thành công nhưng không tìm thấy sản phẩm. Kiểm tra lại URL hoặc thử lại sau.',
                'products': [],
                'count': 0
            }), 200

        # Trả về dữ liệu cho frontend xem trước
        return jsonify({
            'message': 'Crawl thành công',
            'count': len(crawled_products),
            'products': crawled_products
        }), 200

    except Exception as e:
        # Ghi log lỗi chi tiết
        current_app.logger.error(f"[CRAWL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Trả về thông báo lỗi rõ ràng
        return jsonify({
            'message': f'Lỗi khi crawl: {str(e)}'
        }), 500

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
            item_id_value = item.get('itemid') or item.get('item_id') or item.get('itemId')
            # Ưu tiên product_url, sau đó shopee_link, cuối cùng là url (từ crawler Shopee)
            link_value = item.get('product_url') or item.get('shopee_link') or item.get('url')

            if not item_id_value and not link_value:
                continue

            item_id = str(item_id_value) if item_id_value else None

            product = None
            if item_id:
                product = Product.query.filter_by(item_id=item_id).first()
            if not product and link_value:
                product = Product.query.filter_by(product_url=link_value[:2000]).first()

            created = False
            if not product:
                if not item_id:
                    continue
                product = Product(item_id=item_id)
                db.session.add(product)
                created = True
            try:
                if item_id:
                    product.item_id = int(item_id)
            except:
                pass

            product.name = (item.get('name') or '')[:200]
            product.image_url = (item.get('image_url') or item.get('image') or '')[:500]
            product.product_url = (link_value or '')[:2000]

            try:
                product.price = int(float(item.get('price', 0)))
            except (TypeError, ValueError):
                product.price = 0

            product.gender = (item.get('gender') or 'Unisex')[:20]
            product.material = (item.get('material') or 'Other')[:100]
            product.fit_type = (item.get('fit_type') or 'Regular fit')[:50]
            product.color_tone = (item.get('color_tone') or 'Neutral')[:20]
            product.details = (item.get('details') or '')[:200]
            product.shop_name = (item.get('shop_name') or 'Shopee Store')[:150]
            product.crawl_date = datetime.utcnow()
            product.is_active = True

            # --- Category normalization for AI training ---
            # Ưu tiên map sang CLOTHING-ONLY schema (tops/bottoms/dress/sets/sleepwear)
            ai_category_val = (item.get('ai_category') or '').strip()
            item_type_raw = (item.get('item_type') or '').strip()
            sub_cat_raw = (item.get('sub_category') or '').strip()

            item_type_name, category_name = map_to_canonical_clothing(
                ai_category=ai_category_val,
                item_type_raw=item_type_raw,
                shopee_cat=item.get('category')
            )

            # Nếu không map được sang schema chuẩn → bỏ qua, tránh "phân loại khác"
            if not item_type_name or not category_name:
                continue

            # Nếu sau chuẩn hóa vẫn còn "Other" hoặc Shopee leaf là "Khác" → bỏ qua sản phẩm này
            vn_cat = str(category_name).strip().lower()
            if vn_cat in ('other', 'khac', 'khác', 'phan loai khac', 'phân loại khác'):
                continue

            color_name = (item.get('color') or 'Multicolor').strip() or 'Multicolor'
            color_tone = (item.get('color_tone') or 'Pattern').strip() or 'Pattern'
            style_name = (item.get('style') or 'Casual').strip() or 'Casual'

            season_raw = item.get('season')
            if isinstance(season_raw, list) and season_raw:
                season_name = str(season_raw[0])
            else:
                season_name = str(season_raw or 'All-season')

            occasion_raw = item.get('occasion')
            if isinstance(occasion_raw, list) and occasion_raw:
                occasion_name = str(occasion_raw[0])
            else:
                occasion_name = str(occasion_raw or 'Daily wear')

            product.category_label = item_type_name[:50]
            product.sub_category_label = category_name[:50]
            product.color_label = color_name[:50]
            product.style_label = style_name[:50]
            product.season_label = season_name[:50]
            product.occasion_label = occasion_name[:50]

            item_type = get_or_create(ItemType, name=item_type_name)
            category = get_or_create(Category, name=category_name, defaults={"item_type": item_type})
            color = get_or_create(Color, name=color_name, defaults={"tone": color_tone})
            if color.tone != color_tone and color_tone:
                color.tone = color_tone
            style = get_or_create(Style, name=style_name)
            season = get_or_create(Season, name=season_name)
            occasion = get_or_create(Occasion, name=occasion_name)

            product.item_type = item_type
            product.category = category
            product.color = color
            product.style_ref = style
            product.season_ref = season
            product.occasion_ref = occasion

            if created:
                saved_count += 1
            else:
                new_db_items.append(product)

        db.session.commit()

        return jsonify({
            'message': f'Catalog updated. Added {saved_count} new products and refreshed {len(new_db_items)} items.',
            'saved_count': saved_count,
            'updated_count': len(new_db_items)
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Save Crawl Error: {e}")
        return jsonify({'message': f'Database error: {str(e)}'}), 500

@main_bp.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'GET':
        products = Product.query.order_by(Product.id.desc()).limit(100).all()
        payload = []
        for p in products:
            payload.append({
                'id': p.id,
                'item_id': p.item_id,
                'name': p.name,
                'image': p.image_url,
                'price': p.price,
                'category': p.item_type.name if p.item_type else p.category_label,
                'sub_category': p.category.name if p.category else p.sub_category_label,
                'product_url': p.product_url,
                'color': p.color.name if p.color else p.color_label,
                'color_tone': p.color.tone if p.color else p.color_tone,
                'season': p.season_ref.name if p.season_ref else p.season_label,
                'occasion': p.occasion_ref.name if p.occasion_ref else p.occasion_label,
                'gender': p.gender,
                'material': p.material,
                'style': p.style_ref.name if p.style_ref else p.style_label,
                'fit_type': p.fit_type,
                'details': p.details,
                'shop_name': p.shop_name,
            })
        return jsonify(payload), 200

    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'message': 'Missing payload'}), 400

        item_id = data.get('item_id') or data.get('shopee_link')
        if not item_id:
            return jsonify({'message': 'item_id or shopee_link required'}), 400

        product = Product(item_id=str(item_id))
        product.name = (data.get('name') or '')[:200]
        product.image_url = (data.get('image') or '')[:500]
        product.product_url = (data.get('product_url') or data.get('shopee_link') or '')[:2000]
        product.price = int(data.get('price', 0) or 0)
        product.shop_name = (data.get('shop_name') or 'Manual Entry')[:150]
        product.gender = (data.get('gender') or 'Unisex')[:20]
        product.material = (data.get('material') or 'Other')[:100]
        product.fit_type = (data.get('fit_type') or 'Regular fit')[:50]
        product.color_tone = color_tone[:20]
        product.details = (data.get('details') or '')[:200]

        category_field = data.get('category') or 'Other'
        if isinstance(category_field, str) and '|' in category_field:
            item_type_name, sub_category_name = [part.strip() for part in category_field.split('|', 1)]
        else:
            item_type_name = str(category_field).strip() or 'Other'
            sub_category_name = (data.get('sub_category') or 'Other').strip() or 'Other'

        style_name = (data.get('style') or 'Casual').strip() or 'Casual'
        color_name = (data.get('color') or 'Multicolor').strip() or 'Multicolor'
        color_tone = (data.get('color_tone') or 'Pattern').strip() or 'Pattern'
        season_name = (data.get('season') or 'All-season').strip() or 'All-season'
        occasion_name = (data.get('occasion') or 'Daily wear').strip() or 'Daily wear'

        product.category_label = item_type_name[:50]
        product.sub_category_label = sub_category_name[:50]
        product.color_label = color_name[:50]
        product.style_label = style_name[:50]
        product.season_label = season_name[:50]
        product.occasion_label = occasion_name[:50]

        item_type = get_or_create(ItemType, name=item_type_name)
        category = get_or_create(Category, name=sub_category_name, defaults={'item_type': item_type})
        color = get_or_create(Color, name=color_name, defaults={'tone': color_tone})
        if color.tone != color_tone and color_tone:
            color.tone = color_tone
        style = get_or_create(Style, name=style_name)
        season = get_or_create(Season, name=season_name)
        occasion = get_or_create(Occasion, name=occasion_name)

        product.item_type = item_type
        product.category = category
        product.color = color
        product.style_ref = style
        product.season_ref = season
        product.occasion_ref = occasion

        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product added manually'}), 201

@main_bp.route('/api/products/batch_delete', methods=['POST'])
def batch_delete_products():
    data = request.json
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'message': 'No IDs provided'}), 400
        
    try:
        if ids == 'ALL':
             num_deleted = db.session.query(Product).delete()
        else:
             num_deleted = db.session.query(Product).filter(Product.id.in_(ids)).delete(synchronize_session=False)

        db.session.commit()
        return jsonify({'message': f'Deleted {num_deleted} products successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting products: {str(e)}'}), 500

@main_bp.route('/api/products/<int:id>', methods=['GET', 'DELETE', 'PUT'])
def product_detail(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'message': 'Product not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': product.id,
            'item_id': product.item_id,
            'name': product.name,
            'image': product.image_url,
            'price': product.price,
            'category': product.item_type.name if product.item_type else product.category_label,
            'sub_category': product.category.name if product.category else product.sub_category_label,
            'style': product.style_ref.name if product.style_ref else product.style_label,
            'shop_name': product.shop_name,
            'product_url': product.product_url,
            'color': product.color.name if product.color else product.color_label,
            'color_tone': product.color.tone if product.color else product.color_tone,
            'season': product.season_ref.name if product.season_ref else product.season_label,
            'occasion': product.occasion_ref.name if product.occasion_ref else product.occasion_label,
            'gender': product.gender,
            'material': product.material,
            'fit_type': product.fit_type,
            'details': product.details,
        }), 200

    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200

    if request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({'message': 'No changes provided'}), 400

        if 'name' in data:
            product.name = data['name']
        if 'price' in data:
            try:
                product.price = int(float(data['price']))
            except (TypeError, ValueError):
                pass
        if 'image' in data:
            product.image_url = data['image']
        if 'product_url' in data:
            product.product_url = data['product_url']
        elif 'shopee_link' in data:
            product.product_url = data['shopee_link']
        if 'shop_name' in data:
            product.shop_name = data['shop_name']
        if 'gender' in data:
            product.gender = data['gender']
        if 'material' in data:
            product.material = data['material']
        if 'fit_type' in data:
            product.fit_type = data['fit_type']
        if 'details' in data:
            product.details = data['details']

        category_field = data.get('category')
        sub_category_name = data.get('sub_category')

        if category_field or sub_category_name:
            if category_field and isinstance(category_field, str) and '|' in category_field:
                item_type_name, sub_category_name = [part.strip() for part in category_field.split('|', 1)]
            else:
                item_type_name = str(category_field).strip() if category_field else (product.item_type.name if product.item_type else product.category_label or 'Other')
                sub_category_name = sub_category_name or product.category.name if product.category else product.sub_category_label or 'Other'

            item_type = get_or_create(ItemType, name=item_type_name)
            category = get_or_create(Category, name=sub_category_name, defaults={'item_type': item_type})
            product.item_type = item_type
            product.category = category
            product.category_label = item_type_name[:50]
            product.sub_category_label = sub_category_name[:50]

        if 'style' in data:
            style_name = data['style'] or 'Casual'
            style = get_or_create(Style, name=style_name)
            product.style_ref = style
            product.style_label = style_name[:50]

        if 'color' in data or 'color_tone' in data:
            color_name = data.get('color', product.color.name if product.color else product.color_label or 'Multicolor')
            color_tone = data.get('color_tone', product.color.tone if product.color else product.color_tone or 'Pattern')
            color = get_or_create(Color, name=color_name, defaults={'tone': color_tone})
            if color.tone != color_tone and color_tone:
                color.tone = color_tone
            product.color = color
            product.color_label = color_name[:50]
            product.color_tone = color_tone[:20]

        if 'season' in data:
            season_name = data['season'] or 'All-season'
            season = get_or_create(Season, name=season_name)
            product.season_ref = season
            product.season_label = season_name[:50]

        if 'occasion' in data:
            occasion_name = data['occasion'] or 'Daily wear'
            occasion = get_or_create(Occasion, name=occasion_name)
            product.occasion_ref = occasion
            product.occasion_label = occasion_name[:50]

        db.session.commit()
        return jsonify({'message': 'Product updated successfully'}), 200


@main_bp.route('/api/dataset', methods=['GET'])
def export_dataset():
    export_format = (request.args.get('format') or 'json').lower()
    products = (
        Product.query
        .outerjoin(ItemType)
        .outerjoin(Category)
        .outerjoin(Color)
        .outerjoin(Style)
        .outerjoin(Season)
        .outerjoin(Occasion)
        .all()
    )

    dataset = []
    for p in products:
        dataset.append({
            'name': p.name,
            'item_type': p.item_type.name if p.item_type else p.category_label,
            'category': p.category.name if p.category else p.sub_category_label,
            'color': p.color.name if p.color else p.color_label,
            'color_tone': p.color.tone if p.color else p.color_tone,
            'style': p.style_ref.name if p.style_ref else p.style_label,
            'season': p.season_ref.name if p.season_ref else p.season_label,
            'occasion': p.occasion_ref.name if p.occasion_ref else p.occasion_label,
            'gender': p.gender,
            'material': p.material,
            'fit_type': p.fit_type,
            'price': p.price,
            'product_url': p.product_url,
        })

    if export_format == 'csv':
        output = io.StringIO()
        fieldnames = [
            'name',
            'item_type',
            'category',
            'color',
            'color_tone',
            'style',
            'season',
            'occasion',
            'gender',
            'material',
            'fit_type',
            'price',
            'product_url',
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=fashion_dataset.csv'},
        )

    return jsonify({'count': len(dataset), 'items': dataset}), 200


@main_bp.route('/api/tryon', methods=['GET'])
def tryon():
    return jsonify({'status': 'success'}), 200
