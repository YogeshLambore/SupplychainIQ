import fitz  # PyMuPDF
import re
from typing import List, Dict

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False

class PDFProcessor:
    def __init__(self):
        self.embedding_model = None
        if HAS_EMBEDDINGS:
            try:
                # We load a small model for demo purposes
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self.embedding_model = None
                
    def process_pdf(self, file_path_or_bytes) -> Dict:
        """Extracts text and metadata from PDF."""
        try:
            if isinstance(file_path_or_bytes, str):
                doc = fitz.open(file_path_or_bytes)
            else:
                doc = fitz.open(stream=file_path_or_bytes.read(), filetype="pdf")
                
            text = ""
            pages_data = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                text += page_text + "\n"
                pages_data.append({"page": page_num + 1, "content": page_text})
                
            return {
                "success": True,
                "num_pages": len(doc),
                "text_size": len(text),
                "full_text": text,
                "pages": pages_data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def chunk_text(self, pages_data: List[Dict], chunk_size=500) -> List[Dict]:
        """Splits text into chunks, preserving page numbers."""
        chunks = []
        for page in pages_data:
            content = page["content"]
            # Basic splitting by paragraphs or fixed size
            words = content.split()
            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i:i+chunk_size])
                if chunk_text.strip():
                    chunks.append({"page": page["page"], "text": chunk_text})
        return chunks

    def retrieve_relevant(self, query: str, chunks: List[Dict], top_k=2) -> List[Dict]:
        """Lightweight local RAG using sentence-transformers or keyword fallback."""
        if not chunks:
            return []
            
        if self.embedding_model is not None:
            # Semantic search
            chunk_texts = [c["text"] for c in chunks]
            query_embedding = self.embedding_model.encode([query])
            chunk_embeddings = self.embedding_model.encode(chunk_texts)
            
            similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                results.append({
                    "page": chunks[idx]["page"],
                    "text": chunks[idx]["text"],
                    "similarity": float(similarities[idx])
                })
            return results
        else:
            # Keyword fallback
            query_words = set(re.findall(r'\w+', query.lower()))
            scored_chunks = []
            for chunk in chunks:
                chunk_words = set(re.findall(r'\w+', chunk["text"].lower()))
                score = len(query_words.intersection(chunk_words))
                scored_chunks.append((score, chunk))
                
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, chunk in scored_chunks[:top_k]:
                if score > 0:
                    results.append({
                        "page": chunk["page"],
                        "text": chunk["text"],
                        "similarity": 0.0 # Unknown in keyword search
                    })
            return results
