# services/conversation_service.py - Complete Working Conversation Service
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    """Manages conversation history, sessions, and context-aware responses"""
    
    def __init__(self):
        # In-memory storage (you can later move this to Cosmos DB)
        self.sessions: Dict[str, Dict] = {}
        self.conversations: Dict[str, List[Dict]] = {}
        self.session_timeout = timedelta(hours=24)  # Sessions expire after 24 hours
        
        logger.info("✅ ConversationService initialized")
        
    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = {
            'session_id': session_id,
            'user_id': user_id or 'anonymous',
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'message_count': 0,
            'metadata': {}
        }
        
        self.conversations[session_id] = []
        
        logger.info(f"📝 Created new session: {session_id[:8]}...")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        
        # Check if session has expired
        last_activity = datetime.fromisoformat(session['last_activity'])
        if datetime.now() - last_activity > self.session_timeout:
            self.cleanup_session(session_id)
            return None
            
        return session
    
    def add_message(self, session_id: str, user_message: str, bot_response: str, 
                   message_type: str = 'chat', metadata: Optional[Dict] = None) -> bool:
        """Add a message pair to conversation history"""
        try:
            if session_id not in self.sessions:
                logger.warning(f"Session {session_id} not found")
                return False
            
            # Update session activity
            self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
            self.sessions[session_id]['message_count'] += 1
            
            # Add message to conversation history
            message_entry = {
                'message_id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'user_message': user_message,
                'bot_response': bot_response,
                'message_type': message_type,  # 'chat', 'storage', 'simple'
                'metadata': metadata or {}
            }
            
            self.conversations[session_id].append(message_entry)
            
            # Keep only last 50 messages per session to manage memory
            if len(self.conversations[session_id]) > 50:
                self.conversations[session_id] = self.conversations[session_id][-50:]
            
            logger.info(f"💬 Added message to session {session_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add message: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            return []
        
        # Return recent messages (up to limit)
        return self.conversations[session_id][-limit:]
    
    def get_conversation_context(self, session_id: str, context_length: int = 5) -> str:
        """Get recent conversation context for AI prompting"""
        history = self.get_conversation_history(session_id, context_length)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history[-context_length:]:
            context_parts.append(f"User: {msg['user_message']}")
            context_parts.append(f"Assistant: {msg['bot_response'][:200]}...")  # Truncate long responses
        
        return "\n".join(context_parts)
    
    def cleanup_session(self, session_id: str):
        """Remove expired session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.conversations:
            del self.conversations[session_id]
        logger.info(f"🗑️ Cleaned up expired session: {session_id[:8]}...")
    
    def cleanup_expired_sessions(self):
        """Clean up all expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session['last_activity'])
            if current_time - last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.cleanup_session(session_id)
        
        if expired_sessions:
            logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_all_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get all active sessions, optionally filtered by user"""
        sessions = []
        
        for session_id, session in self.sessions.items():
            if user_id is None or session['user_id'] == user_id:
                # Add conversation preview
                recent_messages = self.get_conversation_history(session_id, 3)
                session_copy = session.copy()
                session_copy['recent_messages'] = recent_messages
                sessions.append(session_copy)
        
        return sorted(sessions, key=lambda x: x['last_activity'], reverse=True)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session and its history"""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.conversations:
                del self.conversations[session_id]
            logger.info(f"🗑️ Deleted session: {session_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete session: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get conversation service statistics"""
        total_sessions = len(self.sessions)
        total_messages = sum(len(conv) for conv in self.conversations.values())
        active_sessions = len([s for s in self.sessions.values() 
                             if datetime.now() - datetime.fromisoformat(s['last_activity']) < timedelta(hours=1)])
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_messages': total_messages,
            'average_messages_per_session': total_messages / max(total_sessions, 1),
            'service_status': 'healthy'
        }

# Global conversation service instance
conversation_service = ConversationService()