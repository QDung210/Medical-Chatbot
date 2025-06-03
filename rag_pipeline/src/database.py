import os
from typing import List, Dict
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid

# Database configuration
DATABASE_URL = "postgresql://postgres:password123@localhost:5432/medical_chatbot"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self.engine.connect() as conn:
            # Create chat_sessions table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    title VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create messages table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sources JSONB,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """))
            
            conn.commit()
    
    def create_session(self, title: str = None) -> str:
        """Create new chat session"""
        session_id = str(uuid.uuid4())
        if not title:
            title = f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO chat_sessions (session_id, title)
                VALUES (:session_id, :title)
            """), {"session_id": session_id, "title": title})
            conn.commit()
            return session_id
    
    def save_message(self, session_id: str, role: str, content: str, sources: List[Dict] = None) -> bool:
        """Save chat message"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO messages (session_id, role, content, sources)
                VALUES (:session_id, :role, :content, :sources)
            """), {
                "session_id": session_id,
                "role": role,
                "content": content,
                "sources": str(sources) if sources else None
            })
            conn.commit()
            return True
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT role, content, sources, timestamp
                FROM messages
                WHERE session_id = :session_id
                ORDER BY timestamp ASC
                LIMIT :limit
            """), {"session_id": session_id, "limit": limit})
            
            return [{
                "role": row[0],
                "content": row[1],
                "sources": eval(row[2]) if row[2] else [],
                "timestamp": row[3].isoformat() if row[3] else None
            } for row in result]
    
    def get_all_sessions(self) -> List[Dict]:
        """Get all chat sessions"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT session_id, title, created_at,
                       (SELECT COUNT(*) FROM messages WHERE messages.session_id = chat_sessions.session_id) as message_count
                FROM chat_sessions
                ORDER BY created_at DESC
            """))
            
            return [{
                "session_id": row[0],
                "title": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "message_count": row[3]
            } for row in result]

# Global instance
db_manager = DatabaseManager()
