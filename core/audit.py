import datetime

class AuditLogger:
    """Manages the execution trace for the agentic workflows."""
    
    def __init__(self):
        self.logs = []
        
    def log(self, task: str, action: str, details: str, status: str = "PASS"):
        """Logs an event to the audit trace."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "task": task,
            "action": action,
            "details": details,
            "status": status
        }
        self.logs.append(entry)
        return entry
        
    def get_logs(self):
        return self.logs
        
    def clear(self):
        self.logs = []

# Global singleton for demo purposes (usually would be tied to session state)
# But we'll handle this in Streamlit session state instead of a true global.
