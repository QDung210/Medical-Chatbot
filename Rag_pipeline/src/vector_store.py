import os
import logging
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

def connect_to_qdrant(storage_path="./qdrant_storage"):
    """Connect to local Qdrant instance"""
    try:
        # Normalize the path first
        storage_path = os.path.normpath(os.path.abspath(storage_path))
        
        if not os.path.exists(storage_path):
            logger.error(f"Qdrant storage path does not exist: {storage_path}")
            return None
            
        client = QdrantClient(path=storage_path)
        logger.info(f"Connected to Qdrant at: {storage_path}")
        
        # Try to get collections but don't fail if none exist
        try:
            collections = client.get_collections().collections
            if collections:
                logger.info(f"Found {len(collections)} collections")
                for coll in collections:
                    logger.info(f"  - {coll.name}")
            else:
                logger.warning("No collections found in Qdrant")
        except Exception as e:
            logger.warning(f"Could not list collections: {e}")
        
        return client
        
    except Exception as e:
        error_msg = str(e)
        if "already accessed by another instance" in error_msg:
            logger.error(f"Qdrant database is locked by another instance. Please close other applications using Qdrant at: {storage_path}")
        else:
            logger.error(f"Failed to connect to Qdrant: {e}")
        return None

def get_qdrant_retriever(client, collection_name="medical_data", embedding_model=None, top_k=5):
    """Create Qdrant retriever for similarity search"""
    if not client:
        logger.error("No Qdrant client provided")
        return None
    
    if not embedding_model:
        # Import here to avoid circular import
        try:
            from model_setup import load_embedding_model
            embedding_model = load_embedding_model()
        except ImportError:
            logger.error("Cannot import load_embedding_model")
            return None
    
    def retrieve(query, limit=top_k):
        try:
            query_vector = embedding_model.encode(query).tolist()
            
            # Use the newer query_points method instead of deprecated search
            search_results = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True
            )
            
            documents = []
            for result in search_results.points:
                doc = {
                    'content': result.payload.get('content', ''),
                    'metadata': result.payload.get('metadata', {}),
                    'score': result.score
                }
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    return retrieve 