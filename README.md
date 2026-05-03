# AuraFit (Fitting-AI) - AI Virtual Try-On & Style Recommendation System

## Introduction
AuraFit (Fitting-AI) is an e-commerce platform integrating Artificial Intelligence (AI) to provide a realistic online shopping experience:
1. Virtual Try-On: Try clothes on your actual photos with high realism. The system uses a multi-tier fallback pipeline with SOTA models to ensure 100% success rate and high speed.
2. Smart Styling: Analyzes Body Shape using Computer Vision algorithms, then combines fashion rules to provide personalized outfit recommendations.

## Project Structure
- /frontend/: User Interface (HTML, CSS, Vanilla JS).
- /backend/: API Server orchestrating the entire system (Python & Flask).
  - /backend/app/routes.py: Core logic for Virtual Try-On with automated fallback mechanism.
- /data_engine/: Automated web scraping (Crawler) and garment background removal system.
- /database/: Stores user information and product catalogs (SQLite).

## Installation & Getting Started
The system uses npm to manage and run both the frontend and backend simultaneously.

1. System Requirements
- Python 3.9+
- Node.js (latest version)

2. Environment Setup
Open the Terminal at the project root directory and run:
# Install Python libraries
pip install -r backend/requirements.txt
pip install -r requirements_ai.txt

# Install Playwright for the Crawler
playwright install

# Install Node.js tools
npm install

3. Environment Variables (.env)
Edit the backend/.env file with your API Keys:
TRYONA_API_KEY="Your Private Key"
HF_TOKEN="HuggingFace Token"
RAPIDAPI_KEY="RapidAPI Key"

4. Start the System
Run a single command:
npm start

This command will automatically:
- Launch the Python Flask Backend on port 8080.
- Serve the Frontend interface.
- Automatically open your browser to the Admin Dashboard.

## AI Pipeline Architecture (Virtual Try-On)
The system utilizes a multi-tier processing workflow to maximize quality and reliability:

1. API Priority (Fallback Pipeline):
- Tier 1: TryOna API (Primary - Best for pose and garment detail preservation).
- Tier 2: Virtual Try On (API4AI - Key 1).
- Tier 3: Virtual Try On (API4AI - Key 2 Fallback).
- Tier 4: Fashn-VTON 1.5 (HuggingFace).
- Tier 5: IDM-VTON (HuggingFace).
- Tier 6: Texel Moda (RapidAPI).

2. Advanced Post-Processing:
- Background Removal & Normalization: Automatically removes product backgrounds and aligns them to 768x1024 ratio.
- Exact Color Match: Uses Reinhard Color Transfer with background masking to ensure the garment color in the result perfectly matches the original product photo without overexposure.
- Reverse Inpainting: Uses the U2Net model to segment the original pants/skirt and background, then pastes them back onto the AI result. This ensures 100% preservation of the original lower-body clothes and prevents loss of limbs or anatomical distortions.

## Demo Access Information
- Admin Dashboard:
  - URL: http://localhost:8080/admin_login.html
  - User: admin
  - Pass: admin
- Customer Homepage: http://localhost:8080/index.html
