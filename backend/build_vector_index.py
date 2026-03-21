from app import create_app, db
from app.ai.advanced_pipeline.vector_search import vector_searcher

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        print("Bắt đầu xử lý Vector Embedding cho toàn bộ sản phẩm trong Database...")
        vector_searcher.build_index(db.session)
        print("Xong!")
