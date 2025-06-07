import logging
from pathlib import Path
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "llama-3.1-8b-instant"
COLLECTION = "medical_data"
CACHE_DIR = Path(__file__).parent.parent.parent / ".cache"
EMBEDDINGS_MODEL = CACHE_DIR / "model"

class Resources:
    def __init__(self):
        self.client = None
        self.embedder = None
        self._init_resources()
    
    def _init_resources(self):
        """Initialize Qdrant client and embedder"""
        try:
            logger.info("Khởi tạo Qdrant client và embedder...")
            
            # Initialize Qdrant client
            self.client = QdrantClient(url="http://localhost:6333")
            
            # Initialize embedder
            self.embedder = SentenceTransformer(str(EMBEDDINGS_MODEL))
            
            logger.info("Khởi tạo resources thành công")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo resources: {e}")
            raise

# Global resources instance
resources = Resources()

def get_hardware():
    """Get hardware info"""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu" 