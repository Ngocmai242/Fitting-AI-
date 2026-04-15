from flask import Flask, request, jsonify
from smpl_engine import SMPLEngine
from classifier import ClassifierEngine
from llm_advisor import FashionLLM
import os

app = Flask(__name__)

# Constants
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

# Initialize engines (lazy load to avoid memory issues on startup)
class FashionPipeline:
    def __init__(self):
        self.smpl = None
        self.classifier = None
        self.llm = None

    def lazy_init(self):
        if not self.smpl:
            self.smpl = SMPLEngine(model_dir=MODEL_DIR)
        if not self.classifier:
            self.classifier = ClassifierEngine(model_path=os.path.join(MODEL_DIR, 'efficientnet_body.pth'))
        if not self.llm:
            self.llm = FashionLLM(model_id="llama3.2:3b")

pipeline = FashionPipeline()

@app.route('/api/ai/advanced/analyze', methods=['POST'])
def analyze_body():
    """
    Final Integrated Endpoint
    Input: Image File
    Output: Measurements (3D), Shape, Gender, AI Advice
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    pipeline.lazy_init()
    
    img_file = request.files['image']
    img_bytes = img_file.read()

    # 1. Classification (Gender & Body Shape)
    class_res = pipeline.classifier.predict(img_bytes)
    
    # 2. 3D Measurement (SMPL)
    # Automatically switch SMPL sex based on classification
    pipeline.smpl = SMPLEngine(sex=class_res['gender'].lower(), model_dir=MODEL_DIR)
    measurements = pipeline.smpl.predict_from_image(img_bytes)

    # 3. AI Advice (LLM)
    advice_payload = {
        "gender": class_res['gender'],
        "body_shape": class_res['body_shape'],
        "measurements": measurements
    }
    ai_advice = pipeline.llm.generate_advice(advice_payload)

    return jsonify({
        "status": "success",
        "analysis": {
            "gender": class_res['gender'],
            "body_shape": class_res['body_shape'],
            "confidence": class_res['confidence'],
            "measurements": measurements
        },
        "style_recommendations": ai_advice
    })

if __name__ == '__main__':
    # Default port for advanced pipeline service
    app.run(host='0.0.0.0', port=5000)
