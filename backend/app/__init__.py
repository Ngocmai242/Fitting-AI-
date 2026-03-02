import os
import sys

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

db = SQLAlchemy()


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "..", "..", "frontend")
    frontend_dir = os.path.abspath(frontend_dir)

    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.secret_key = "super_secret_key_for_session_management"

    codespace_name = os.getenv("CODESPACE_NAME")

    if codespace_name:
        CORS(app, resources={r"/*": {"origins": "*"}})
    else:
        CORS(app, resources={r"/*": {"origins": "*"}})

    db_path = os.path.join(base_dir, "..", "..", "database", "database_v2.db")
    db_path = os.path.abspath(db_path)

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        from . import models, routes  # noqa: F401

        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path))

        db.create_all()
        seed_reference_data()
        seed_data()

    from .routes import main_bp

    app.register_blueprint(main_bp)

    return app


def seed_reference_data():
    from data_engine.feature_engine import get_reference_taxonomy
    from .models import (
        Category,
        Color,
        ItemType,
        Occasion,
        Season,
        Style,
    )

    taxonomy = get_reference_taxonomy()

    item_types_map = dict(taxonomy["item_types"])
    item_types_map.setdefault("Other", ["Other"])

    for item_type_name, categories in item_types_map.items():
        item_type = ItemType.query.filter_by(name=item_type_name).first()
        if not item_type:
            item_type = ItemType(name=item_type_name)
            db.session.add(item_type)
            db.session.flush()

        for category_name in categories:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                db.session.add(Category(name=category_name, item_type=item_type))

    for color_name, tone in taxonomy["colors"].items():
        if not Color.query.filter_by(name=color_name).first():
            db.session.add(Color(name=color_name, tone=tone))

    for style_name in taxonomy["styles"]:
        if not Style.query.filter_by(name=style_name).first():
            db.session.add(Style(name=style_name))

    for season_name in taxonomy["seasons"]:
        if not Season.query.filter_by(name=season_name).first():
            db.session.add(Season(name=season_name))

    for occasion_name in taxonomy["occasions"]:
        if not Occasion.query.filter_by(name=occasion_name).first():
            db.session.add(Occasion(name=occasion_name))

    db.session.commit()


def seed_data():
    from werkzeug.security import generate_password_hash

    from .models import Outfit, User

    if not Outfit.query.first():
        seed_outfits = [
            Outfit(
                name="Summer Floral Dress",
                image_url="https://images.unsplash.com/photo-1572804013427-4d7ca7268217?w=500",
                style="Casual",
                shop_link="https://shopee.vn/dress1",
                body_type="Hourglass",
            ),
            Outfit(
                name="Office Blazer Set",
                image_url="https://images.unsplash.com/photo-1487222477894-8943e31ef7b2?w=500",
                style="Office",
                shop_link="https://lazada.vn/suit1",
                body_type="Rectangle",
            ),
        ]
        db.session.add_all(seed_outfits)
        db.session.commit()

    if not User.query.filter_by(username="admin").first():
        admin_user = User(
            username="admin",
            email="admin@aurafit.com",
            password=generate_password_hash("admin"),
            role="ADMIN",
            fullname="System Administrator",
            avatar="https://ui-avatars.com/api/?name=Admin&background=0D8ABC&color=fff",
        )
        db.session.add(admin_user)
        db.session.commit()
