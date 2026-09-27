import cv2
import numpy as np
import json
import re
import base64
import io
from typing import Optional

# ── Visual analysis states ──────────────────────────────────────────────────
VISUAL_SUCCESS              = "VISUAL_SUCCESS"
VISUAL_EMPTY_IMAGE          = "EMPTY_IMAGE"
VISUAL_PARSING_FAILURE      = "PARSING_FAILURE"
VISUAL_VISION_MODEL_FAILURE = "VISION_MODEL_FAILURE"
VISUAL_INSUFFICIENT         = "INSUFFICIENT_VISUAL_EVIDENCE"
VISUAL_AMBIGUOUS            = "AMBIGUOUS_VISUAL_EVIDENCE"
VISUAL_PARTIAL              = "VISUAL_ANALYSIS_PARTIAL"

# ── Per-pass status ─────────────────────────────────────────────────────────
PASS_OK   = "SUCCESS"
PASS_FAIL = "FAIL"
PASS_PART = "PARTIAL"

# ── OCR states ───────────────────────────────────────────────────────────────
OCR_OK          = "OCR_AVAILABLE"
OCR_UNAVAILABLE = "OCR_UNAVAILABLE"
OCR_FAILED      = "OCR_FAILED"

# ── Reconciliation states ────────────────────────────────────────────────────
SAME_ENTITY      = "SAME_ENTITY"
DIFFERENT_ENTITY = "DIFFERENT_ENTITY"
AMBIGUOUS_ENTITY = "AMBIGUOUS_ENTITY"


class EngineeringAnalyzer:
    def __init__(self, llm_manager, img_processor=None, ocr_engine=None):
        self.llm      = llm_manager
        self.img_proc = img_processor
        # Accept injected OCR engine or lazy-load it
        self._ocr_engine = ocr_engine

    @property
    def ocr(self):
        if self._ocr_engine is None:
            try:
                from core.ocr_engine import LocalOCREngine
                self._ocr_engine = LocalOCREngine()
            except Exception:
                self._ocr_engine = _NullOCR()
        return self._ocr_engine

    # ────────────────────────────────────────────────────────────────────── #
    #  IMAGE HEALTH CHECK                                                     #
    # ────────────────────────────────────────────────────────────────────── #
    def _profile_image(self, pil_img) -> dict:
        """Determines image complexity, edge density, and whether to use regional processing."""
        w, h = pil_img.size
        megapixels = (w * h) / 1000000.0
        aspect_ratio = w / float(h) if h > 0 else 1
        
        cv_img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        
        # Edge density
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / float(w * h)
        
        # Complexity classification
        if megapixels < 1.0 and edge_density < 0.05:
            complexity = "SIMPLE"
        elif megapixels > 4.0 or edge_density > 0.15:
            complexity = "VERY_DENSE"
        elif megapixels > 2.0 or edge_density > 0.08:
            complexity = "DENSE"
        else:
            complexity = "MODERATE"
            
        return {
            "width": w, "height": h, "megapixels": megapixels,
            "aspect_ratio": aspect_ratio, "edge_density": edge_density,
            "complexity": complexity
        }

    def _extract_regions(self, profile) -> list:
        """Generates adaptive bounding regions for DENSE images."""
        regions = []
        w, h = profile["width"], profile["height"]
        
        # If simple or moderate, just use one region
        if profile["complexity"] in ["SIMPLE", "MODERATE"] or max(w, h) < 1500:
            return [{"id": "R0", "x": 0, "y": 0, "width": w, "height": h}]
            
        # VERY_DENSE / DENSE -> Adaptive overlap grid (2x2 or 3x3)
        cols = 3 if w > 3000 else 2
        rows = 3 if h > 3000 else 2
        
        tile_w = w // cols
        tile_h = h // rows
        overlap_x = int(tile_w * 0.2)
        overlap_y = int(tile_h * 0.2)
        
        rid = 1
        for r in range(rows):
            for c in range(cols):
                rx = max(0, c * tile_w - (overlap_x if c > 0 else 0))
                ry = max(0, r * tile_h - (overlap_y if r > 0 else 0))
                rw = min(w - rx, tile_w + (overlap_x if c < cols-1 else 0))
                rh = min(h - ry, tile_h + (overlap_y if r < rows-1 else 0))
                
                regions.append({
                    "id": f"R{rid}",
                    "x": rx, "y": ry, "width": rw, "height": rh
                })
                rid += 1
                
        return regions

    def _check_image_health(self, base64_img: str) -> dict:
        if not base64_img:
            return {"healthy": False, "reason": "No base64 image data supplied.", "pil": None}
        try:
            from PIL import Image
            img_bytes = base64.b64decode(base64_img)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            w, h = img.size
            if w < 16 or h < 16:
                return {"healthy": False, "reason": f"Image too small ({w}x{h}).", "pil": None}
            pixels = list(img.getdata())
            r_vals = [p[0] for p in pixels]
            mean_r = sum(r_vals) / len(r_vals)
            variance = sum((v - mean_r) ** 2 for v in r_vals) / len(r_vals)
            if variance < 5.0:
                return {"healthy": False, "reason": f"Image appears blank (variance={variance:.2f}).", "pil": None}
            return {"healthy": True, "reason": f"{w}x{h} variance={variance:.1f}", "pil": img}
        except Exception as e:
            return {"healthy": False, "reason": f"Decode error: {e}", "pil": None}

    # ────────────────────────────────────────────────────────────────────── #
    #  FIVE-PASS MOONDREAM WITH PER-PASS STATUS                              #
    # ────────────────────────────────────────────────────────────────────── #
    def _five_pass_vision(self, base64_img: str) -> dict:
        """Returns raw pass text and per-pass status dict."""
        PASSES = {
            "pass_1_global":        "Describe the overall diagram type, title, major regions, and broad workflow. Be specific.",
            "pass_2_components":    "List every visible component, equipment box, node, actor, symbol, and process step. Include its visible label or name exactly as written.",
            "pass_3_labels":        "Read all visible text, tags, labels, annotations, and numbers. If text is partially unreadable, write exactly what you can read and mark the rest as unclear.",
            "pass_4_relationships": "Describe every line, arrow, pipe, and connector you see. For each, state the source component and target component and the direction of flow.",
            "pass_5_ambiguity":     "List every object, label, or connection that is unclear, partially hidden, overlapping, or that you cannot confidently identify.",
        }
        raw_passes    = {}
        pass_statuses = {}
        successful    = 0

        for key, prompt in PASSES.items():
            resp = self.img_proc.query_vision_model(base64_img, prompt) if self.img_proc else ""
            if not resp or resp.strip() == "" or "Vision model unavailable" in resp:
                raw_passes[key]    = ""
                pass_statuses[key] = PASS_FAIL
            else:
                raw_passes[key]    = resp
                pass_statuses[key] = PASS_OK
                successful        += 1

        return {"raw": raw_passes, "statuses": pass_statuses, "successful": successful, "total": len(PASSES)}

    # ────────────────────────────────────────────────────────────────────── #
    #  LOCAL OCR EXTRACTION                                                   #
    # ────────────────────────────────────────────────────────────────────── #
    def _run_ocr(self, pil_img) -> dict:
        """Runs local OCR. Returns status + findings. Never crashes the pipeline."""
        try:
            result = self.ocr.run(pil_img)
            if result["success"]:
                return {"status": OCR_OK, "findings": result["findings"], "raw": result["raw"]}
            return {"status": OCR_FAILED, "findings": [], "raw": None,
                    "error": result.get("error", "")}
        except Exception as e:
            return {"status": OCR_FAILED, "findings": [], "raw": None, "error": str(e)}

    # ────────────────────────────────────────────────────────────────────── #
    #  STRUCTURED PARSER (Moondream text → JSON)                              #
    # ────────────────────────────────────────────────────────────────────── #
    def _parse_structured_findings(self, combined_text: str, ocr_findings: list):
        """
        Parses combined Moondream text into structured JSON.
        OCR findings are passed in to allow the LLM to cross-reference.
        Returns (structured_dict, success: bool, reason: str)
        """
        ocr_summary = json.dumps(
            [{"text": f["text"], "conf": f["confidence"], "status": f["status"]}
             for f in ocr_findings], ensure_ascii=False
        ) if ocr_findings else "[]"

        prompt = (
            "You are an engineering evidence parser. Extract observations strictly from the "
            "vision text and OCR data below. Never invent facts.\
\
"
            "Schema:\
"
            "{\
"
            '  "metadata": {"diagram_type": "...", "title": "..."},\
'
            '  "components": [\
'
            '    {"id": "C001", "type": "...", "visible_tag": "...", '
            '"status": "<OBSERVED|INFERRED|UNKNOWN>", '
            '"sources": ["MOONDREAM_PASS_2", "LOCAL_OCR"]}\
'
            "  ],\
"
            '  "labels": [\
'
            '    {"text": "...", "associated_id": "...", '
            '"readability": "<CLEAR|UNCLEAR>", '
            '"ocr_confidence": null, "source": "..."}\
'
            "  ],\
"
            '  "relationships": [\
'
            '    {"source_id": "C001", "target_id": "C002", '
            '"relationship": "connected_to", '
            '"direction": "<FORWARD|REVERSE|BIDIRECTIONAL|UNKNOWN>", '
            '"evidence_type": "<VISIBLE_ARROW|VISIBLE_LINE|INFERRED>", '
            '"source_pass": "MOONDREAM_PASS_4", '
            '"status": "<OBSERVED|INFERRED>"}\
'
            "  ],\
"
            '  "ambiguities": [\
'
            '    {"description": "...", "affected_id": "..."}\
'
            "  ]\
"
            "}\
\
"
            "IMPORTANT RULES:\
"
            "- visible_tag must be the EXACT text seen in the image or OCR. "
            "Never use internal IDs (C001) as visible tags.\
"
            "- If no tag is visible: set visible_tag to null.\
"
            "- Proximity is NOT connection. Only mark relationships if a line/arrow is visible.\
"
            "- sources list must reflect which pass provided the evidence.\
"
            "- Output ONLY valid JSON.\
\
"
            f"Vision Analysis:\
{combined_text}\
\
"
            f"OCR Findings:\
{ocr_summary}\
"
        )
        raw = self.llm.generate(prompt=prompt, default_category="ENGINEERING")
        try:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group(0)), True, "OK"
        except json.JSONDecodeError as e:
            return self._empty_structured(), False, f"JSONDecodeError: {e}"
        except Exception as e:
            return self._empty_structured(), False, f"Exception: {e}"
        return self._empty_structured(), False, "No JSON found in LLM response."

    # ────────────────────────────────────────────────────────────────────── #
    #  ENTITY RECONCILIATION                                                  #
    # ────────────────────────────────────────────────────────────────────── #
    def _reconcile_entities(self, structured: dict, ocr_findings: list) -> dict:
        """
        Cross-reference OCR labels against parsed components.
        Merges confirmed matches; marks ambiguous ones.
        """
        components   = structured.get("components", [])
        ocr_texts    = {f["text"].upper().strip(): f for f in ocr_findings}
        reconciled   = []
        conflicts    = []

        for comp in components:
            tag = (comp.get("visible_tag") or "").upper().strip()
            comp_out = dict(comp)

            if tag and tag in ocr_texts:
                # Exact OCR match
                ocr_entry = ocr_texts[tag]
                comp_out["ocr_match"]       = SAME_ENTITY
                comp_out["ocr_confidence"]  = ocr_entry.get("confidence")
                comp_out["ocr_bbox"]        = ocr_entry.get("bbox")
                if "LOCAL_OCR" not in comp_out.get("sources", []):
                    comp_out.setdefault("sources", []).append("LOCAL_OCR")
                comp_out["bbox_source"]     = "LOCAL_OCR_EXACT"
            elif tag:
                # Fuzzy check — partial match
                candidates = [t for t in ocr_texts if tag in t or t in tag]
                if candidates:
                    best_ocr = ocr_texts[candidates[0]]
                    comp_out["ocr_match"]   = AMBIGUOUS_ENTITY
                    comp_out["ocr_candidate"] = candidates[0]
                    comp_out["ocr_confidence"] = best_ocr.get("confidence")
                    conflicts.append({
                        "component_id":    comp.get("id"),
                        "moondream_tag":   tag,
                        "ocr_candidate":   candidates[0],
                        "status":          AMBIGUOUS_ENTITY,
                    })
                else:
                    comp_out["ocr_match"] = "NO_OCR_MATCH"
            else:
                comp_out["ocr_match"] = "NO_TAG"

            reconciled.append(comp_out)

        structured["components"] = reconciled
        structured["ocr_conflicts"] = conflicts
        return structured

    # ────────────────────────────────────────────────────────────────────── #
    #  RAG RELEVANCE GATE                                                     #
    # ────────────────────────────────────────────────────────────────────── #
    def evaluate_relevance(self, query: str, structured: dict, reference_text: str) -> str:
        if not reference_text:
            return ""
        comp_tags = [c.get("visible_tag") or c.get("type") for c in structured.get("components", [])]
        prompt = (
            "Evaluate if the retrieved reference document chunks are relevant to the "
            "user question and diagram.\
"
            "Classify: RELEVANT, PARTIALLY_RELEVANT, or NOT_RELEVANT. "
            "One sentence reason.\
\
"
            f"Question: {query}\
"
            f"Diagram component tags: {comp_tags}\
"
            f"Reference text: {reference_text[:800]}\
"
        )
        result = self.llm.generate(prompt=prompt, default_category="ENGINEERING")
        if "NOT_RELEVANT" in result.upper():
            return "NOT_RELEVANT: Document evaluated as not relevant to this diagram."
        return reference_text

    # ────────────────────────────────────────────────────────────────────── #
    #  FAILURE-AWARE REASONING                                                #
    # ────────────────────────────────────────────────────────────────────── #
    def _build_reasoning(self, query: str, visual_state: str, visual_reason: str,
                          structured: dict, ocr_findings: list, relevant_evidence: str,
                          data_context: str, history: list) -> str:
        failure_states = {VISUAL_VISION_MODEL_FAILURE, VISUAL_PARSING_FAILURE,
                          VISUAL_EMPTY_IMAGE, VISUAL_INSUFFICIENT}

        if visual_state in failure_states:
            system_note = (
                "IMPORTANT: The visual analysis pipeline returned no reliable evidence.\
"
                f"Visual state: {visual_state}. Reason: {visual_reason}\
"
                "This is a SYSTEM STATE, NOT a fact about the image content.\
"
                "DO NOT conclude the diagram is empty or blank.\
"
                "You MUST say: 'I cannot confirm any diagram content because the visual "
                "analysis did not produce reliable evidence.'\
"
            )
            context = system_note
            if relevant_evidence and "NOT_RELEVANT" not in relevant_evidence:
                context += f"\
Reference Evidence:\
{relevant_evidence}\
"
            if data_context:
                context += f"\
Data Evidence:\
{data_context}\
"
            prompt = (
                f"Question: {query}\
\
"
                "Based on the available evidence (or lack thereof), answer honestly."
            )
        else:
            # Build claim-level evidence summary
            comp_summary = json.dumps([
                {
                    "id":         c.get("id"),
                    "type":       c.get("type"),
                    "visible_tag": c.get("visible_tag"),
                    "status":     c.get("status"),
                    "ocr_match":  c.get("ocr_match"),
                    "sources":    c.get("sources"),
                }
                for c in structured.get("components", [])
            ], indent=2)

            rel_summary = json.dumps(structured.get("relationships", []), indent=2)

            ocr_summary = json.dumps(
                [{"text": f["text"], "conf": f["confidence"], "bbox": f["bbox"]}
                 for f in ocr_findings], indent=2
            ) if ocr_findings else "[]"

            context = (
                f"Structured Visual Findings:\
{json.dumps(structured.get('metadata', {}))}\
\
"
                f"Components:\
{comp_summary}\
\
"
                f"Topology:\
{rel_summary}\
\
"
                f"OCR Extracted Labels:\
{ocr_summary}\
\
"
            )
            if relevant_evidence and "NOT_RELEVANT" not in relevant_evidence:
                context += f"Reference Evidence:\
{relevant_evidence}\
\
"
            if data_context:
                context += f"Data Evidence:\
{data_context}\
\
"

            prompt = (
                "Rules:\
"
                "1. Separate OBSERVED (directly visible) vs INFERRED vs UNKNOWN.\
"
                "2. Never invent operating parameters, standards, citations, or tags.\
"
                "3. Proximity is NOT connection — only claim topology if visual evidence shows a line/arrow.\
"
                "4. If evidence is absent: say 'I cannot confirm this from available evidence.'\
"
                f"5. Visual state: {visual_state}\
\
"
                f"Question: {query}"
            )

        return self.llm.generate(
            prompt=prompt,
            context=context,
            default_category="ENGINEERING",
            history=history,
        )

    # ────────────────────────────────────────────────────────────────────── #
    #  VERIFICATION                                                           #
    # ────────────────────────────────────────────────────────────────────── #
    def verify_answer(self, query: str, structured: dict, ocr_findings: list,
                      reference_evidence: str, answer: str, visual_state: str) -> dict:
        failure_states = {VISUAL_VISION_MODEL_FAILURE, VISUAL_PARSING_FAILURE, VISUAL_EMPTY_IMAGE}
        if visual_state in failure_states:
            return {
                "claims": [{
                    "claim":  "Verification attempted.",
                    "status": "NOT_VERIFIABLE",
                    "reason": (f"visual_state='{visual_state}'. "
                               "No reliable visual evidence was produced. "
                               "Cannot confirm or deny factual claims about the diagram."),
                }],
                "has_contradiction": False,
                "overall_status":    "FAIL",
                "confidence":        "LOW",
                "verifiable":        False,
            }

        n_comp = len(structured.get("components", []))
        n_rel  = len(structured.get("relationships", []))
        n_ocr  = len(ocr_findings)
        conflicts = structured.get("ocr_conflicts", [])

        prompt = (
            "You are an Engineering Verification AI.\
\
"
            "Context:\
"
            f"- Visual state: {visual_state}\
"
            f"- Components extracted: {n_comp}\
"
            f"- Relationships extracted: {n_rel}\
"
            f"- OCR labels extracted: {n_ocr}\
"
            f"- OCR/Moondream conflicts: {len(conflicts)}\
\
"
            "Rules:\
"
            "SUPPORTED: claim directly backed by structured findings or OCR or reference.\
"
            "UNSUPPORTED: claim makes a factual assertion not in the evidence.\
"
            "CONTRADICTED: claim contradicts available evidence.\
"
            "NOT_VERIFIABLE: claim cannot be assessed because evidence is absent "
            "(system failure, not empty image).\
\
"
            "CRITICAL: Empty components due to parsing/model failure = NOT_VERIFIABLE, "
            "never SUPPORTED for 'diagram is empty'.\
\
"
            "Output JSON:\
"
            "{\
"
            '  "claims": [{"claim":"...","status":"...","reason":"..."}],\
'
            '  "has_contradiction": false,\
'
            '  "overall_status": "<PASS|REVIEW|FAIL>",\
'
            '  "confidence": "<HIGH|MEDIUM|LOW>"\
'
            "}\
\
"
            f"Question: {query}\
"
            f"Findings: {json.dumps(structured)}\
"
            f"OCR: {json.dumps(ocr_findings[:10])}\
"
            f"Reference: {(reference_evidence or '')[:400]}\
"
            f"Answer: {answer}\
"
        )
        raw = self.llm.generate(prompt=prompt, default_category="ENGINEERING")
        try:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                result = json.loads(m.group(0))
                result["verifiable"] = True
                return result
        except Exception:
            pass
        return {"claims": [], "has_contradiction": False, "overall_status": "REVIEW",
                "confidence": "LOW", "verifiable": False}

    # ────────────────────────────────────────────────────────────────────── #
    #  EVIDENCE-BASED CONFIDENCE                                              #
    # ────────────────────────────────────────────────────────────────────── #
    @staticmethod
    def _derive_confidence(visual_state: str, n_components: int, n_labels: int,
                           n_relationships: int, n_ocr: int, verification: dict,
                           has_reference: bool, ocr_conflicts: list) -> str:
        if visual_state in {VISUAL_VISION_MODEL_FAILURE, VISUAL_PARSING_FAILURE,
                             VISUAL_EMPTY_IMAGE}:
            return "LOW"
        if visual_state == VISUAL_INSUFFICIENT:
            return "LOW"

        score = 0
        # Vision evidence quality
        if n_components > 0:    score += 2
        if n_labels > 0:        score += 1
        if n_relationships > 0: score += 2
        # OCR quality
        if n_ocr > 0:           score += 2
        if n_ocr > 3:           score += 1
        # OCR conflicts reduce confidence
        score -= min(len(ocr_conflicts), 3)
        # Reference
        if has_reference:       score += 1
        # Verification
        if verification.get("overall_status") == "PASS": score += 2
        if verification.get("has_contradiction"):         score -= 3
        if visual_state == VISUAL_PARTIAL:                score -= 1

        if score >= 8:   return "HIGH"
        elif score >= 4: return "MEDIUM"
        else:            return "LOW"

    # ────────────────────────────────────────────────────────────────────── #
    #  HITL TRIGGER                                                           #
    # ────────────────────────────────────────────────────────────────────── #
    @staticmethod
    def _should_trigger_hitl(visual_state: str, confidence: str,
                              verification: dict, ocr_conflicts: list) -> tuple:
        if visual_state in {VISUAL_VISION_MODEL_FAILURE, VISUAL_PARSING_FAILURE}:
            return True, ("Visual analysis did not produce sufficient evidence. "
                          "The vision pipeline or structured parser failed.")
        if visual_state == VISUAL_EMPTY_IMAGE:
            return True, "The image appears blank or unreadable. Please verify the uploaded file."
        if ocr_conflicts:
            return True, (f"{len(ocr_conflicts)} ambiguous OCR/vision entity match(es) detected. "
                          "Manual verification recommended.")
        if verification.get("has_contradiction"):
            return True, "Contradictory evidence detected between visual findings and reference documents."
        if verification.get("overall_status") == "FAIL":
            return True, "One or more claims could not be verified against available evidence."
        if confidence == "LOW":
            return True, "Overall evidence confidence is LOW."
        return False, ""

    # ────────────────────────────────────────────────────────────────────── #
    #  MULTI-PASS VISION ORCHESTRATOR                                         #
    # ────────────────────────────────────────────────────────────────────── #
    def multi_pass_vision(self, base64_img: str, query: str) -> dict:
        """Full pipeline: health check → adaptive regional 5-pass → OCR → parse → reconcile."""
        # Health check
        if not base64_img:
            return self._make_failure(VISUAL_VISION_MODEL_FAILURE,
                                      "No image data supplied.")
        health = self._check_image_health(base64_img)
        if not health["healthy"]:
            return self._make_failure(VISUAL_EMPTY_IMAGE, health["reason"])

        pil_img = health["pil"]
        
        # Adaptive: if profile doesn't exist (old health check didn't have it), create it
        if "profile" not in health or not health["profile"]:
            profile = self._profile_image(pil_img)
        else:
            profile = health["profile"]
            
        regions = self._extract_regions(profile)

        # Guard: vision model
        if not self.img_proc:
            return self._make_failure(VISUAL_VISION_MODEL_FAILURE,
                                      "No vision model initialised.")

        global_structured = self._empty_structured()
        global_structured["metadata"]["image_profile"] = profile
        all_ocr_findings = []
        
        total_vision_successful = 0
        total_vision_passes = 0
        global_raw_passes = {}
        global_pass_statuses = {}
        
        import io
        import base64
        
        # Adaptive Hierarchical Processing
        for region in regions:
            # 1. OCR
            if hasattr(self, "ocr"):
                ocr_engine = self.ocr
            elif hasattr(self, "_ocr_engine"):
                ocr_engine = self._ocr_engine
            else:
                from core.ocr_engine import LocalOCREngine
                ocr_engine = LocalOCREngine()
                
            if hasattr(ocr_engine, "run"):
                try:
                    # check if run accepts region
                    import inspect
                    if "region" in inspect.signature(ocr_engine.run).parameters:
                        ocr_result = ocr_engine.run(pil_img, region=region)
                    else:
                        ocr_result = ocr_engine.run(pil_img)
                except Exception:
                    ocr_result = ocr_engine.run(pil_img)
            else:
                ocr_result = {"success": False, "findings": []}
                
            if ocr_result.get("success"):
                all_ocr_findings.extend(ocr_result.get("findings", []))
                
            # 2. Vision (crop if not global)
            if region["id"] == "R0":
                reg_b64 = base64_img
            else:
                crop = pil_img.crop((region["x"], region["y"], region["x"]+region["width"], region["y"]+region["height"]))
                buf = io.BytesIO()
                crop.save(buf, format="JPEG")
                reg_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                
            # Five-pass Moondream
            vp = self._five_pass_vision(reg_b64)
            raw_passes    = vp["raw"]
            pass_statuses = vp["statuses"]
            successful    = vp["successful"]
            total         = vp["total"]
            
            total_vision_successful += successful
            total_vision_passes += total
            
            if region["id"] == "R0":
                global_raw_passes = raw_passes
                global_pass_statuses = pass_statuses
                
            label_map = {
                "pass_1_global":        "--- GLOBAL ---",
                "pass_2_components":    "--- COMPONENTS ---",
                "pass_3_labels":        "--- LABELS ---",
                "pass_4_relationships": "--- RELATIONSHIPS ---",
                "pass_5_ambiguity":     "--- AMBIGUITY ---",
            }
            combined = "\n\n".join(
                f"{lbl}\n{raw_passes[k]}"
                for k, lbl in label_map.items()
                if pass_statuses[k] == PASS_OK
            )
            
            struct, parse_ok, parse_reason = self._parse_structured_findings(combined, ocr_result.get("findings", []))
            
            if parse_ok or parse_reason == "VISUAL_ANALYSIS_PARTIAL":
                struct = self._reconcile_entities(struct, ocr_result.get("findings", []))
                
            # Merge into global
            for c in struct.get("components", []):
                c["id"] = f"{region['id']}_{c.get('id', 'U')}"
                global_structured["components"].append(c)
                
            for r in struct.get("relationships", []):
                r["source_id"] = f"{region['id']}_{r.get('source_id', 'U')}"
                if r.get("target_id") != "BOUNDARY":
                    r["target_id"] = f"{region['id']}_{r.get('target_id', 'U')}"
                global_structured["relationships"].append(r)
                
            if "ocr_conflicts" in struct:
                global_structured.setdefault("ocr_conflicts", []).extend(struct["ocr_conflicts"])

        # Global Deduplication of OCR findings
        try:
            from core.ocr_engine import _compute_iou
            unique_ocr = []
            for f in all_ocr_findings:
                is_dup = False
                for u in unique_ocr:
                    iou = _compute_iou(
                        [f["bbox"]["x"], f["bbox"]["y"], f["bbox"]["x"]+f["bbox"]["width"], f["bbox"]["y"]+f["bbox"]["height"]],
                        [u["bbox"]["x"], u["bbox"]["y"], u["bbox"]["x"]+u["bbox"]["width"], u["bbox"]["y"]+u["bbox"]["height"]]
                    )
                    if iou > 0.4:
                        if f["confidence"] and u["confidence"] and f["confidence"] > u["confidence"]:
                            u["text"] = f["text"]
                            u["confidence"] = f["confidence"]
                        is_dup = True
                        break
                if not is_dup:
                    unique_ocr.append(f)
            all_ocr_findings = unique_ocr
        except ImportError:
            pass

        n_comp = len(global_structured.get("components", []))
        n_lbl  = len(global_structured.get("labels", []))
        n_rel  = len(global_structured.get("relationships", []))
        
        # Determine final visual state
        # Only fail if ALL vision passes failed globally across all regions
        if total_vision_successful == 0:
            visual_state = VISUAL_VISION_MODEL_FAILURE
            reason = "All vision passes failed across all regions."
            parse_ok = False
        elif (n_comp + n_lbl + n_rel) == 0 and total_vision_successful > 0:
            visual_state = VISUAL_INSUFFICIENT
            reason = ("Vision returned responses but no structured entities were extracted. "
                      "Image may be sparse or the model could not identify distinct elements.")
            parse_ok = False
        elif total_vision_successful < total_vision_passes:
            visual_state = VISUAL_PARTIAL
            reason = f"Adaptive processing: {total_vision_successful}/{total_vision_passes} regional passes succeeded."
            parse_ok = True
        else:
            visual_state = VISUAL_SUCCESS
            reason = (f"Adaptive processing successful. "
                      f"Extracted {n_comp} components, {n_lbl} labels, "
                      f"{n_rel} relationships, {len(all_ocr_findings)} OCR labels.")
            parse_ok = True

        return {
            "visual_state":    visual_state,
            "reason":          reason,
            "raw_passes":      global_raw_passes,
            "pass_statuses":   global_pass_statuses,
            "structured":      global_structured,
            "parse_success":   parse_ok,
            "n_components":    n_comp,
            "n_labels":        n_lbl,
            "n_relationships": n_rel,
            "ocr_status":      "OCR_AVAILABLE" if all_ocr_findings else "OCR_NO_TEXT",
            "ocr_findings":    all_ocr_findings,
        }
    def _make_failure(self, state: str, reason: str) -> dict:
        return {
            "visual_state":    state,
            "reason":          reason,
            "raw_passes":      {},
            "pass_statuses":   {},
            "structured":      self._empty_structured(),
            "parse_success":   False,
            "n_components":    0,
            "n_labels":        0,
            "n_relationships": 0,
            "ocr_status":      OCR_UNAVAILABLE,
            "ocr_findings":    [],
        }

    @staticmethod
    def _empty_structured() -> dict:
        return {
            "metadata":      {"diagram_type": "Unknown", "title": "Unknown"},
            "components":    [],
            "labels":        [],
            "relationships": [],
            "ambiguities":   [],
            "ocr_conflicts": [],
        }

    # ────────────────────────────────────────────────────────────────────── #
    #  MAIN ENTRY POINT                                                       #
    # ────────────────────────────────────────────────────────────────────── #
    def generate_final_report(self, query: str, base64_img: str,
                               reference_evidence: str, data_context: str,
                               history: list = None) -> dict:
        # 1. Vision + OCR + Parse + Reconcile
        vision  = self.multi_pass_vision(base64_img, query)
        v_state = vision["visual_state"]
        v_reason = vision["reason"]
        struct  = vision["structured"]
        ocr_f   = vision["ocr_findings"]
        ocr_st  = vision["ocr_status"]
        ps      = vision.get("pass_statuses", {})
        n_comp  = vision["n_components"]
        n_lbl   = vision["n_labels"]
        n_rel   = vision["n_relationships"]
        n_ocr   = len(ocr_f)

        # 2. RAG (after visual — never before)
        rel_evidence = self.evaluate_relevance(query, struct, reference_evidence)
        has_ref = bool(rel_evidence and "NOT_RELEVANT" not in rel_evidence)

        # 3. Reasoning
        answer = self._build_reasoning(query, v_state, v_reason, struct,
                                        ocr_f, rel_evidence, data_context, history)

        # 4. Verification (receives visual_state explicitly)
        verification = self.verify_answer(query, struct, ocr_f,
                                          rel_evidence, answer, v_state)

        # 5. Confidence
        ocr_conflicts = struct.get("ocr_conflicts", [])
        confidence = self._derive_confidence(
            v_state, n_comp, n_lbl, n_rel, n_ocr, verification, has_ref, ocr_conflicts
        )

        # 6. HITL
        hitl_flag, hitl_reason = self._should_trigger_hitl(
            v_state, confidence, verification, ocr_conflicts
        )

        # ── Format response ──────────────────────────────────────────────
        st_emoji = {
            VISUAL_SUCCESS:              "[OK]",
            VISUAL_EMPTY_IMAGE:          "[BLANK]",
            VISUAL_PARSING_FAILURE:      "[PARSE_FAIL]",
            VISUAL_VISION_MODEL_FAILURE: "[VISION_FAIL]",
            VISUAL_INSUFFICIENT:         "[INSUFFICIENT]",
            VISUAL_AMBIGUOUS:            "[AMBIGUOUS]",
            VISUAL_PARTIAL:              "[PARTIAL]",
        }.get(v_state, "[?]")

        md  = "### ENGINEERING ANALYSIS\
\
"
        md += f"**Question:** {query}\
\
"
        md += f"**VISUAL ANALYSIS STATUS:** `{v_state}` {st_emoji}\
"
        md += f"*{v_reason}*\
\
"

        # Pass diagnostics
        if ps:
            md += "**Vision Pass Diagnostics:**\
"
            for k, s in ps.items():
                icon = "[OK]" if s == PASS_OK else "[FAIL]"
                md += f"- {icon} {k.replace('_', ' ').title()}: `{s}`\
"
            md += f"\
**OCR Status:** `{ocr_st}` — {n_ocr} labels extracted\
\
"

        md += "#### 1. DIAGRAM IDENTIFICATION\
"
        md += f"- Type: {struct.get('metadata', {}).get('diagram_type', 'Unknown')}\
"
        md += f"- Title: {struct.get('metadata', {}).get('title', 'Unknown')}\
\
"

        md += "#### 2. DIRECTLY OBSERVED COMPONENTS\
"
        if struct.get("components"):
            for c in struct["components"]:
                tag     = c.get("visible_tag") or "*(no visible tag)*"
                bbox    = f"bbox={c['ocr_bbox']}" if c.get("ocr_bbox") else "bbox=NOT_AVAILABLE"
                ocr_m   = c.get("ocr_match", "N/A")
                srcs    = ", ".join(c.get("sources", []))
                md += (f"- **{c.get('type', '?')}** `{tag}` "
                       f"| Status: {c.get('status', 'UNKNOWN')} "
                       f"| OCR: {ocr_m} | {bbox} | Sources: {srcs}\
")
        else:
            if v_state in {VISUAL_PARSING_FAILURE, VISUAL_VISION_MODEL_FAILURE}:
                md += ("- No components extracted. "
                       "**This reflects a system/model failure, not confirmed image content.**\
")
            else:
                md += "- No components identified in available evidence.\
"

        md += "\
#### 3. VISIBLE LABELS / TAGS (OCR)\
"
        if ocr_f:
            for f in ocr_f[:20]:  # cap display at 20
                conf = f"{f['confidence']:.2f}" if f["confidence"] else "N/A"
                md += (f"- `{f['text']}` | conf={conf} | "
                       f"bbox=({f['bbox']['x']},{f['bbox']['y']},"
                       f"{f['bbox']['width']}x{f['bbox']['height']}) | {f['status']}\
")
        else:
            md += "- No OCR labels extracted.\
"

        if ocr_conflicts:
            md += "\
**OCR/Vision Conflicts:**\
"
            for c in ocr_conflicts:
                md += (f"- Component `{c['component_id']}`: vision=`{c['moondream_tag']}` "
                       f"vs OCR candidate=`{c['ocr_candidate']}` → `{c['status']}`\
")

        md += "\
#### 4. RELATIONSHIPS / TOPOLOGY\
"
        if struct.get("relationships"):
            for r in struct["relationships"]:
                md += (f"- {r.get('source_id', '?')} → {r.get('target_id', '?')} "
                       f"[{r.get('relationship')}] "
                       f"Dir={r.get('direction', '?')} "
                       f"Evidence={r.get('evidence_type', '?')} "
                       f"Pass={r.get('source_pass', '?')} "
                       f"Status={r.get('status', '?')}\
")
        else:
            md += "- No relationships identified.\
"

        md += "\
#### 5. REFERENCE EVIDENCE\
"
        if has_ref:
            md += "- Reference document evaluated as relevant. Chunks cross-referenced.\
\
"
        else:
            md += "- None provided or evaluated as NOT_RELEVANT.\
\
"

        md += "#### 6. REASONING & CONCLUSION\
"
        md += f"{answer}\
\
"

        md += "#### 7. VERIFICATION\
"
        for claim in verification.get("claims", []):
            md += (f"- **{claim.get('status', '?')}**: {claim.get('claim')} "
                   f"— *{claim.get('reason')}*\
")
        if verification.get("has_contradiction"):
            md += "- **CONFLICT DETECTED**: Contradictory evidence found.\
"
        if not verification.get("verifiable", True):
            md += ("- **NOT_VERIFIABLE**: Verification could not proceed "
                   "— reliable visual evidence was not produced.\
")

        md += f"\
#### 8. OVERALL CONFIDENCE: **{confidence}**\
"

        if hitl_flag:
            md += "\
---\
"
            md += "> [!WARNING]\
"
            md += "> **HUMAN VERIFICATION REQUIRED**\
"
            md += f">\
> **Issue:** {hitl_reason}\
"
            md += f">\
> **Detected state:** `{v_state}`\
"
            established = []
            if n_comp > 0: established.append(f"{n_comp} component(s)")
            if n_ocr > 0:  established.append(f"{n_ocr} OCR label(s)")
            if n_rel > 0:  established.append(f"{n_rel} relationship(s)")
            md += f">\
> **Established:** {', '.join(established) or 'Nothing'}\
"
            md += ">\
> **Action:** Review the uploaded image and use Approve / Reject.\
"

        return {
            "markdown":            md,
            "visual_state":        v_state,
            "verification_status": verification.get("overall_status", "REVIEW"),
            "confidence":          confidence,
            "hitl_required":       hitl_flag,
            "hitl_reason":         hitl_reason,
            "pass_statuses":       ps,
            "raw_passes":          vision.get("raw_passes", {}),
            "ocr_status":          ocr_st,
            "ocr_findings":        ocr_f,
        }



class _NullOCR:
    @property
    def available(self): return False
    def run(self, pil_img): return {"success": False, "status": "OCR_NOT_INITIALISED", "findings": []}
