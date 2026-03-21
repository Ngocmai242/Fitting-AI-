import os
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.models import Product

class VectorSearchEngine:
    """
    Tìm kiếm sản phẩm sử dụng Vector Embedding thay vì query SQL chay.
    Dùng cho 'Tìm kiếm sản phẩm bằng vector (Sentence-BERT)'.
    """
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print(f"[VectorSearch] Initializing Sentence Transformer: {model_name}")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = SentenceTransformer(model_name, device=self.device)
        self.embeddings = None
        self.product_index = []  # List of product IDs corresponding to embeddings
    
    def build_index(self, db_session):
        """Build product index. Call this periodically or on app startup."""
        print("[VectorSearch] Building product embeddings...")
        products = db_session.query(Product).all()
        
        texts = []
        self.product_index = []
        for p in products:
            # Combine relevant fields for text representation
            cat = getattr(p, "category_label", "") or ""
            sub_cat = getattr(p, "sub_category_label", "") or ""
            desc = p.description or ""
            text = f"{p.name} {cat} {sub_cat} {desc}".strip()
            
            texts.append(text)
            self.product_index.append(p.id)
            
        if not texts:
            print("[VectorSearch] No products found to index.")
            return

        with torch.no_grad():
            self.embeddings = self.model.encode(texts, show_progress_bar=True)
            
        print(f"[VectorSearch] Built index for {len(self.product_index)} products.")

    def search_similar(self, db_session, query: str, top_k: int = 5):
        """Return Top K products matching the query"""
        if self.embeddings is None or len(self.product_index) == 0:
            print("[VectorSearch] Index not built yet. Building now...")
            self.build_index(db_session)
            
        if self.embeddings is None or len(self.product_index) == 0:
            return []

        # Encode user query
        query_vec = self.model.encode([query])
        
        # Calculate cosine similarity between query and all products
        scores = cosine_similarity(query_vec, self.embeddings)[0]
        
        # Get top matches
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            product_id = self.product_index[idx]
            match_score = scores[idx]
            
            p = db_session.query(Product).get(product_id)
            if p:
                results.append(p)
                
        return results

# Singleton instance
vector_searcher = VectorSearchEngine()
