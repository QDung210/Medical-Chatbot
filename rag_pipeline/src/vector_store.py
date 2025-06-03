import os
from typing import List, Dict, Optional, Callable
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

QDRANT_CLOUD_URL = os.getenv('QDRANT_CLOUD_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

class VectorStore:
    def __init__(self):
        """Initialize Vector Store"""
        self.client = None
        self._connect()

    def _connect(self) -> None:
        """Connect to Qdrant Cloud"""
        if not (QDRANT_CLOUD_URL and QDRANT_API_KEY):
            return

        try:
            self.client = QdrantClient(
                url=QDRANT_CLOUD_URL,
                api_key=QDRANT_API_KEY,
                timeout=30
            )
        except Exception:
            self.client = None

    def create_retriever(
        self,
        collection_name: str,
        embedding_model: SentenceTransformer,
        top_k: int = 5
    ) -> Optional[Callable]:
        """Create similarity search function"""
        if not self.client:
            return None

        def retrieve(query: str, limit: int = top_k) -> List[Dict]:
            try:
                query_vector = embedding_model.encode(query).tolist()
                search_results = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=limit,
                    with_payload=True
                )
                
                return [{
                    'content': result.payload.get('content', ''),
                    'metadata': result.payload.get('metadata', {}),
                    'score': result.score
                } for result in search_results.points]
                
            except Exception:
                return []
        
        return retrieve

    def cleanup(self) -> None:
        """Cleanup connection"""
        if self.client:
            try:
                self.client.close()
                self.client = None
            except:
                pass 