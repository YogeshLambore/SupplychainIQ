import os, sys, json, base64, io
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.ocr_engine import LocalOCREngine
from core.engineering_analyzer import EngineeringAnalyzer

def make_test_drawing():
    img = Image.new("RGB", (1800, 1600), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    labels = [
        ("ITEM 1 BODY", 100, 100),
        ("ITEM 2 HANDLE", 800, 100),
        ("ITEM 3 PIVOT STUD", 1500, 100),
        ("ITEM 4 COLLAR", 100, 1400),
        ("ITEM 5 PIN", 800, 1400),
        ("CONTROL HANDLE ASSEMBLY", 1400, 1400),
        ("SECTION Y-Y", 800, 800)
    ]
    for lbl, x, y in labels:
        draw.text((x, y), lbl, fill=(0, 0, 0))
    return img

def test_ocr():
    print("=== TEST 2: OCR CONTENT VERIFICATION ===")
    img = make_test_drawing()
    ocr = LocalOCREngine()
    result = ocr.run(img)
    print("STATUS:", result["status"])
    print("FINDINGS:", len(result["findings"]))
    for f in result["findings"]:
        print(f"TEXT: {f['text']:<25} | CONF: {f['confidence']} | BBOX: {f['bbox']}")

def test_parser_fallback():
    print("\n=== TEST 4: PARSER FAILURE RECOVERY ===")
    
    class MockLLM:
        def generate(self, **kwargs):
            return "This is completely invalid JSON that will fail."
            
    class MockImgProc:
        def query_vision_model(self, base64_img, prompt):
            return "Simulated Moondream output for " + prompt[:30]

    analyzer = EngineeringAnalyzer(llm_manager=MockLLM(), img_processor=MockImgProc())
    
    # 1x1 image
    img = Image.new("RGB", (20, 20), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    
    res = analyzer.multi_pass_vision(b64, "test")
    print("FINAL VISUAL STATE:", res.get("claims", [{"status": res.get("status")}])[0])
    
if __name__ == "__main__":
    test_ocr()
    test_parser_fallback()
