import uuid
import psycopg
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_postgres import PostgresChatMessageHistory

# Database connection settings
DB_CONFIG = {
    "dbname": "chatbot_db",
    "user": "postgres", 
    "password": "123456",
    "host": "localhost",
    "port": "5433",
}

table_name = "message_store"

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    """Get chat history by session ID"""
    sync_connection = psycopg.connect(**DB_CONFIG)
    
    return PostgresChatMessageHistory(
        table_name, 
        session_id, 
        sync_connection=sync_connection
    ) 