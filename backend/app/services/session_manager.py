"""Session management for in-memory state storage."""
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid

from app.models.schema import ClarifyingQuestion, SessionState


class SessionStore:
    """In-memory session store for managing user sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
    
    def create_session(self, nl_input: str, file_context: Optional[str] = None) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        
        session = SessionState(
            session_id=session_id,
            nl_input=nl_input,
            file_context=file_context,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve a session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, updates: dict) -> Optional[SessionState]:
        """Update session with new data."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.now(timezone.utc)
        self.sessions[session_id] = session
        return session

    def set_questions(self, session_id: str, questions: list[ClarifyingQuestion]) -> bool:
        """Store clarifying questions in the session."""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.clarifying_questions = questions
        session.updated_at = datetime.now(timezone.utc)
        return True
    
    def add_to_chat_history(self, session_id: str, role: str, content: str) -> bool:
        """Add message to chat history"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.chat_history.append({"role": role, "content": content})
        session.updated_at = datetime.now(timezone.utc)
        return True
    
    def get_chat_history(self, session_id: str) -> list:
        """Get chat history for a session"""
        session = self.sessions.get(session_id)
        return session.chat_history if session else []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> list:
        """List all active sessions"""
        return list(self.sessions.keys())


# Global instance
session_store = SessionStore()
