from . import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default='USER')
    
    # Simple profile fields
    fullname = db.Column(db.String(100))
    avatar = db.Column(db.String(500), default='https://ui-avatars.com/api/?name=User&background=FF9EB5&color=fff')
    address = db.Column(db.String(200))
    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(500))
    shopee_link = db.Column(db.String(2000))
    price = db.Column(db.Float)
    category = db.Column(db.String(50)) # top/bottom/dress/accessory
    sub_category = db.Column(db.String(50))
    gender = db.Column(db.String(50))  # Nam/Nữ/Unisex/Trẻ em
    material = db.Column(db.String(100))  # Cotton, Kaki, Jeans, etc.
    style = db.Column(db.String(50))
    details = db.Column(db.String(200))  # Cổ tròn, Tay ngắn, etc.
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
