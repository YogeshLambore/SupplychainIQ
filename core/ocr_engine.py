"""
SupplyChain AI — Local OCR Engine
Uses RapidOCR (ONNX Runtime) — fully offline, no Tesseract binary needed.
"""
import io
import cv2
import numpy as np
from PIL import Image
import re
from typing import Optional

# ---- State constants --------------------------------------------------------
OCR_INSTALLED_AND_USABLE  = "OCR_INSTALLED_AND_USABLE"
OCR_PACKAGE_INSTALLED_MODEL_MISSING = "OCR_PACKAGE_INSTALLED_MODEL_MISSING"
OCR_NOT_INSTALLED         = "OCR_NOT_INSTALLED"
OCR_RUNTIME_FAILURE       = "OCR_RUNTIME_FAILURE"
OCR_UNAVAILABLE           = "OCR_UNAVAILABLE"


def check_ocr_health() -> dict:
    """Full health check for the local OCR engine."""
    report = {
        "ocr_engine":        "RapidOCR (ONNX Runtime)",
        "package":           "rapidocr-onnxruntime",
        "import":            "FAIL",
        "model_files":       "FAIL",
        "model_path":        None,
        "initialization":    "FAIL",
        "local_inference":   "FAIL",
        "internet_required": "NO",
        "offline_ready":     "NO",
        "status":            OCR_NOT_INSTALLED,
        "detail":            "",
    }

    try:
        from rapidocr_onnxruntime import RapidOCR
        report["import"] = "PASS"
    except ImportError as e:
        report["detail"] = f"Import error: {e}"
        return report

    try:
        import rapidocr_onnxruntime, os
        pkg_dir = os.path.dirname(rapidocr_onnxruntime.__file__)
        models_dir = os.path.join(pkg_dir, "models")
        required = [
            "ch_PP-OCRv4_det_infer.onnx",
            "ch_PP-OCRv4_rec_infer.onnx",
            "ch_ppocr_mobile_v2.0_cls_infer.onnx",
        ]
        missing = [m for m in required if not os.path.isfile(os.path.join(models_dir, m))]
        if missing:
            report["model_files"] = "FAIL"
            report["detail"]      = f"Missing model files: {missing}"
            report["status"]      = OCR_PACKAGE_INSTALLED_MODEL_MISSING
            return report
        report["model_files"] = "PASS"
        report["model_path"]  = models_dir
    except Exception as e:
        report["detail"] = f"Model check error: {e}"
        return report

    try:
        ocr = RapidOCR()
        report["initialization"] = "PASS"
    except Exception as e:
        report["detail"] = f"Init error: {e}"
        report["status"] = OCR_RUNTIME_FAILURE
        return report

    try:
        test_img = np.full((60, 200, 3), 255, dtype=np.uint8)
        cv2.putText(test_img, "P-101", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        result, _ = ocr(test_img)
        if result:
            report["local_inference"] = "PASS"
            report["status"]          = OCR_INSTALLED_AND_USABLE
            report["offline_ready"]   = "YES"
        else:
            report["local_inference"] = "PARTIAL"
            report["status"]          = OCR_INSTALLED_AND_USABLE
            report["offline_ready"]   = "YES"
            report["detail"]          = "Inference ran but returned no detections on test image."
    except Exception as e:
        report["local_inference"] = "FAIL"
        report["detail"]          = f"Inference error: {e}"
        report["status"]          = OCR_RUNTIME_FAILURE

    return report


def _pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _enhance_for_ocr(cv_img: np.ndarray, apply_upscale=True, apply_clahe=True) -> np.ndarray:
    """Adaptive preprocessing based on parameters."""
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    if apply_upscale:
        h, w = gray.shape
        if max(h, w) < 800:
            scale = 800 / max(h, w)
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            
    if apply_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def normalize_engineering_text(text: str) -> str:
    """Normalizes kerning/spacing issues in engineering texts."""
    t = text
    t = re.sub(r'(?i)ITEM\s*(\d+)', r'ITEM \1 ', t)
    
    terms = ["BODY", "HANDLE", "PIVOT", "STUD", "COLLAR", "PIN", "ASSEMBLY", "CONTROL", "SECTION"]
    for term in terms:
        t = re.sub(f'(?i)({term})', r' \1 ', t)
        
    t = re.sub(r'\s+', ' ', t).strip()
    return t if t else text


def _compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    if (boxAArea + boxBArea - interArea) == 0:
        return 0
    return interArea / float(boxAArea + boxBArea - interArea)


def _ocr_to_schema(raw_results, scale_x: float = 1.0, scale_y: float = 1.0, offset_x=0, offset_y=0) -> list:
    findings = []
    if not raw_results:
        return findings

    for idx, item in enumerate(raw_results):
        try:
            quad, text, conf = item
            xs = [p[0] / scale_x for p in quad]
            ys = [p[1] / scale_y for p in quad]
            x  = int(min(xs)) + offset_x
            y  = int(min(ys)) + offset_y
            w  = int(max(xs) - min(xs))
            h  = int(max(ys) - min(ys))

            if conf is None:
                confidence = None
                status     = "UNCERTAIN"
            elif conf >= 0.80:
                confidence = round(float(conf), 3)
                status     = "OBSERVED"
            elif conf >= 0.50:
                confidence = round(float(conf), 3)
                status     = "UNCERTAIN"
            else:
                confidence = round(float(conf), 3)
                status     = "UNCERTAIN"

            raw_txt = str(text).strip()
            findings.append({
                "id":         f"OCR_{idx:03d}",
                "text":       normalize_engineering_text(raw_txt),
                "raw_text":   raw_txt,
                "bbox":       {"x": x, "y": y, "width": w, "height": h},
                "confidence": confidence,
                "source":     "LOCAL_OCR",
                "status":     status,
            })
        except Exception:
            continue

    return findings


class LocalOCREngine:
    def __init__(self):
        self._ocr   = None
        self.status = OCR_NOT_INSTALLED
        self._init()

    def _init(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr   = RapidOCR()
            self.status = OCR_INSTALLED_AND_USABLE
        except ImportError:
            self.status = OCR_NOT_INSTALLED
        except Exception:
            self.status = OCR_RUNTIME_FAILURE

    @property
    def available(self) -> bool:
        return self.status == OCR_INSTALLED_AND_USABLE and self._ocr is not None

    def run(self, image: Image.Image, region: dict = None) -> dict:
        """
        Adaptive OCR. 
        region is {"x", "y", "width", "height"} in original image coords.
        """
        if not self.available:
            return {"success": False, "status": OCR_FAILED, "findings": [], "raw": None, "error": "Not available"}

        try:
            original = image.convert("RGB")
            orig_w, orig_h = original.size
            
            # Sub-region extraction
            offset_x, offset_y = 0, 0
            if region:
                x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                original = original.crop((x, y, x + w, y + h))
                orig_w, orig_h = original.size
                offset_x, offset_y = x, y

            cv_orig = _pil_to_cv2(original)
            
            # Base pass
            cv_enhanced = _enhance_for_ocr(cv_orig)
            enh_h, enh_w = cv_enhanced.shape[:2]
            scale_x = enh_w / orig_w
            scale_y = enh_h / orig_h

            all_raw = []
            raw, _ = self._ocr(cv_enhanced)
            if raw:
                all_raw.extend(raw)

            # High-res Small Text Fallback check (if few results or low confidence on small crops)
            if region and orig_w < 500 and orig_h < 500:
                if not raw or (raw and sum(r[2] for r in raw)/len(raw) < 0.7):
                    # 2x upscale + thresholding
                    up = cv2.resize(cv_orig, (orig_w*2, orig_h*2), interpolation=cv2.INTER_CUBIC)
                    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    raw_fallback, _ = self._ocr(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR))
                    if raw_fallback:
                        # scale down quad back to cv_enhanced scale to share schema logic
                        for item in raw_fallback:
                            quad, text, conf = item
                            shifted = [[p[0] * (scale_x/2), p[1] * (scale_y/2)] for p in quad]
                            all_raw.append([shifted, text, conf])

            # Large image Tiled pass
            elif max(orig_w, orig_h) > 1200:
                tile_h, tile_w = enh_h // 2, enh_w // 2
                overlaps = [
                    (0, 0), (0, tile_w), (tile_h, 0), (tile_h, tile_w),
                    (tile_h//2, tile_w//2)
                ]
                for ty, tx in overlaps:
                    tile = cv_enhanced[ty:ty+tile_h, tx:tx+tile_w]
                    tile_raw, _ = self._ocr(tile)
                    if tile_raw:
                        for item in tile_raw:
                            quad, text, conf = item
                            shifted_quad = [[p[0] + tx, p[1] + ty] for p in quad]
                            all_raw.append([shifted_quad, text, conf])

            findings = _ocr_to_schema(all_raw, scale_x, scale_y, offset_x, offset_y)
            
            # IoU Deduplication
            unique_findings = []
            for f in findings:
                fb = f["bbox"]
                boxA = [fb["x"], fb["y"], fb["x"]+fb["width"], fb["y"]+fb["height"]]
                
                is_duplicate = False
                for u in unique_findings:
                    ub = u["bbox"]
                    boxB = [ub["x"], ub["y"], ub["x"]+ub["width"], ub["y"]+ub["height"]]
                    iou = _compute_iou(boxA, boxB)
                    
                    if iou > 0.4:
                        # Spatial duplicate. Keep the one with higher confidence.
                        if f["confidence"] and u["confidence"] and f["confidence"] > u["confidence"]:
                            u["confidence"] = f["confidence"]
                            u["text"] = f["text"]
                            u["raw_text"] = f["raw_text"]
                        is_duplicate = True
                        break
                        
                if not is_duplicate:
                    unique_findings.append(f)
                    
            findings = unique_findings

            if not findings:
                status = "OCR_NO_TEXT"
            elif len(findings) > 0 and len(findings) < 5 and max(orig_w, orig_h) > 1500:
                status = "OCR_PARTIAL"
            else:
                status = "OCR_SUCCESS"

            return {
                "success":  True,
                "status":   status,
                "findings": findings,
                "raw":      all_raw,
                "error":    None,
            }

        except Exception as e:
            return {
                "success":  False,
                "status":   "OCR_FAILED",
                "findings": [],
                "raw":      None,
                "error":    str(e),
            }
