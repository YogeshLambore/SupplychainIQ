import chromadb
import uuid
import datetime
import os

class HistoryManager:
    def __init__(self, persist_directory="./data/chroma"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.sessions = self.client.get_or_create_collection(name="nexora_sessions")
            self.messages = self.client.get_or_create_collection(name="nexora_messages")
            self.documents = self.client.get_or_create_collection(name="nexora_documents")
            self.analysis = self.client.get_or_create_collection(name="nexora_analysis")
            self.is_connected = True
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            self.is_connected = False
            
    def create_session(self, workspace: str, default_title: str = "New Conversation") -> str:
        if not self.is_connected: return f"temp_sess_{uuid.uuid4().hex[:6]}"
        
        session_id = f"sess_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now = datetime.datetime.now().isoformat()
        
        try:
            self.sessions.add(
                ids=[session_id],
                metadatas=[{"workspace": workspace, "created_at": now, "updated_at": now}],
                documents=[default_title]
            )
        except Exception as e:
            print(f"Error creating session: {e}")
        return session_id

    def update_session_timestamp(self, session_id: str):
        if not self.is_connected or session_id.startswith("temp_"): return
        try:
            res = self.sessions.get(ids=[session_id])
            if res and res['ids']:
                metadata = res['metadatas'][0]
                metadata['updated_at'] = datetime.datetime.now().isoformat()
                self.sessions.update(ids=[session_id], metadatas=[metadata])
        except Exception:
            pass

    def add_message(self, session_id: str, role: str, content: str, workspace: str, model: str = None) -> str:
        if not self.is_connected or session_id.startswith("temp_"): return "temp_msg"
        
        msg_id = f"msg_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now = datetime.datetime.now().isoformat()
        try:
            meta = {"session_id": session_id, "role": role, "timestamp": now, "workspace": workspace}
            if model:
                meta["model"] = model
            self.messages.add(
                ids=[msg_id],
                metadatas=[meta],
                documents=[content]
            )
            self.update_session_timestamp(session_id)
        except Exception as e:
            print(f"Error adding message: {e}")
        return msg_id

    def get_messages(self, session_id: str):
        if not self.is_connected or session_id.startswith("temp_"): return []
        try:
            results = self.messages.get(where={"session_id": session_id})
            if not results or not results['ids']:
                return []
            
            msgs = []
            for i in range(len(results['ids'])):
                msg = {
                    "id": results['ids'][i],
                    "role": results['metadatas'][i]["role"],
                    "content": results['documents'][i],
                    "timestamp": results['metadatas'][i]["timestamp"]
                }
                if "model" in results['metadatas'][i]:
                    msg["model"] = results['metadatas'][i]["model"]
                msgs.append(msg)
            
            msgs.sort(key=lambda x: x["timestamp"])
            return msgs
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    def get_sessions(self):
        if not self.is_connected: return []
        try:
            results = self.sessions.get()
            if not results or not results['ids']:
                return []
            
            sessions = []
            for i in range(len(results['ids'])):
                sessions.append({
                    "session_id": results['ids'][i],
                    "title": results['documents'][i],
                    "workspace": results['metadatas'][i]["workspace"],
                    "created_at": results['metadatas'][i]["created_at"],
                    "updated_at": results['metadatas'][i]["updated_at"]
                })
                
            sessions.sort(key=lambda x: x['updated_at'], reverse=True)
            return sessions
        except Exception as e:
            print(f"Error retrieving sessions: {e}")
            return []

    def delete_session(self, session_id: str):
        if not self.is_connected: return
        try:
            self.sessions.delete(ids=[session_id])
            self.messages.delete(where={"session_id": session_id})
            try:
                self.documents.delete(where={"session_id": session_id})
                self.analysis.delete(where={"session_id": session_id})
            except Exception:
                pass
        except Exception as e:
            print(f"Error deleting session: {e}")
            
    def rename_session(self, session_id: str, new_title: str):
        if not self.is_connected: return
        try:
            self.sessions.update(ids=[session_id], documents=[new_title])
        except Exception as e:
            print(f"Error renaming session: {e}")
            
    def link_document(self, session_id: str, filename: str, file_bytes: bytes):
        if not self.is_connected or session_id.startswith("temp_"): return
        try:
            os.makedirs("./data/uploads", exist_ok=True)
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            file_path = f"./data/uploads/{session_id}_{safe_filename}"
            with open(file_path, "wb") as f:
                f.write(file_bytes)
                
            doc_id = f"doc_{uuid.uuid4().hex[:6]}"
            self.documents.add(
                ids=[doc_id],
                metadatas=[{"session_id": session_id, "file_path": file_path, "filename": filename}],
                documents=[filename]
            )
        except Exception as e:
            print(f"Error linking document: {e}")
            
    def get_session_document(self, session_id: str):
        if not self.is_connected or session_id.startswith("temp_"): return None
        try:
            res = self.documents.get(where={"session_id": session_id})
            if res and res['ids']:
                return res['metadatas'][0]
        except Exception:
            pass
        return None
            
    def generate_title(self, session_id: str, workspace: str, task: str, filename: str, llm_manager) -> str:
        """Generates an automatic session title."""
        if not self.is_connected or session_id.startswith("temp_"): return
        
        deterministic_title = f"{workspace} Analysis"
        if filename:
            deterministic_title = f"{filename} Analysis"
            
        if not llm_manager or not llm_manager.is_loaded:
            self.rename_session(session_id, deterministic_title)
            return deterministic_title
            
        prompt = (
            f"Generate a very short, 3 to 7 word title for this conversation.\n"
            f"Workspace: {workspace}\n"
            f"File: {filename}\n"
            f"Task: {task}\n"
            f"Requirements: Only output the title. Do not output any other text or punctuation."
        )
        try:
            title = llm_manager.generate(prompt=prompt, context="", default_category="GENERAL")
            title = title.strip('*\"\'\n ')
            if len(title) > 0 and len(title) < 50:
                self.rename_session(session_id, title)
                return title
        except Exception:
            pass
            
        self.rename_session(session_id, deterministic_title)
        return deterministic_title