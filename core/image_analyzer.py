from PIL import Image, ImageDraw
import io

class ImageAnalyzer:
    def __init__(self, vision_model_path=None):
        self.vision_model_path = vision_model_path
        self.has_vision_model = False
        # Here we'd load Moondream or Surya if available
        
    def analyze_image(self, image_file, query: str):
        """Analyzes an image and returns results and optionally an annotated image."""
        try:
            img = Image.open(image_file).convert("RGB")
            query = query.lower()
            
            result_text = "Vision model unavailable."
            confidence = "N/A"
            annotated_img = img.copy()
            
            # Deterministic Fallback based on typical demo P&ID queries
            if "component" in query or "label" in query or "visible" in query:
                result_text = "**Deterministic Fallback:**\nDetected potential engineering components in this diagram:\n- V-104 (Valve/Vessel)\n- P-201 (Pump)\n\n*(Full visual reasoning requires the local vision model)*"
                confidence = "Simulated (Fallback)"
                
                # Draw mock bounding boxes for demo purposes
                draw = ImageDraw.Draw(annotated_img)
                # Mock coords for P-201 and V-104 matching our demo generator
                draw.rectangle([(300, 250), (400, 350)], outline="#10b981", width=4)
                draw.rectangle([(500, 280), (520, 320)], outline="#10b981", width=4)
                
            elif "explain" in query:
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
