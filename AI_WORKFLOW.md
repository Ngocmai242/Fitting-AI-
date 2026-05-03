# AI & Data Inference Workflow

This document outlines the workflow for data collection and AI-powered recommendations within the AuraFit platform. Note that this system is designed to use pre-trained models for inference, and regular users do not need to perform AI training.

## 1. Prerequisites

To run the internal AI and data processing scripts:

```bash
pip install -r requirements_ai.txt
playwright install
```

## 2. Directory Structure

- **`data_engine/`**: Automated data collection and cleaning.
    - `crawler_shopee.py`: Scrapes product data from Shopee for the recommendation catalog.
- **`ai_engine/`**: Contains AI logic and pre-trained model weights.
    - `train_recommender.py`: Internal script used to generate recommendation logic weights.
    - `train_bodyshape.py`: Internal script for body shape classification logic.

## 3. Data Collection Workflow (Internal)

The system uses `Playwright` to simulate browser interactions for product discovery.

**To update the product catalog:**

```bash
python data_engine/crawler_shopee.py
```

*Output:*
- Scraped product details are saved to `datasets/shopee_data/`.
- Images are automatically cleaned using AI background removal (U2-Net).

## 4. Smart Recommendation Workflow

The recommendation engine uses an internal model to match user body stats with appropriate clothing styles.

**How it works (Backend Logic):**
1.  **User Profiling**: The system takes user input (height, weight, measurements).
2.  **Product Matching**: The engine calculates a compatibility score between the user profile and products in the catalog.
3.  **Output**: The top-scoring items are displayed as "AI Styled" recommendations on the frontend.

## 5. Virtual Try-On Integration

The Virtual Try-On feature utilizes a multi-tier API fallback system. It does NOT require local model training.

- **Primary Engine**: TryOna API (Cloud-based inference).
- **Secondary Engine**: Fashn-VTON / API4AI (Cloud-based inference).

---
*Note: For production, ensure all API keys are correctly configured in your .env file. Direct training of the Try-On model is not required as the system utilizes state-of-the-art pre-trained SOTA models via secure API gateways.*
