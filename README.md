# AuraFit (Fitting-AI) - AI Virtual Try-On & Style Recommendation System

AuraFit is an advanced e-commerce solution that leverages state-of-the-art Artificial Intelligence to provide a seamless and realistic online shopping experience. The system combines high-fidelity virtual fitting with personalized style recommendations based on body shape analysis.

## 🚀 Key Features

1.  **AI Virtual Try-On**: Try on clothes using your own photos with high realism. The system employs a multi-tier fallback pipeline utilizing SOTA models (TryOna, Fashn-VTON, IDM-VTON) to ensure a 100% success rate.
2.  **Smart Styling & Recommendations**: Uses Computer Vision (YOLOv8) to analyze user body shape and metrics, providing personalized outfit suggestions based on professional fashion rules.
3.  **Automated Data Engine**: Integrated Shopee crawler with AI-powered background removal and image cleaning for high-quality product listings.

---

## 🛠️ System Architecture

-   **Frontend**: Vanilla JavaScript, HTML5, and CSS3. Features a minimalist pastel design for a premium user experience.
-   **Backend**: Python Flask API orchestrating AI workflows, user sessions, and product management.
-   **AI Engine**:
    *   **Computer Vision**: YOLOv8 for clothing detection and classification.
    *   **Image Processing**: U2-Net / BirefNet for automated background removal.
    *   **Virtual Try-On**: Multi-tier API integration (TryOna, API4AI, HuggingFace, RapidAPI).
-   **Database**: SQLite managed via SQLAlchemy ORM.

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python**: 3.9 or higher.
- **Node.js**: Latest stable version.

### 2. Environment Setup
Clone the repository and install the required dependencies:

```bash
# Install Python libraries
pip install -r backend/requirements.txt
pip install -r requirements_ai.txt

# Install Playwright browsers for the Crawler
playwright install

# Install Node.js tools and server management packages
npm install
```

### 3. Configuration
Configure your environment variables in `backend/.env`:
```env
TRYONA_API_KEY="Your_Private_Key"
HF_TOKEN="Your_HuggingFace_Token"
RAPIDAPI_KEY="Your_RapidAPI_Key"
```

---

## 🏃 How to Run the System

The system is designed for ease of use with multiple ways to start the services.

### Option 1: Using NPM (Recommended)
Run a single command to start both the backend and frontend simultaneously:
```bash
npm start
```

### Option 2: Using Batch Files (Windows)
Double-click `Run_Project_Final.bat` in the root directory. This will:
1.  Check and install missing requirements.
2.  Launch the **VITON-HD Local API**.
3.  Start the **Flask Production Server** (Waitress).
4.  Automatically open the **Admin Dashboard** in your default browser.

---

## 📊 AI Pipeline Details

### 1. Multi-Tier VTON Fallback
To ensure high availability and quality, the system attempts inference in the following order:
- **Tier 1**: TryOna API (Primary - Best detail preservation).
- **Tier 2**: API4AI Virtual Try On (Key 1).
- **Tier 3**: API4AI Virtual Try On (Key 2 Fallback).
- **Tier 4**: Fashn-VTON 1.5 (HuggingFace).
- **Tier 5**: IDM-VTON (HuggingFace).
- **Tier 6**: Texel Moda (RapidAPI).

### 2. Post-Processing Excellence
- **Background Normalization**: Products are automatically aligned to a 768x1024 ratio.
- **Exact Color Match**: Uses Reinhard Color Transfer to prevent overexposure and ensure garment colors match the original product photo.
- **Reverse Inpainting**: Segments original body parts (like legs/arms) and background to ensure anatomical integrity and 100% preservation of non-replaced clothing items.

---

## 🔑 Access Information

-   **Admin Dashboard**:
    *   URL: `http://localhost:8080/admin_login.html`
    *   Default Credentials: `admin` / `admin`
-   **Customer Homepage**: `http://localhost:8080/index.html`

---

## 📂 Project Structure
```text
├── backend/            # Flask API, routes, and business logic
├── frontend/           # Web interface (HTML/CSS/JS)
├── data_engine/        # Crawler and data processing scripts
├── VITON-HD/           # Local VTON API components
├── database/           # SQLite database files
└── scripts/            # Utility and maintenance scripts
```
