# AuraFit (Fitting-AI) - AI Virtual Try-On & Style Recommendation

## 🌟 Introduction
AuraFit (Fitting-AI) is a cutting-edge e-commerce web platform integrating Artificial Intelligence (AI) to provide the most realistic and personalized online shopping experience:
1. **Virtual Try-On**: Try clothes on your actual photos with high realism. The system uses a Multi-tier Fallback Pipeline with SOTA models like Fashn-VTON, IDM-VTON, and RapidAPI Texel Moda to ensure a 100% success rate and blazing fast speed.
2. **Smart Styling**: Analyzes Body Shape using Computer Vision algorithms, then combines standard fashion rules to provide perfect outfit recommendations.

## 📁 Project Structure
- `/frontend/`: User Interface (HTML, Pastel Minimalism CSS, Vanilla JS).
- `/backend/`: API Server orchestrating the entire system (Python & Flask).
  - `/backend/app/routes.py`: Contains the core logic for the Virtual Try-On with Seamless Fallback mechanism.
- `/data_engine/`: Automated web scraping system (Crawler) using Playwright, and background removal for clothing images using YOLO/Rembg models.
- `/database/`: Stores user information, product catalogs, and crawl history (SQLite).
- `/ai_engine/`: Contains scripts for training machine learning models for fashion recommendations (PyTorch).

## 🚀 Installation & Getting Started
The system uses `npm` and `concurrently` to manage and run both the frontend and backend simultaneously with a single command.

### 1. System Requirements
- Python 3.9+
- Node.js (latest version)
- (Optional) CUDA-supported GPU if running AI models locally.

### 2. Environment Setup
Open the Terminal at the project root directory and run the following commands:
```bash
# Install all Python libraries for Backend and AI
pip install -r backend/requirements.txt
pip install -r requirements_ai.txt

# Install Playwright (Used for the Data Engine Crawler)
playwright install

# Install Node.js tools (for concurrent execution)
npm install
```

### 3. Environment Variables Configuration (.env)
Create or edit the `backend/.env` file with your important API Keys:
```env
# Tokens used to call HuggingFace Spaces (Comma-separated)
HF_TOKENS="hf_token1,hf_token2,..."
# The Ultimate Fallback (Fallback 5) for VTON
RAPIDAPI_KEY="your_rapidapi_key"
```

### 4. Start the System
With just a single command:
```bash
npm start
```
This command will automatically:
- Launch the Python Flask Backend on port `8080`.
- Serve the Frontend interface.
- Automatically open your browser directly to the Admin Dashboard.

---

## 🧠 AI Pipeline Architecture
The project's AI system utilizes a high-performance **Concurrent Multi-tier Pipeline**:
1. **Preprocessing**: Automatically removes product backgrounds using AI (`rembg`/`u2net`), then applies Smart Padding to fit the standard 768x1024 white background ratio with a `flat-lay` optimized perspective.
2. **Super-Fast Concurrent VTON**:
   - **Tier 1: Fashn-VTON 1.5 (HuggingFace)**: Launched in **Concurrent Mode** (all tokens tested simultaneously). Uses **50 Timesteps** and **2.0 Guidance Scale** for maximum texture detail and original color preservation.
   - **Tier 2: IDM-VTON (HuggingFace)**: Secondary fallback, also running in concurrent mode to maximize reliability within a strictly limited time budget.
   - **Tier 3 (Ultimate Fallback)**: Calls `Texel Moda` via RapidAPI to ensure a 100% success rate regardless of HuggingFace congestion.
3. **Optimized Integrity**: The pipeline is strictly configured to use **Segmentation-Free** processing and **Dynamic Photo-Type** detection, ensuring 100% preservation of human limbs (no missing hands/feet) and accurate garment borders.
4. **Natural Color Preservation**: Unlike standard pipelines that use aggressive post-processing color transfers, AuraFit relies on high-fidelity diffusion generation to keep 100% of the original product patterns and colors without artifacts.

## 📌 Demo Access Information
- **Admin Account**: 
  - Login: `http://localhost:8080/admin_login.html`
  - Default Username: `admin`
  - Default Password: `admin`
- **Customer Homepage**: `http://localhost:8080/index.html`
