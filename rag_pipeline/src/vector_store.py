import logging
from typing import List, Dict, Optional, Callable
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from .config import QDRANT_CLOUD_URL, QDRANT_API_KEY

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        """Khởi tạo Vector Store"""
        self.client = None
        self._connect()

    def _connect(self) -> None:
        """Kết nối tới Qdrant Cloud"""
        if not (QDRANT_CLOUD_URL and QDRANT_API_KEY):
            logger.error("Thiếu thông tin xác thực Qdrant Cloud")
            return

        try:
            self.client = QdrantClient(
                url=QDRANT_CLOUD_URL,
                api_key=QDRANT_API_KEY,
                timeout=30,
                prefer_grpc=False
            )
            collections = self.client.get_collections()
            logger.info(f"Đã kết nối thành công tới Qdrant Cloud! Collections: {[c.name for c in collections.collections]}")
        except Exception as e:
            logger.error(f"Không thể kết nối tới Qdrant Cloud: {e}")
            self.client = None

    def create_retriever(
        self,
        collection_name: str,
        embedding_model: SentenceTransformer,
        top_k: int = 5
    ) -> Optional[Callable]:
        """Tạo hàm truy xuất dữ liệu dựa trên độ tương đồng"""
        if not self.client:
            logger.error("Chưa kết nối tới Qdrant")
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
                
            except Exception as e:
                logger.error(f"Lỗi tìm kiếm: {e}")
                return []
        
        return retrieve

    def cleanup(self) -> None:
        """Dọn dẹp kết nối"""
        if self.client:
            try:
                self.client.close()
                self.client = None
            except Exception as e:
                logger.warning(f"Lỗi khi đóng kết nối: {e}")

    def __del__(self):
        """Hủy đối tượng"""
        self.cleanup() 