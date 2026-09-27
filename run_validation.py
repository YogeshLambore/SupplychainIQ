import base64, io, json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.ocr_engine import LocalOCREngine

def test_1_real_ocr():
    print("==================================================")
    print("TEST 1 — REAL OCR")
    print("==================================================")
    img = Image.new("RGB", (600, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    labels = ["P-101", "P-102", "V-201", "TK-301", "PT-101", "FT-102"]
    
    for i, lbl in enumerate(labels):
        x = 50 + (i % 3) * 150
        y = 50 + (i // 3) * 150
        draw.text((x, y), lbl, fill=(0, 0, 0))
        
    ocr = LocalOCREngine()
    result = ocr.run(img)
    
    print("Expected labels:", labels)
    findings = result.get("findings", [])
    print(f"Total findings: {len(findings)}")
    for f in findings:
        print(f"Detected: {f['text']:<10} | Conf: {f['confidence']} | Bbox: {f['bbox']}")

if __name__ == "__main__":
    test_1_real_ocr()
