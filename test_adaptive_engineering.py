import os, sys, base64
from PIL import Image
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.engineering_analyzer import EngineeringAnalyzer
from core.ocr_engine import LocalOCREngine

# Mock LLM and Vision
class MockLLM:
    def generate(self, **kwargs):
        return """```json
{
  "metadata": {"diagram_type": "P&ID"},
  "components": [{"id": "C1", "type": "PUMP", "visible_tag": "P-101", "item_number": null, "status": "OBSERVED"}],
  "relationships": [{"source_id": "C1", "target_id": "BOUNDARY", "relationship": "connected_to", "boundary_continuation": true}]
}
```"""

class MockVision:
    def query_vision_model(self, *args, **kwargs):
        return "Observed pump P-101 connecting to boundary."

def test_adaptive_real_image():
    img_path = r"E:\Nexora prototype\data\uploads\sess_20260916_204723_6a207b_diagram.jpg"
    if not os.path.exists(img_path):
        print("Real image not found")
        return
        
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        
    analyzer = EngineeringAnalyzer(MockLLM(), MockVision(), LocalOCREngine())
    res = analyzer.generate_final_report("Analyze this", b64, "", "")
    
    # print("Markdown Report:\\n", res["markdown"])
    print("\nVisual State:", res["visual_state"])
    print("OCR Status:", res["ocr_status"])
    print("Total OCR Findings:", len(res["ocr_findings"]))

if __name__ == "__main__":
    print("=== ADAPTIVE REGION TEST ===")
    test_adaptive_real_image()
