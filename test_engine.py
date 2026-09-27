import json
import base64
from core.engineering_analyzer import EngineeringAnalyzer
from core.llm import LLMManager

class MockImageAnalyzer:
    def query_vision_model(self, base64_img, query):
        if "overall" in query: return "This is a P&ID diagram of a cooling system."
        if "components" in query: return "Pump P-101, Heat Exchanger HX-201, Valve V-102."
        if "labels" in query: return "P-101, HX-201, V-102, COOLING_WATER_IN."
        if "lines" in query: return "P-101 flows to V-102. V-102 flows to HX-201."
        if "ambiguous" in query: return "Label on the heat exchanger is slightly blurry but readable."
        return "Unknown"

def test_pipeline():
    llm = LLMManager(model_name="llama3:8b")
    # if Ollama isn't running, this will fall back cleanly in LLMManager
    
    img_proc = MockImageAnalyzer()
    analyzer = EngineeringAnalyzer(llm, img_proc)
    
    query = "What is connected to the pump?"
    base64_img = "mock_base64"
    reference_evidence = "[Page 1] Pump P-101 feeds into control valve V-102."
    data_context = ""
    
    report = analyzer.generate_final_report(query, base64_img, reference_evidence, data_context)
    
    with open("test_engine_report.txt", "w", encoding="utf-8") as f:
        f.write(report["markdown"])
        f.write(f"\n\nHITL Required: {report['hitl_required']}\n")
    print("Test finished successfully.")

if __name__ == "__main__":
    test_pipeline()
