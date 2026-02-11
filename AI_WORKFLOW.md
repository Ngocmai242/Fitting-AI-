
# AI & Data Workflow Setup

This document outlines how to use the newly created AI Training and Data Crawling modules.

## 1. Prerequisites

Before running any AI scripts, you need to install the dependencies.

```bash
pip install -r requirements_ai.txt
playwright install
```

## 2. Directory Structure

- **`data_engine/`**: Contains scripts for crawling storage.
    - `crawler_shopee.py`: The main script to scrape product data from Shopee.
- **`ai_engine/`**: Contains AI model definitions and training scripts.
    - `train_recommender.py`: A PyTorch-based training pipeline for the Outfit Recommender system.

## 3. Workflow 1: Crawling Data (Shopee)

The crawler uses `Playwright` to simulate a real browser interaction. It navigates, scrolls (to handle lazy loading), and extracts product details.

**To Run the Crawler:**

```bash
python data_engine/crawler_shopee.py
```

*Output:*
- The script will launch a browser (Chromium).
- It searches for keywords (e.g., "váy nữ", "áo thun nam").
- Scraped data is saved as a JSON file in `datasets/shopee_data/`.

## 4. Workflow 2: Training the AI Model

The recommender system uses a simple Neural Network (PyTorch) to predict the compatibility score between a User Profile and an Outfit.

**To Train the Model:**

```bash
python ai_engine/train_recommender.py
```

*Output:*
- The script simulates a training dataset (User Features + Outfit Features).
- It runs a training loop for 10 Epochs.
- The trained model is saved to `ai_engine/outfit_recommender.pth`.

## 5. Next Steps (Integration)

To connect this to your main Flask app:

1.  **Load the Model**: In `backend/app.py`, load the saved `outfit_recommender.pth`.
2.  **Inference API**: Create an endpoint `/api/recommend` that:
    - Takes User Body Stats from the request.
    - Loads the scraped products from `datasets/shopee_data/`.
    - Feeds User Stats + Product Features into the Model.
    - Returns the products with the highest scores.

---
**Note on Virtual Try-On:**
Training a full Virtual Try-On model (like VITON-HD or Stable Diffusion) requires powerful GPUs (NVIDIA RTX 3090+) and 10GB+ of VRAM. It is recommended to use an external API (like Replicate or HuggingFace Inference API) for this feature in a local/production environment initially.
