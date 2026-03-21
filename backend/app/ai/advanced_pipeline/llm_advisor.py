import requests
import json

class FashionLLM:
    """
    LLM Interface for providing fashion advice using localized Ollama.
    Optimized for Llama 3.2 3B via API.
    """
    def __init__(self, model_id="llama3.2:3b", host="http://localhost:11434"):
        self.model_id = model_id
        self.host = host
        print(f"Initialized LLM Advisor using Ollama model: {self.model_id} at {self.host}")

    def generate_advice(self, user_info):
        """
        user_info: dict with keys {gender, body_shape, measurements}
        """
        prompt = f"""Bạn là một chuyên gia tư vấn thời trang cao cấp. Dựa trên thông tin người dùng:
- Giới tính: {user_info.get('gender', 'N/A')}
- Dáng người: {user_info.get('body_shape', 'N/A')}
- Số đo chi tiết: Vai {user_info.get('measurements', {}).get('shoulder', 'N/A')}cm, Ngực {user_info.get('measurements', {}).get('chest', 'N/A')}cm, Eo {user_info.get('measurements', {}).get('waist', 'N/A')}cm, Hông {user_info.get('measurements', {}).get('hip', 'N/A')}cm.

Hãy gợi ý 3 bộ trang phục hoàn chỉnh (gồm áo, quần/váy) phù hợp để tôn lên ưu điểm và che khuyết điểm của dáng người này.
Trả về bằng tiếng Việt, cấu trúc nghiêm ngặt bằng JSON như sau:
{{
  "recommendations": [
    {{ "title": "Tên bộ 1", "top_description": "Mô tả áo...", "bottom_description": "Mô tả quần/váy...", "reason": "Lý do phù hợp..." }},
    {{ "title": "Tên bộ 2", "top_description": "Mô tả áo...", "bottom_description": "Mô tả quần/váy...", "reason": "Lý do phù hợp..." }},
    {{ "title": "Tên bộ 3", "top_description": "...", "bottom_description": "...", "reason": "..." }}
  ]
}}
Không trả lời thêm bất cứ nội dung nào ngoài JSON.
"""
        try:
            response = requests.post(
                f'{self.host}/api/generate',
                json={
                    'model': self.model_id,
                    'prompt': prompt,
                    'stream': False,
                    'format': 'json'  # Force JSON output for Ollama 3.x
                },
                timeout=60
            )
            response.raise_for_status()
            
            # The response from Ollama is a JSON string containing our data
            raw_output = response.json().get('response', '')
            
            # Find JSON block (if any formatting leaked)
            json_start = raw_output.find('{')
            json_end = raw_output.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                return json.loads(raw_output[json_start:json_end])
            else:
                return json.loads(raw_output)
                
        except json.JSONDecodeError:
            print(f"[Ollama LLM] Failed to parse JSON: {raw_output}")
            return {"error": "Invalid format returned by LLM."}
        except Exception as e:
            print(f"[Ollama LLM] API Error: {e}")
            return {"error": "Could not connect to Ollama local server."}
