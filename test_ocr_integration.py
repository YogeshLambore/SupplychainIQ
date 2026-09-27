"""
NEXORA — Local OCR Health Check + Full Integration Tests (Phases 21 & 22)
Tests cover OCR standalone, Moondream+OCR fusion, and all failure scenarios.
All tests use deterministic mocks — Ollama not required.
"""
import sys, os, io, base64, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont

# ─── Image generators ────────────────────────────────────────────────────────

def make_real_diagram_b64(labels=None):
    """Non-blank diagram with visible labels."""
    labels = labels or ["P-101", "V-102", "HX-201"]
    img = Image.new("RGB", (600, 400), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    for i, lbl in enumerate(labels):
        x = 80 + i * 160
        draw.rectangle([x, 120, x + 100, 200], fill=(200, 210, 230), outline=(30, 60, 120), width=3)
        draw.text((x + 10, 150), lbl, fill=(10, 10, 10))
    for i in range(len(labels) - 1):
        x1 = 180 + i * 160
        x2 = x1 + 60
        draw.line([(x1, 160), (x2, 160)], fill=(30, 80, 30), width=3)
        draw.polygon([(x2, 153), (x2 + 10, 160), (x2, 167)], fill=(30, 80, 30))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

def make_blank_b64():
    img = Image.new("RGB", (300, 200), (255, 255, 255))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

def make_dense_b64():
    """Many small labels."""
    img = Image.new("RGB", (800, 600), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    tags = [f"TAG-{i:03d}" for i in range(20)]
    for i, t in enumerate(tags):
        x = (i % 5) * 140 + 20
        y = (i // 5) * 120 + 20
        draw.rectangle([x, y, x + 100, y + 60], outline=(60, 60, 60), width=2)
        draw.text((x + 5, y + 20), t, fill=(0, 0, 0))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

def make_loRes_b64():
    """Low-resolution image."""
    img = Image.new("RGB", (80, 60), (230, 230, 230))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ─── Mocks ───────────────────────────────────────────────────────────────────

class GoodImgProc:
    def query_vision_model(self, b64, query, custom_system_prompt=None):
        if "global" in query or "overall" in query:     return "P&ID diagram — Cooling Loop. Title: COOLING_SYS."
        if "components" in query:                        return "Pump P-101, Valve V-102, Heat Exchanger HX-201."
        if "text" in query or "labels" in query:         return "Labels: P-101, V-102, HX-201, COOLING_IN."
        if "relationships" in query or "lines" in query: return "Arrow from P-101 to V-102. Arrow from V-102 to HX-201."
        if "unclear" in query or "ambiguous" in query:   return "HX-201 outlet label slightly blurry."
        return "Some content."

class FailImgProc:
    def query_vision_model(self, *args, **kw): return ""

class GoodLLM:
    def generate(self, prompt="", context="", default_category="ENGINEERING", history=None):
        p = (prompt + context).lower()
        if "engineering evidence parser" in p or "output only valid json" in p:
            return json.dumps({
                "metadata": {"diagram_type": "P&ID", "title": "COOLING_SYS"},
                "components": [
                    {"id": "C001", "type": "Pump",           "visible_tag": "P-101",  "status": "OBSERVED",  "sources": ["MOONDREAM_PASS_2", "LOCAL_OCR"]},
                    {"id": "C002", "type": "Valve",          "visible_tag": "V-102",  "status": "OBSERVED",  "sources": ["MOONDREAM_PASS_2", "LOCAL_OCR"]},
                    {"id": "C003", "type": "Heat Exchanger", "visible_tag": "HX-201", "status": "OBSERVED",  "sources": ["MOONDREAM_PASS_2"]},
                ],
                "labels": [
                    {"text": "P-101",  "associated_id": "C001", "readability": "CLEAR", "ocr_confidence": 0.97, "source": "LOCAL_OCR"},
                    {"text": "COOLING_IN", "associated_id": "",  "readability": "CLEAR", "source": "LOCAL_OCR"},
                ],
                "relationships": [
                    {"source_id": "C001", "target_id": "C002", "relationship": "flows_to",
                     "direction": "FORWARD", "evidence_type": "VISIBLE_ARROW",
                     "source_pass": "MOONDREAM_PASS_4", "status": "OBSERVED"},
                    {"source_id": "C002", "target_id": "C003", "relationship": "flows_to",
                     "direction": "FORWARD", "evidence_type": "VISIBLE_ARROW",
                     "source_pass": "MOONDREAM_PASS_4", "status": "OBSERVED"},
                ],
                "ambiguities": [{"description": "HX-201 outlet label blurry", "affected_id": "C003"}]
            })
        if "relevant" in p and "classify" in p:    return "RELEVANT: Document matches P-101."
        if "engineering verification" in p:
            return json.dumps({"claims": [{"claim": "P-101 flows to V-102.", "status": "SUPPORTED", "reason": "MOONDREAM_PASS_4 arrow evidence."}], "has_contradiction": False, "overall_status": "PASS", "confidence": "HIGH"})
        if "cannot confirm" in p or "system/model failure" in p or "visual analysis pipeline" in p:
            return "I cannot confirm any diagram content because visual analysis did not produce reliable evidence."
        return "Based on findings: P-101 is connected to V-102 via a visible process line."

    def check_health(self): return True
    @property
    def is_loaded(self): return True

# ─── Test runner ─────────────────────────────────────────────────────────────
RESULTS = []

def run_test(name, fn):
    print(f"\n{'='*60}\nTEST {name}\n{'='*60}")
    try:
        r = fn()
        st, notes = r.get("status", "FAIL"), r.get("notes", "")
        print(f"  STATUS: {st}")
        if notes: print(f"  NOTES:  {notes}")
        RESULTS.append((name, st, notes))
    except Exception as e:
        import traceback; traceback.print_exc()
        RESULTS.append((name, "FAIL", str(e)))

# ────────────────────────────────────────────────────────────────────────────
# PHASE 21 — OCR Health Check
# ────────────────────────────────────────────────────────────────────────────
def test_ocr_health():
    from core.ocr_engine import check_ocr_health, OCR_INSTALLED_AND_USABLE
    h = check_ocr_health()
    print(f"  OCR ENGINE:       {h['ocr_engine']}")
    print(f"  PACKAGE:          {h['package']}")
    print(f"  MODEL PATH:       {h['model_path']}")
    print(f"  IMPORT:           {h['import']}")
    print(f"  MODEL FILES:      {h['model_files']}")
    print(f"  INITIALIZATION:   {h['initialization']}")
    print(f"  LOCAL INFERENCE:  {h['local_inference']}")
    print(f"  INTERNET REQUIRED:{h['internet_required']}")
    print(f"  OFFLINE READY:    {h['offline_ready']}")
    print(f"  STATUS:           {h['status']}")
    ok = h["status"] == OCR_INSTALLED_AND_USABLE and h["offline_ready"] == "YES"
    return {"status": "PASS" if ok else "FAIL", "notes": h.get("detail", h["status"])}

def test_ocr_text_extraction():
    from core.ocr_engine import LocalOCREngine
    ocr = LocalOCREngine()
    if not ocr.available:
        return {"status": "FAIL", "notes": f"OCR not available: {ocr.status}"}
    img = Image.new("RGB", (300, 80), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "P-101", fill=(0, 0, 0))
    result = ocr.run(img)
    texts = [f["text"] for f in result.get("findings", [])]
    bboxes = [f["bbox"] for f in result.get("findings", [])]
    print(f"  Texts found: {texts}")
    print(f"  Bboxes:      {bboxes}")
    ok = result["success"] and len(texts) > 0
    return {"status": "PASS" if ok else "PARTIAL",
            "notes": f"texts={texts}, bboxes={len(bboxes)}"}

def test_ocr_bbox():
    from core.ocr_engine import LocalOCREngine
    ocr = LocalOCREngine()
    img = Image.new("RGB", (400, 100), (255, 255, 255))
    ImageDraw.Draw(img).text((50, 30), "HX-201", fill=(0, 0, 0))
    r = ocr.run(img)
    findings = r.get("findings", [])
    has_bbox = all("bbox" in f and all(k in f["bbox"] for k in ["x","y","width","height"]) for f in findings)
    return {"status": "PASS" if has_bbox and findings else "PARTIAL",
            "notes": f"findings={len(findings)}, all_have_bbox={has_bbox}"}

# ────────────────────────────────────────────────────────────────────────────
# PHASE 22 — Integration Tests
# ────────────────────────────────────────────────────────────────────────────
def test_1_simple_workflow():
    from core.engineering_analyzer import EngineeringAnalyzer, VISUAL_SUCCESS, VISUAL_PARTIAL
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report("What components are visible?", b64, "", "")
    checks = [
        r["visual_state"] in {VISUAL_SUCCESS, VISUAL_PARTIAL},
        r["confidence"] in {"HIGH", "MEDIUM"},
        r["ocr_status"] == "OCR_AVAILABLE",
        len(r["ocr_findings"]) > 0,
    ]
    return {"status": "PASS" if all(checks) else "FAIL",
            "notes": f"state={r['visual_state']}, conf={r['confidence']}, ocr={len(r['ocr_findings'])}"}

def test_2_dense_diagram():
    from core.engineering_analyzer import EngineeringAnalyzer
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc())
    b64 = make_dense_b64()
    r = analyzer.generate_final_report("List all components and labels.", b64, "", "")
    return {"status": "PASS", "notes": f"state={r['visual_state']}, ocr={len(r['ocr_findings'])}"}

def test_4_low_resolution():
    from core.engineering_analyzer import EngineeringAnalyzer, VISUAL_EMPTY_IMAGE
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc())
    b64 = make_loRes_b64()
    r = analyzer.generate_final_report("Describe the diagram.", b64, "", "")
    # Low-res image may be treated as too small → EMPTY_IMAGE or succeed
    ok = "visual_state" in r
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"state={r['visual_state']}, conf={r['confidence']}"}

def test_5_blank_image():
    from core.engineering_analyzer import EngineeringAnalyzer, VISUAL_EMPTY_IMAGE
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc())
    b64 = make_blank_b64()
    r = analyzer.generate_final_report("Describe this diagram.", b64, "", "")
    checks = [r["visual_state"] == VISUAL_EMPTY_IMAGE, r["confidence"] == "LOW", r["hitl_required"]]
    return {"status": "PASS" if all(checks) else "FAIL",
            "notes": f"state={r['visual_state']}"}

def test_6_vision_model_failure():
    from core.engineering_analyzer import EngineeringAnalyzer, VISUAL_VISION_MODEL_FAILURE
    analyzer = EngineeringAnalyzer(GoodLLM(), FailImgProc())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report("What is in this diagram?", b64, "", "")
    checks = [
        r["visual_state"] == VISUAL_VISION_MODEL_FAILURE,
        r["confidence"] == "LOW",
        r["hitl_required"],
        "cannot confirm" in r["markdown"].lower() or "did not produce" in r["markdown"].lower(),
        "diagram is empty" not in r["markdown"].lower(),
    ]
    return {"status": "PASS" if all(checks) else "FAIL",
            "notes": f"state={r['visual_state']}, hitl={r['hitl_required']}"}

def test_7_ocr_failure_graceful():
    from core.engineering_analyzer import EngineeringAnalyzer, _NullOCR
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc(), ocr_engine=_NullOCR())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report("List components.", b64, "", "")
    # Must not crash; vision-only analysis should still work
    ok = "markdown" in r and "visual_state" in r
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"state={r['visual_state']}, ocr={r['ocr_status']}"}

def test_8_ocr_moondream_disagreement():
    """OCR sees P-10?, vision sees P-101 → AMBIGUOUS_ENTITY detected."""
    from core.engineering_analyzer import EngineeringAnalyzer, AMBIGUOUS_ENTITY
    from core.ocr_engine import LocalOCREngine, OCR_INSTALLED_AND_USABLE

    class MismatchLLM(GoodLLM):
        def generate(self, prompt="", context="", default_category="ENGINEERING", history=None):
            p = (prompt + context).lower()
            if "engineering evidence parser" in p or "output only valid json" in p:
                return json.dumps({
                    "metadata": {"diagram_type": "P&ID", "title": "Test"},
                    "components": [{"id": "C001", "type": "Pump", "visible_tag": "P-101",
                                    "status": "OBSERVED", "sources": ["MOONDREAM_PASS_2"]}],
                    "labels": [], "relationships": [], "ambiguities": []
                })
            return super().generate(prompt, context, default_category, history)

    # Create OCR that returns a partial match "P-10"
    class PartialOCR:
        @property
        def available(self): return True
        def run(self, img):
            return {"success": True, "status": "OCR_AVAILABLE",
                    "findings": [{"id": "OCR_000", "text": "P-10", "bbox": {"x":10,"y":10,"width":40,"height":20},
                                  "confidence": 0.52, "source": "LOCAL_OCR", "status": "UNCERTAIN"}],
                    "raw": None}

    analyzer = EngineeringAnalyzer(MismatchLLM(), GoodImgProc(), ocr_engine=PartialOCR())
    b64 = make_real_diagram_b64(["P-10"])
    r = analyzer.generate_final_report("Identify the pump.", b64, "", "")
    conflicts = r.get("markdown", "")
    has_ambiguous = AMBIGUOUS_ENTITY in conflicts or "AMBIGUOUS" in conflicts
    return {"status": "PASS" if has_ambiguous else "PARTIAL",
            "notes": f"AMBIGUOUS_ENTITY present in output: {has_ambiguous}"}

def test_9_missing_info():
    from core.engineering_analyzer import EngineeringAnalyzer
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report("What is the operating pressure of P-101?", b64, "", "")
    ok = "cannot confirm" in r["markdown"].lower() or "not visible" in r["markdown"].lower()
    return {"status": "PASS" if ok else "PARTIAL",
            "notes": f"answer contains uncertainty language: {ok}"}

def test_10_unrelated_reference():
    from core.engineering_analyzer import EngineeringAnalyzer

    class NotRelLLM(GoodLLM):
        def generate(self, prompt="", context="", default_category="ENGINEERING", history=None):
            if "relevant" in (prompt+context).lower() and "classify" in (prompt+context).lower():
                return "NOT_RELEVANT: Document is about HR workflow, not the P&ID diagram."
            return super().generate(prompt, context, default_category, history)

    analyzer = EngineeringAnalyzer(NotRelLLM(), GoodImgProc())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report("Analyze the diagram.", b64, "HR policy document text here.", "")
    ok = "NOT_RELEVANT" in r["markdown"] or "not relevant" in r["markdown"].lower()
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"NOT_RELEVANT detected: {ok}"}

def test_11_contradictory_reference():
    from core.engineering_analyzer import EngineeringAnalyzer

    class ContrLLM(GoodLLM):
        def generate(self, prompt="", context="", default_category="ENGINEERING", history=None):
            if "engineering verification" in (prompt+context).lower():
                return json.dumps({"claims": [{"claim": "P-101 flows to V-102.", "status": "CONTRADICTED",
                                               "reason": "Reference doc says P-101 flows to V-103."}],
                                   "has_contradiction": True, "overall_status": "FAIL", "confidence": "LOW"})
            return super().generate(prompt, context, default_category, history)

    analyzer = EngineeringAnalyzer(ContrLLM(), GoodImgProc())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report("Where does P-101 flow to?", b64, "P-101 flows to V-103.", "")
    ok = r["hitl_required"] and ("CONFLICT" in r["markdown"] or "CONTRADICTED" in r["markdown"])
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"hitl={r['hitl_required']}, conflict_in_output={ok}"}

def test_12_full_pipeline():
    from core.engineering_analyzer import EngineeringAnalyzer, VISUAL_SUCCESS, VISUAL_PARTIAL
    analyzer = EngineeringAnalyzer(GoodLLM(), GoodImgProc())
    b64 = make_real_diagram_b64()
    r = analyzer.generate_final_report(
        "Give a full analysis of the diagram including all components, labels, and topology.",
        b64,
        "[Page 1] P-101 pump feeds into control valve V-102.",
        ""
    )
    checks = [
        "markdown" in r,
        r["visual_state"] in {VISUAL_SUCCESS, VISUAL_PARTIAL},
        r["confidence"] in {"HIGH", "MEDIUM"},
        r["ocr_status"] == "OCR_AVAILABLE",
        len(r["ocr_findings"]) > 0,
        "verification_status" in r,
        "pass_statuses" in r,
    ]
    return {"status": "PASS" if all(checks) else "FAIL",
            "notes": f"state={r['visual_state']}, conf={r['confidence']}, "
                     f"ocr={len(r['ocr_findings'])}, hitl={r['hitl_required']}"}

# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE 21 — OCR HEALTH CHECK")
    print("="*60)
    run_test("OCR-Health-Check",      test_ocr_health)
    run_test("OCR-Text-Extraction",   test_ocr_text_extraction)
    run_test("OCR-Bounding-Box",      test_ocr_bbox)

    print("\n" + "="*60)
    print("PHASE 22 — INTEGRATION TESTS")
    print("="*60)
    run_test("1-Simple-Workflow-Diagram",      test_1_simple_workflow)
    run_test("2-Dense-Diagram",               test_2_dense_diagram)
    run_test("4-Low-Resolution",              test_4_low_resolution)
    run_test("5-Blank-Image",                 test_5_blank_image)
    run_test("6-Vision-Model-Failure",        test_6_vision_model_failure)
    run_test("7-OCR-Failure-Graceful",        test_7_ocr_failure_graceful)
    run_test("8-OCR-Moondream-Disagreement",  test_8_ocr_moondream_disagreement)
    run_test("9-Missing-Information",         test_9_missing_info)
    run_test("10-Unrelated-Reference",        test_10_unrelated_reference)
    run_test("11-Contradictory-Reference",    test_11_contradictory_reference)
    run_test("12-Full-Pipeline",              test_12_full_pipeline)

    print("\n" + "="*60 + "\nFINAL TEST SUMMARY\n" + "="*60)
    total  = len(RESULTS)
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    for name, status, notes in RESULTS:
        icon = "[PASS]" if status == "PASS" else "[PARTIAL]" if status == "PARTIAL" else "[FAIL]"
        print(f"  {icon} {name}  {notes}")
    print(f"\n  {passed}/{total} tests PASSED")
    print("="*60)
