import os
import requests
import json
from pathlib import Path

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"

class LLMManager:
    """Manages LLM invocation and fallbacks using local Ollama."""
    
    def __init__(self, model_name: str = "llama3:8b"):
        self.model_name = model_name
        self.is_loaded = self.check_health()
        
    def check_health(self):
        """Checks if Ollama is running and the model is available."""
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                if self.model_name in models:
                    return True
        except Exception:
            pass
        return False
        
    def get_status(self):
        self.is_loaded = self.check_health()
        return "READY" if self.is_loaded else "FALLBACK"
        
    def route_task(self, query: str, default_category: str) -> str:
        query_lower = query.lower()
        if "nexora" in query_lower or "what is" in query_lower and "nexora" in query_lower:
            return "GENERAL"
        return default_category
        
    def generate(self, prompt: str, context: str = None, default_category: str = "DOCUMENT") -> str:
        """Generates an answer based on prompt and context using Ollama, or falls back."""
        self.is_loaded = self.check_health()
        
        category = self.route_task(prompt, default_category)
        
        if self.is_loaded:
            try:
                system_prompt = (
                    "You are the local language model used by NEXORA. "
                    "NEXORA is an offline/on-premise AI workbench for confidential industrial work. "
                    "It uses local open-weight AI models and supports controlled workflows. "
                    "Follow only the provided context. Do not invent facts. "
                    "Do not claim unavailable information. Explain clearly and concisely. "
                    "Do not create fictional company deployments. Do not guess."
                )
                
                full_prompt = f"SYSTEM INSTRUCTIONS\n{system_prompt}\n\n"
                
                if category == "GENERAL":
                    full_prompt += "CONTEXT\nNEXORA is a sovereign on-premise agentic AI workbench. It processes documents, data, and engineering files securely and locally without external APIs.\n\n"
                elif context:
                    full_prompt += f"SOURCE CONTEXT\n{context}\n\n"
                    
                full_prompt += f"USER QUESTION\n{prompt}\n\n"
                full_prompt += "RESPONSE REQUIREMENTS\nAnswer using only the available information. If information is missing, you MUST say exactly: 'I could not find this information in the available data.' Do NOT guess.\n"
                
                payload = {
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1
                    }
                }
                
                response = requests.post(OLLAMA_URL, json=payload, timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                else:
                    return self._try_fallback_model(full_prompt, prompt, context)
            except Exception as e:
                print(f"Ollama inference failed: {e}")
                return self._try_fallback_model(full_prompt, prompt, context)
                
        # Fallback Mode
        return self._deterministic_fallback(prompt, context)
        
    def _try_fallback_model(self, full_prompt: str, original_prompt: str, context: str) -> str:
        """Tries to use another available model in Ollama if the primary fails."""
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                fallback_models = [m for m in models if m != self.model_name]
                if fallback_models:
                    fallback_model = fallback_models[0]
                    payload = {
                        "model": fallback_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                    fallback_resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
                    if fallback_resp.status_code == 200:
                        data = fallback_resp.json()
                        return f"*(Generated using fallback model: {fallback_model})*\n\n" + data.get("response", "").strip()
        except Exception as e:
            print(f"Fallback model failed: {e}")
            pass
        return self._deterministic_fallback(original_prompt, context)
        
    def _deterministic_fallback(self, prompt: str, context: str) -> str:
        """Provides a deterministic answer when the local LLM is missing."""
        prompt_lower = prompt.lower()
        fallback_msg = "Local Llama is unavailable. NEXORA is using the existing local processing path.\n\n"
        
        if not context:
            return f"{fallback_msg}Could not generate deterministic response without context."
            
        if "summar" in prompt_lower or "findings" in prompt_lower:
            return f"{fallback_msg}**Deterministic Fallback Summary:**\nThe uploaded document contains {len(context.split())} words. Key sections extracted:\n\n{context}\n\n*(Local Llama model unavailable - using deterministic extraction)*"
            
        if "date" in prompt_lower:
            import re
            dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', context)
            if dates:
                return f"{fallback_msg}**Deterministic Fallback:** Found date(s): {', '.join(dates)}."
            return f"{fallback_msg}No dates found in the provided context."
            
        return f"{fallback_msg}**Deterministic Fallback:**\n\nI found the following relevant information:\n\n{context}\n\n*(Full reasoning requires Local LLM which is currently NOT LOADED)*"
