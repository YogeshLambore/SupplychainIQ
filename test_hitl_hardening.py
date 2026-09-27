"""
NEXORA Engineering Analyzer — HITL/Visual Failure Hardening Tests
Tests A through H as specified in the requirements.
Uses mocks so tests run independently of Ollama availability.
"""
import sys
import os
import json
import base64
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engineering_analyzer import (
    EngineeringAnalyzer,
    VISUAL_SUCCESS, VISUAL_EMPTY_IMAGE, VISUAL_PARSING_FAILURE,
    VISUAL_VISION_MODEL_FAILURE, VISUAL_INSUFFICIENT, VISUAL_PARTIAL,
)

# ------------------------------------------------------------------ #
#  Mock helpers                                                        #
# ------------------------------------------------------------------ #

def make_blank_image_b64():
    """Creates a near-zero-variance (blank white) PNG as base64."""
    from PIL import Image
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def make_real_image_b64():
    """Creates a varied (non-blank) PNG as base64."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 300), color=(30, 30, 60))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 120], fill=(200, 100, 50))
    draw.rectangle([220, 80, 330, 160], fill=(50, 180, 80))
    draw.line([155, 85, 218, 120], fill=(255, 255, 0), width=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class MockImgProc:
    """Configurable mock image processor."""
    def __init__(self, responses=None, always_fail=False, always_empty=False):
        self.responses    = responses or {}
        self.always_fail  = always_fail
        self.always_empty = always_empty

    def query_vision_model(self, base64_img, query, custom_system_prompt=None):
        if self.always_fail:
            return ""
        if self.always_empty:
            return "Vision model unavailable."
        if "overall" in query:
            return self.responses.get("global", "P&ID diagram with cooling loop.")
        if "components" in query:
            return self.responses.get("components", "Pump P-101, Valve V-102, Heat Exchanger HX-201.")
        if "text" in query or "labels" in query:
            return self.responses.get("labels", "Labels: P-101, V-102, HX-201, COOLING_IN.")
        if "lines" in query or "relationships" in query:
            return self.responses.get("relationships", "P-101 flows to V-102. V-102 flows to HX-201.")
        if "unclear" in query or "ambiguous" in query:
            return self.responses.get("ambiguity", "Label on HX-201 outlet is slightly blurry.")
        return "Some diagram content."


class MockLLM:
    """
    Returns realistic structured JSON for parser calls,
    and honest uncertainty messages for reasoning calls.
    Configurable for failure simulation.
    """
    def __init__(self, parsing_mode="good", reasoning_mode="normal", fail_json=False):
        self.parsing_mode  = parsing_mode
        self.reasoning_mode = reasoning_mode
        self.fail_json     = fail_json

    def generate(self, prompt="", context="", default_category="ENGINEERING", history=None):
        p = prompt.lower() + context.lower()

        # Parser call detection
        if "engineering data parser" in p or "output only valid json" in p:
            if self.fail_json:
                return "This is not JSON at all."
            if self.parsing_mode == "empty":
                return json.dumps({
                    "metadata": {"type": "Unknown", "title": "Unknown"},
                    "components": [], "labels": [], "relationships": [], "ambiguities": []
                })
            if self.parsing_mode == "good":
                return json.dumps({
                    "metadata": {"type": "P&ID", "title": "Cooling System"},
                    "components": [
                        {"id": "1", "type": "Pump",           "visible_tag": "P-101",  "status": "OBSERVED"},
                        {"id": "2", "type": "Valve",          "visible_tag": "V-102",  "status": "OBSERVED"},
                        {"id": "3", "type": "Heat Exchanger", "visible_tag": "HX-201", "status": "OBSERVED"},
                    ],
                    "labels": [
                        {"text": "P-101",       "associated_id": "1", "readability": "CLEAR"},
                        {"text": "COOLING_IN",  "associated_id": "",  "readability": "CLEAR"},
                    ],
                    "relationships": [
                        {"source": "P-101", "target": "V-102",  "relationship": "flows_to", "evidence": "visible_line", "status": "OBSERVED"},
                        {"source": "V-102", "target": "HX-201", "relationship": "flows_to", "evidence": "visible_line", "status": "OBSERVED"},
                    ],
                    "ambiguities": ["HX-201 outlet label is slightly blurry."]
                })

        # Relevance call
        if "relevant" in p and "classify" in p:
            return "RELEVANT: Document matches diagram components."

        # Verification call
        if "engineering verification" in p or "verify" in p:
            return json.dumps({
                "claims": [
                    {"claim": "P-101 is connected to V-102.", "status": "SUPPORTED",
                     "reason": "Visual findings show flows_to relationship."},
                ],
                "has_contradiction": False,
                "overall_status":    "PASS",
                "confidence":        "HIGH"
            })

        # Reasoning — failure-aware
        if "cannot confirm" in p or "system/model failure" in p or "visual analysis state" in p:
            return (
                "I cannot confirm any diagram content because the visual analysis "
                "did not produce reliable evidence. "
                "The system encountered a failure state and no structured findings were extracted."
            )

        # Normal reasoning
        return (
            "Based on the visual findings: Pump P-101 is connected to Valve V-102, "
            "which feeds Heat Exchanger HX-201. "
            "This is directly observed from the diagram topology."
        )

    def check_health(self):
        return True

    @property
    def is_loaded(self):
        return True


# ------------------------------------------------------------------ #
#  Test runner                                                         #
# ------------------------------------------------------------------ #
RESULTS = []

def run_test(name, fn):
    print(f"\n{'='*60}")
    print(f"TEST {name}")
    print('='*60)
    try:
        result = fn()
        status = result.get("status", "FAIL")
        notes  = result.get("notes", "")
        print(f"  STATUS: {status}")
        if notes:
            print(f"  NOTES:  {notes}")
        RESULTS.append((name, status, notes))
    except Exception as e:
        print(f"  STATUS: FAIL — Exception: {e}")
        import traceback; traceback.print_exc()
        RESULTS.append((name, "FAIL", str(e)))


# ------------------------------------------------------------------ #
#  TEST A — Valid non-empty diagram                                    #
# ------------------------------------------------------------------ #
def test_a():
    llm      = MockLLM(parsing_mode="good")
    img_proc = MockImgProc()
    analyzer = EngineeringAnalyzer(llm, img_proc)

    b64 = make_real_image_b64()
    report = analyzer.generate_final_report("What components are visible?", b64, "", "")

    state = report["visual_state"]
    n_comp = len(report.get("raw_passes", {}))  # passes fired

    checks = [
        state in {VISUAL_SUCCESS, VISUAL_PARTIAL},
        report["confidence"] != "LOW",
        report["verification_status"] in {"PASS", "REVIEW"},
        "EMPTY" not in state,
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={state}, confidence={report['confidence']}"}


# ------------------------------------------------------------------ #
#  TEST B — Actually blank image                                       #
# ------------------------------------------------------------------ #
def test_b():
    llm      = MockLLM()
    img_proc = MockImgProc()
    analyzer = EngineeringAnalyzer(llm, img_proc)

    b64 = make_blank_image_b64()
    report = analyzer.generate_final_report("Describe this diagram.", b64, "", "")

    state = report["visual_state"]
    checks = [
        state == VISUAL_EMPTY_IMAGE,
        report["confidence"] == "LOW",
        report["hitl_required"],
        # must NOT claim diagram content
        "empty" in report["markdown"].lower() or "blank" in report["markdown"].lower(),
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={state}"}


# ------------------------------------------------------------------ #
#  TEST C — Vision model failure                                       #
# ------------------------------------------------------------------ #
def test_c():
    llm      = MockLLM()
    img_proc = MockImgProc(always_fail=True)   # all passes return ""
    analyzer = EngineeringAnalyzer(llm, img_proc)

    b64 = make_real_image_b64()
    report = analyzer.generate_final_report("What is in this diagram?", b64, "", "")

    state = report["visual_state"]
    checks = [
        state == VISUAL_VISION_MODEL_FAILURE,
        report["confidence"] == "LOW",
        report["hitl_required"],
        "cannot confirm" in report["markdown"].lower()
            or "did not produce" in report["markdown"].lower(),
        # must NOT say diagram is empty
        "diagram is empty" not in report["markdown"].lower(),
        "image is empty"   not in report["markdown"].lower(),
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={state}, hitl={report['hitl_required']}"}


# ------------------------------------------------------------------ #
#  TEST D — Valid image + JSON parser failure                          #
# ------------------------------------------------------------------ #
def test_d():
    llm      = MockLLM(fail_json=True)    # LLM returns non-JSON for parser
    img_proc = MockImgProc()              # vision passes succeed
    analyzer = EngineeringAnalyzer(llm, img_proc)

    b64 = make_real_image_b64()
    report = analyzer.generate_final_report("Identify components.", b64, "", "")

    state = report["visual_state"]
    checks = [
        state == VISUAL_PARSING_FAILURE,
        report["confidence"] == "LOW",
        report["hitl_required"],
        "diagram is empty" not in report["markdown"].lower(),
        "image is empty"   not in report["markdown"].lower(),
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={state}"}


# ------------------------------------------------------------------ #
#  TEST E — Ambiguous / partial extraction                             #
# ------------------------------------------------------------------ #
def test_e():
    """Only some vision passes succeed → VISUAL_PARTIAL."""
    llm = MockLLM(parsing_mode="good")

    class PartialImgProc:
        def query_vision_model(self, b64, query, custom_system_prompt=None):
            # Fail passes 4 and 5
            if "relationships" in query or "unclear" in query or "ambiguous" in query:
                return ""
            return "Some content observed."

    analyzer = EngineeringAnalyzer(llm, PartialImgProc())
    b64 = make_real_image_b64()
    report = analyzer.generate_final_report("Explain the diagram.", b64, "", "")

    state = report["visual_state"]
    checks = [
        state in {VISUAL_PARTIAL, VISUAL_INSUFFICIENT, VISUAL_SUCCESS},
        "diagram is empty" not in report["markdown"].lower(),
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={state}"}


# ------------------------------------------------------------------ #
#  TEST F — Second component query with failed extraction              #
# ------------------------------------------------------------------ #
def test_f():
    llm      = MockLLM()
    img_proc = MockImgProc(always_fail=True)
    analyzer = EngineeringAnalyzer(llm, img_proc)

    b64 = make_real_image_b64()
    report = analyzer.generate_final_report("Identify the second major component.", b64, "", "")

    md = report["markdown"].lower()
    checks = [
        report["visual_state"] == VISUAL_VISION_MODEL_FAILURE,
        # Must NOT say "there is no second component"
        "there is no second" not in md,
        # Must express inability to confirm
        "cannot confirm" in md or "did not produce" in md or "not produce" in md,
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={report['visual_state']}"}


# ------------------------------------------------------------------ #
#  TEST G — Claim verification correctness                             #
# ------------------------------------------------------------------ #
def test_g():
    llm      = MockLLM()
    img_proc = MockImgProc()
    analyzer = EngineeringAnalyzer(llm, img_proc)

    # Test 1: Verifying "diagram is empty" with PARSING_FAILURE state
    # should return NOT_VERIFIABLE, never SUPPORTED
    v1 = analyzer.verify_answer(
        query="Is the diagram empty?",
        structured_findings={
            "metadata": {"type": "Unknown", "title": "Unknown"},
            "components": [], "labels": [], "relationships": [], "ambiguities": []
        },
        reference_evidence="",
        answer="The diagram appears to be empty based on the analysis.",
        visual_state=VISUAL_PARSING_FAILURE,
    )

    # With PARSING_FAILURE, must be NOT_VERIFIABLE, never SUPPORTED for "empty" claim
    v1_status = v1.get("overall_status", "")
    v1_verifiable = v1.get("verifiable", True)
    v1_claims = v1.get("claims", [])
    has_supported_empty = any(
        "empty" in c.get("claim", "").lower() and c.get("status") == "SUPPORTED"
        for c in v1_claims
    )

    checks = [
        v1_status == "FAIL",          # parsing failure should be overall FAIL
        not v1_verifiable,            # should be marked not verifiable
        not has_supported_empty,      # must not SUPPORT the "empty" claim
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"overall_status={v1_status}, verifiable={v1_verifiable}, "
                     f"has_supported_empty={has_supported_empty}"}


# ------------------------------------------------------------------ #
#  TEST H — Regression (components/integration)                       #
# ------------------------------------------------------------------ #
def test_h():
    llm      = MockLLM(parsing_mode="good")
    img_proc = MockImgProc()
    analyzer = EngineeringAnalyzer(llm, img_proc)

    b64 = make_real_image_b64()

    # Standard analysis
    report = analyzer.generate_final_report(
        "What is connected to P-101?",
        b64,
        "[Page 1] Pump P-101 feeds into control valve V-102.",
        ""
    )

    checks = [
        "markdown" in report,
        "visual_state" in report,
        "confidence" in report,
        "hitl_required" in report,
        "pass_statuses" in report,
        isinstance(report["hitl_required"], bool),
        report["markdown"].strip() != "",
    ]
    ok = all(checks)
    return {"status": "PASS" if ok else "FAIL",
            "notes": f"visual_state={report['visual_state']}, confidence={report['confidence']}"}


# ------------------------------------------------------------------ #
#  Run all tests                                                       #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    run_test("A — Valid Non-Empty Diagram",         test_a)
    run_test("B — Actually Blank Image",            test_b)
    run_test("C — Vision Model Failure",            test_c)
    run_test("D — Valid Image + Parser Failure",    test_d)
    run_test("E — Partial Extraction (Ambiguous)",  test_e)
    run_test("F — Second Component / No Evidence",  test_f)
    run_test("G — Claim Verification Correctness",  test_g)
    run_test("H — Regression Integration",          test_h)

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    total = len(RESULTS)
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    for name, status, notes in RESULTS:
        icon = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {icon} {name}  {notes}")
    print(f"\n  {passed}/{total} tests PASSED")
    print("="*60)
