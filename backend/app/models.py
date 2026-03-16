from datetime import datetime

from . import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default="USER")

    fullname = db.Column(db.String(100))
    avatar = db.Column(
        db.String(500),
        default="https://ui-avatars.com/api/?name=User&background=FF9EB5&color=fff",
    )
    address = db.Column(db.String(200))
    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ItemType(db.Model):
    __tablename__ = "item_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    categories = db.relationship("Category", back_populates="item_type", lazy=True)
    products = db.relationship("Product", back_populates="item_type", lazy=True)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    item_type_id = db.Column(db.Integer, db.ForeignKey("item_types.id"), nullable=False)

    item_type = db.relationship("ItemType", back_populates="categories")
    products = db.relationship("Product", back_populates="category", lazy=True)


class Color(db.Model):
    __tablename__ = "colors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    tone = db.Column(db.String(20), nullable=False, default="Neutral")

    products = db.relationship("Product", back_populates="color", lazy=True)


class Style(db.Model):
    __tablename__ = "styles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    products = db.relationship("Product", back_populates="style_ref", lazy=True)


class Season(db.Model):
    __tablename__ = "seasons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)

    products = db.relationship("Product", back_populates="season_ref", lazy=True)


class Occasion(db.Model):
    __tablename__ = "occasions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    products = db.relationship("Product", back_populates="occasion_ref", lazy=True)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500))
    product_url = db.Column(db.String(2000))
    # Virtual Try-On / Smart Styling
    shopee_url = db.Column(db.Text)
    style_tag = db.Column(db.Text)
    body_shape_tag = db.Column(db.Text)
    price = db.Column(db.Integer)
    price_display = db.Column(db.String(50))
    details = db.Column(db.String(200))
    shop_name = db.Column(db.String(150))
    shop_id = db.Column(db.String(100))
    rating = db.Column(db.Float, default=0)
    sold_count = db.Column(db.Integer, default=0)
    crawl_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_valid = db.Column(db.Boolean, default=True)

    ai_category = db.Column(db.String(100))
    classification = db.Column(db.Text)  # Stores JSON string of classification details

    # Relational taxonomy
    item_type_id = db.Column(db.Integer, db.ForeignKey("item_types.id"))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id"))
    style_id = db.Column(db.Integer, db.ForeignKey("styles.id"))
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"))
    occasion_id = db.Column(db.Integer, db.ForeignKey("occasions.id"))

    gender = db.Column(db.String(20))
    material = db.Column(db.String(100))
    fit_type = db.Column(db.String(50))
    color_tone = db.Column(db.String(20))
    clean_image_path = db.Column(db.String(255))
    color_primary = db.Column(db.String(50))
    color_secondary = db.Column(db.String(50))
    hex_primary = db.Column(db.String(10))
    season = db.Column(db.String(50))
    occasion = db.Column(db.String(50))

    # Denormalized labels for backwards compatibility with existing UI
    category_label = db.Column(db.String(50))
    sub_category_label = db.Column(db.String(50))
    color_label = db.Column(db.String(50))
    style_label = db.Column(db.String(50))
    season_label = db.Column(db.String(50))
    occasion_label = db.Column(db.String(50))

    item_type = db.relationship("ItemType", back_populates="products")
    category = db.relationship("Category", back_populates="products")
    color = db.relationship("Color", back_populates="products")
    style_ref = db.relationship("Style", back_populates="products")
    season_ref = db.relationship("Season", back_populates="products")
    occasion_ref = db.relationship("Occasion", back_populates="products")


class Outfit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500))
    body_type = db.Column(db.String(50))
    style = db.Column(db.String(50))
    color = db.Column(db.String(50))
    color_tone = db.Column(db.String(50))
    shop_link = db.Column(db.String(500))


db.Index("ix_products_item_id", Product.item_id, unique=True)
