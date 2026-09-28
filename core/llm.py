import os
import re
import requests
import json
from pathlib import Path
from typing import Optional

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"

# ─── Multi-model chat configuration ──────────────────────────────────────────
CHAT_MODELS = {
    "⚡ Fast":          "qwen3.5:4b",
    "👨‍💻 Coding":       "qwen2.5-coder:3b",
    "🧠 Deep Reasoning": "llama3:8b",
}

CHAT_MODEL_LABELS = {
    "qwen3.5:4b":       ("⚡", "Fast",          "Qwen3.5 4B",          "General questions and quick answers"),
    "qwen2.5-coder:3b": ("👨‍💻", "Coding",        "Qwen2.5-Coder 3B",    "Programming and software engineering"),
    "llama3:8b":        ("🧠", "Deep Reasoning", "Llama 3 8B",          "Complex reasoning and detailed analysis"),
}

CHAT_SYSTEM_PROMPTS = {
    "qwen3.5:4b": (
        "You are SupplyChain AI Fast, a concise local AI assistant. "
        "Answer accurately and directly. "
        "Prefer clear explanations and avoid unnecessary verbosity. "
        "Do not expose internal reasoning or hidden chain-of-thought. "
        "When the user requests detailed reasoning, inform them they can switch to Deep Reasoning mode."
    ),
    "qwen2.5-coder:3b": (
        "You are SupplyChain AI Coding, a local software engineering assistant. "
        "Focus on correct, practical, maintainable code. "
        "Explain important implementation decisions briefly. "
        "When useful, provide complete runnable code. "
        "Consider edge cases and algorithmic complexity. "
        "Do not expose hidden chain-of-thought. "
        "ALWAYS wrap code in markdown code blocks with the correct language tag."
    ),
    "llama3:8b": (
        "You are the local language model used by SupplyChain AI. "
        "You are a helpful, professional, general-purpose local AI conversation interface and coding assistant. "
        "You can answer general questions, write complex Python code, and analyze provided context. "
        "When providing code, ALWAYS wrap it in markdown code blocks."
    ),
}


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
        return "READY" if self.is_loaded else "FALLBACK"

    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific Ollama model is installed locally. Does not affect self.is_loaded."""
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                return model_name in models
        except Exception:
            pass
        return False

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Remove <think>...</think> blocks that some local models emit internally."""
        import re as _re
        # Strip complete think blocks (including multiline)
        cleaned = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL)
        # Also strip any unclosed <think> block at the start (model cut off mid-thought)
        cleaned = _re.sub(r'^<think>.*', '', cleaned, flags=_re.DOTALL)
        return cleaned.strip()

    def generate_with_model(
        self,
        prompt: str,
        model_name: str,
        context: str = None,
        history: list = None,
    ) -> str:
        """
        Send a chat request to a specific local Ollama model.
        Uses mode-specific system prompts from CHAT_SYSTEM_PROMPTS.
        Strips internal thinking tokens before returning.
        Falls back to deterministic response if Ollama is unreachable.
        """
        # Availability guard
        if not self.is_model_available(model_name):
            return (
                f"⚠️ **Selected local model `{model_name}` is not installed.**\n\n"
                "Please install it using Ollama before using this mode.\n\n"
                "Local AI engine must be running and the model must be downloaded."
            )

        system_prompt = CHAT_SYSTEM_PROMPTS.get(model_name, CHAT_SYSTEM_PROMPTS["llama3:8b"])

        full_prompt = f"SYSTEM INSTRUCTIONS\n{system_prompt}\n\n"

        if context:
            full_prompt += f"SOURCE CONTEXT\n{context}\n\n"

        if history:
            full_prompt += "CONVERSATION HISTORY\n"
            for msg in history:
                role_str = "User" if msg.get("role") == "user" else "Assistant"
                full_prompt += f"{role_str}: {msg.get('content', '')}\n"
            full_prompt += "\n"

        full_prompt += f"USER QUESTION\n{prompt}\n"

        payload = {
            "model": model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            if response.status_code == 200:
                raw = response.json().get("response", "").strip()
                return self._strip_thinking(raw)
            else:
                return f"⚠️ **Local AI engine returned an error** (HTTP {response.status_code}). Please verify Ollama is running."
        except requests.exceptions.ConnectionError:
            return "⚠️ **Local AI engine is unavailable.** Please verify that Ollama is running."
        except requests.exceptions.Timeout:
            return "⚠️ **Request timed out.** The model may be loading — please try again."
        except Exception as e:
            print(f"generate_with_model error: {e}")
            return "⚠️ **An error occurred during inference.** Please check Ollama status."


    def route_task(self, query: str, default_category: str) -> str:
        query_lower = query.lower()
        if "SupplyChain AI" in query_lower or "what is" in query_lower and "SupplyChain AI" in query_lower:
            return "GENERAL"
        return default_category
        
    def generate_viz_plan(self, query: str, schema_context: str) -> Optional[dict]:
        """
        Calls Llama to convert a natural-language visualization request into a
        structured JSON plan. Returns a dict or None if Llama is unavailable or
        the response cannot be parsed as valid JSON.
        All numeric calculations remain with Pandas — Llama only identifies intent.
        """
        import json
        try:
            self.is_loaded = self.check_health()
            if not self.is_loaded:
                return None

            prompt = (
                "You are a data visualization intent classifier. "
                "Given a dataset schema and a user request, output ONLY a valid JSON object "
                "with these exact keys (no extra text, no markdown, no explanation):\n"
                "{\n"
                '  "chart_type": "<bar|hbar|grouped_bar|stacked_bar|line|time_series|area|cumulative|'
                'moving_avg|pie|donut|histogram|scatter|box|corr_heatmap|heatmap|count|pareto|funnel|top_n|ranking>",\n'
                '  "x_column": "<exact column name or null>",\n'
                '  "y_column": "<exact column name or null>",\n'
                '  "aggregation": "<sum|mean|count|median|min|max|std>",\n'
                '  "group_by": "<column name or null>",\n'
                '  "filter_column": "<column name or null>",\n'
                '  "filter_operator": "<year_eq|eq|gte|lte|gt|lt|contains or null>",\n'
                '  "filter_value": "<value or null>",\n'
                '  "sort": "<ascending|descending|none>",\n'
                '  "top_n": <integer or null>,\n'
                '  "title": "<concise chart title>"\n'
                "}\n\n"
                f"Dataset schema:\n{schema_context}\n\n"
                f"User request: {query}\n\n"
                "Output ONLY the JSON object:"
            )

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 400}
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            if response.status_code != 200:
                return None

            raw = response.json().get("response", "").strip()
            # Extract JSON block
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return None
            plan = json.loads(m.group(0))
            # Basic sanity: must have chart_type
            if "chart_type" not in plan:
                return None
            return plan
        except Exception:
            return None

    def generate(self, prompt: str, context: str = None, default_category: str = "DOCUMENT", history: list = None) -> str:

        """Generates an answer based on prompt and context using Ollama, or falls back."""
        self.is_loaded = self.check_health()
        
        category = self.route_task(prompt, default_category)
        
        if self.is_loaded:
            try:
                if category == "GENERAL":
                    system_prompt = (
                        "You are the local language model used by SupplyChain AI. "
                        "You are a helpful, professional, general-purpose local AI conversation interface and coding assistant. "
                        "You can answer general questions, write complex Python code, and analyze provided context. "
                        "When providing code, ALWAYS wrap it in markdown code blocks."
                    )
                else:
                    system_prompt = (
                        "You are the local language model used by SupplyChain AI. "
                        "SupplyChain AI is an offline/on-premise AI workbench for confidential industrial work. "
                        "It uses local open-weight AI models and supports controlled workflows. "
                        "Follow only the provided context. Do not invent facts. "
                        "Do not claim unavailable information. Explain clearly and concisely. "
                        "Do not create fictional company deployments. Do not guess."
                    )
                
                full_prompt = f"SYSTEM INSTRUCTIONS\n{system_prompt}\n\n"
                
                if category == "GENERAL":
                    full_prompt += "CONTEXT\nSupplyChain AI is a sovereign on-premise agentic AI workbench. It processes documents, data, and engineering files securely and locally without external APIs.\n\n"
                
                if context:
                    full_prompt += f"SOURCE CONTEXT\n{context}\n\n"
                    
                if history:
                    full_prompt += "CONVERSATION HISTORY\n"
                    for msg in history:
                        role_str = "User" if msg.get("role") == "user" else "Assistant"
                        full_prompt += f"{role_str}: {msg.get('content')}\n"
                    full_prompt += "\n"
                    
                full_prompt += f"USER QUESTION\n{prompt}\n\n"
                
                if category != "GENERAL":
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
        fallback_msg = "Local Llama is unavailable. SupplyChain AI is using the existing local processing path.\n\n"
        
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
