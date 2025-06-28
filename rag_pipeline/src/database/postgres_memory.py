import uuid
import psycopg
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_postgres import PostgresChatMessageHistory
import logging
import os

# Set up logging
logger = logging.getLogger(__name__)

# Database connection settings - use environment variables
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "medical_chatbot"),
    "user": os.getenv("POSTGRES_USER", "admin"), 
    "password": os.getenv("POSTGRES_PASSWORD", "admin123"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

table_name = "message_store"

def init_database():
    """Initialize database and create table if not exists"""
    try:
        logger.info("Initializing PostgreSQL database...")
        connection = psycopg.connect(**DB_CONFIG)
        
        # Setup schema - this will create the table if it doesn't exist
        PostgresChatMessageHistory.create_tables(connection, table_name)
        logger.info(f"Database initialized successfully. Table '{table_name}' ready.")
        connection.close()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    """Get chat history by session ID"""
    logger.info(f"PostgreSQL: Getting chat history for session_id: {session_id}")
    sync_connection = psycopg.connect(**DB_CONFIG)
    
    # Convert session_id to valid UUID if it's not already
    try:
        # Try to parse as UUID first
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        # If not valid UUID, create UUID from string hash
        import hashlib
        hash_object = hashlib.md5(session_id.encode())
        hash_hex = hash_object.hexdigest()
        # Format as UUID string
        session_uuid = uuid.UUID(hash_hex)
        logger.info(f"Converted session_id '{session_id}' to UUID: {session_uuid}")
    
    return PostgresChatMessageHistory(
        table_name, 
        str(session_uuid), 
        sync_connection=sync_connection
    ) 