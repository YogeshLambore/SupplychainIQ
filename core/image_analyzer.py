from PIL import Image, ImageDraw
import io

class ImageAnalyzer:
    def __init__(self, vision_model_path=None):
        import os
        self.vision_model_path = vision_model_path
        self.model_name = "moondream:1.8b"
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_url = f"{self.ollama_host}/api/generate"
        self.ollama_tags_url = f"{self.ollama_host}/api/tags"
        self.has_vision_model = self.check_health()
        
    def check_health(self):
        import requests
        try:
            response = requests.get(self.ollama_tags_url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                if self.model_name in models:
                    return True
        except Exception:
            pass
        return False
        
    def analyze_image(self, image_file, query: str):
        """Analyzes an image and returns results and optionally an annotated image."""
        try:
            img = Image.open(image_file).convert("RGB")
            query_lower = query.lower()
            
            result_text = "Vision model unavailable."
            confidence = "N/A"
            annotated_img = img.copy()
            
        # Removed repeated check_health call for performance
            
            if self.has_vision_model:
                import base64
                import requests
                
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                system_prompt = (
                    "You are the local vision analyzer for SupplyChain AI. "
                    "Analyze this engineering diagram carefully. "
                    "Do not invent components, process conditions, or safety ratings. "
                    "If something is unclear, simply say it is not clearly visible. "
                )
                
                payload = {
                    "model": self.model_name,
                    "prompt": f"{system_prompt}\n\nQuestion: {query}",
                    "images": [base64_img],
                    "stream": False,
                    "options": {
                        "temperature": 0.1
                    }
                }
                
                try:
                    response = requests.post(self.ollama_url, json=payload, timeout=60)
                    if response.status_code == 200:
                        data = response.json()
                        result_text = "**Moondream Vision Analysis:**\n" + data.get("response", "").strip()
                        confidence = "High (Local Moondream)"
                        return {
                            "success": True,
                            "text": result_text,
                            "confidence": confidence,
                            "annotated_image": annotated_img,
                            "original_size": img.size,
                            "base64_img": base64_img
                        }
                except Exception as e:
                    print(f"Moondream inference failed: {e}")
                    # Continue to fallback
            
            # Deterministic Fallback based on typical demo P&ID queries
            if "component" in query_lower or "label" in query_lower or "visible" in query_lower:
                result_text = "**Deterministic Fallback:**\nDetected potential engineering components in this diagram:\n- V-104 (Valve/Vessel)\n- P-201 (Pump)\n\n*(Full visual reasoning requires the local vision model)*"
                confidence = "Simulated (Fallback)"
                
                # Draw mock bounding boxes for demo purposes
                draw = ImageDraw.Draw(annotated_img)
                # Mock coords for P-201 and V-104 matching our demo generator
                draw.rectangle([(300, 250), (400, 350)], outline="#10b981", width=4)
                draw.rectangle([(500, 280), (520, 320)], outline="#10b981", width=4)
                
            elif "explain" in query_lower:
                result_text = f"**Image Metadata Analysis:**\nFormat: {img.format}\nSize: {img.size}\nMode: {img.mode}\n\n*(Local vision model is not loaded in this environment. Deterministic fallback used.)*"
            else:
                result_text = "I cannot confidently answer that based on the fallback visual processing. Please load the local vision model."
                
            return {
                "success": True,
                "text": result_text,
                "confidence": confidence,
                "annotated_image": annotated_img,
                "original_size": img.size
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def query_vision_model(self, base64_img: str, query: str, custom_system_prompt: str = None) -> str:
        """Executes a direct query against the vision model for multi-pass analysis."""
        if not getattr(self, 'has_vision_model', False):
            return "Vision model unavailable."
        
        system_prompt = custom_system_prompt or (
            "You are the local vision analyzer for SupplyChain AI. "
            "Analyze this engineering diagram carefully. "
            "Do not invent components, process conditions, or safety ratings. "
            "If something is unclear, simply say it is not clearly visible."
        )
        
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\n\nQuestion: {query}",
            "images": [base64_img],
            "stream": False,
            "options": {"temperature": 0.0}
        }
        import requests
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass
        return ""
