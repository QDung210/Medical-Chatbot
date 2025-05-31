import os
import logging
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

def connect_to_qdrant():
    """Connect to Qdrant Cloud if env vars are set, else báo lỗi."""
    cloud_url = os.getenv('QDRANT_CLOUD_URL')
    api_key = os.getenv('QDRANT_API_KEY')
    if cloud_url and api_key:
        try:
            logger.info(f"🌐 Connecting to Qdrant Cloud: {cloud_url}")
            client = QdrantClient(url=cloud_url, api_key=api_key, timeout=30, prefer_grpc=False)
            # Test connection
            collections = client.get_collections()
            logger.info(f"✅ Connected to Qdrant Cloud successfully! Collections: {[c.name for c in collections.collections]}")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant Cloud: {e}")
            return None
    else:
        logger.error("❌ Qdrant Cloud credentials not found in environment variables.")
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