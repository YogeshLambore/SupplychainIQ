import os, sys, json
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.ocr_engine import LocalOCREngine

def test_real_image():
    img_path = r"E:\SupplyChain AI prototype\data\uploads\sess_20260916_204723_6a207b_diagram.jpg"
    if not os.path.exists(img_path):
        print("Image not found:", img_path)
        return
        
    img = Image.open(img_path)
    print("Original image size:", img.size)
    
    ocr = LocalOCREngine()
    result = ocr.run(img)
    
    print("OCR status:", result["status"])
    print("Number of detections:", len(result["findings"]))
    
    # In LocalOCREngine, tile usage relies on size > 1200
    w, h = img.size
    print(f"Used tiling: {max(w, h) > 1200}")
    
    print("\nEXPECTED TEXT VERIFICATION:")
    expected = [
        "ITEM 1 BODY",
        "ITEM 2 HANDLE",
        "ITEM 3 PIVOT STUD",
        "ITEM 4 COLLAR",
        "ITEM 5 PIN",
        "CONTROL HANDLE ASSEMBLY",
        "SECTION Y-Y"
    ]
    
    # Build text corpus for fuzzy matching
    found_texts = [f["text"].upper() for f in result["findings"]]
    raw_findings = result["findings"]
    
    print(f"{'Visible text':<25} | {'Detected?':<10} | {'Actual OCR text':<30} | {'Confidence':<10} | BBox")
    print("-" * 100)
    
    for exp in expected:
        match = None
        exact = False
        for f in raw_findings:
            if exp in f["text"].upper():
                match = f
                exact = True
                break
            # weak fuzzy match
            elif exp.split()[0] in f["text"].upper() and exp.split()[-1] in f["text"].upper():
                match = f
                break
                
        if match:
            status = "FOUND" if exact else "PARTIAL"
            print(f"{exp:<25} | {status:<10} | {match['text']:<30} | {match['confidence']:<10} | {match['bbox']}")
        else:
            print(f"{exp:<25} | {'NOT_FOUND':<10} | {'':<30} | {'':<10} | ")
            
if __name__ == "__main__":
    test_real_image()
