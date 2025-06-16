import logging
import os
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

def download_model_if_needed():
    """
    Tải về embedding model nếu thư mục .cache/model chưa tồn tại
    """
    try:
        # Kiểm tra xem thư mục .cache có tồn tại không
        if not CACHE_DIR.exists():
            logger.info(f"Tạo thư mục .cache tại: {CACHE_DIR}")
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Kiểm tra xem model đã được tải về chưa
        if not EMBEDDINGS_MODEL.exists() or not any(EMBEDDINGS_MODEL.iterdir()):
            logger.info("Thư mục model chưa tồn tại hoặc rỗng. Đang tải embedding model...")
            logger.info("Quá trình này có thể mất vài phút...")
            EMBEDDINGS_MODEL.mkdir(parents=True, exist_ok=True)
            model_name = "strongpear/M3-retriever-MEDICAL" 
            temp_model = SentenceTransformer(model_name)
            
            # Lưu model vào thư mục cache
            temp_model.save(str(EMBEDDINGS_MODEL))
            logger.info(f"Đã tải và lưu model tại: {EMBEDDINGS_MODEL}")
            
        else:
            logger.info(f"Model đã tồn tại tại: {EMBEDDINGS_MODEL}")
            
    except Exception as e:
        logger.error(f"Lỗi khi tải model: {e}")
        raise

class Resources:
    def __init__(self):
        self.client = None
        self.embedder = None
        self._init_resources()
    
    def _init_resources(self):
        """Initialize Qdrant client and embedder"""
        try:
            logger.info("Khởi tạo Qdrant client và embedder...")
            
            # Đảm bảo model đã được tải về
            download_model_if_needed()
            
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
    return "cpu" 
    # Uncomment chỗ này nếu có GPU
    # import torch
    # if torch.cuda.is_available():
    #     return "cuda"
    # else:
    #     return "cpu" 