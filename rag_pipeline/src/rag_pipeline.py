import logging
import os
from typing import Dict, List, Optional
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Configuration constants
DEFAULT_MODEL = 'llama-3.3-70b-versatile'
DEFAULT_COLLECTION = 'medical_data'
DEFAULT_TOP_K = 10
DEFAULT_MAX_TOKENS = 1024
EMBEDDING_MODEL = 'strongpear/M3-retriever-MEDICAL'

from .model_setup import ModelManager
from .vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalRAGPipeline:
    def __init__(self, collection_name: str = DEFAULT_COLLECTION, model_name: str = DEFAULT_MODEL):
        """Khởi tạo Medical RAG Pipeline"""
        self.collection_name = collection_name
        self.model_name = model_name
        self.embedding_model = None
        self.vector_store = None
        self.retriever = None
        self.llm_pipeline = None
        self._setup_pipeline()
    
    def _setup_pipeline(self) -> None:
        """Thiết lập các thành phần của pipeline"""
        try:
            # 1. Tải embedding model
            self.embedding_model = ModelManager.load_embedding_model()
            
            # 2. Khởi tạo vector store
            self.vector_store = VectorStore()
            if not self.vector_store.client:
                raise Exception("Không thể kết nối tới Vector Store")
            
            # 3. Thiết lập retriever
            self.retriever = self.vector_store.create_retriever(
                collection_name=self.collection_name,
                embedding_model=self.embedding_model,
                top_k=DEFAULT_TOP_K
            )
            
            # 4. Tải LLM
            llm_config = ModelManager.load_llm_model(model_name=self.model_name)
            if llm_config['type'] != 'groq':
                raise Exception(f"Lỗi tải LLM: {llm_config.get('message', 'Lỗi không xác định')}")
            
            self.llm_pipeline = ModelManager.create_llm_pipeline(llm_config)
            logger.info("✅ RAG Pipeline thiết lập thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi thiết lập pipeline: {e}")
            raise
    
    def _search_documents(self, query: str, limit: int = DEFAULT_TOP_K) -> List[Dict]:
        """Tìm kiếm tài liệu liên quan"""
        if not self.retriever:
            return []
        return self.retriever(query, limit=limit)
    
    def _generate_context_prompt(self, query: str, documents: List[Dict]) -> str:
        """Tạo prompt với context"""
        if not documents:
            context = "Không tìm thấy tài liệu liên quan."
        else:
            context_parts = []
            for i, doc in enumerate(documents, 1):
                content = doc.get('content', '')
                score = doc.get('score', 0)
                context_parts.append(f"[Tài liệu {i}] (Độ tương đồng: {score:.2f})\n{content}\n")
            context = "\n".join(context_parts)
        
        return f"""Bạn là một trợ lý y tế thông minh. Hãy trả lời câu hỏi dựa trên thông tin y tế được cung cấp.

THÔNG TIN Y TẾ:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
- Trả lời bằng tiếng Việt
- Dựa vào thông tin được cung cấp
- Nếu không có thông tin liên quan, hãy nói rõ
- Luôn khuyên bạn tham khảo bác sĩ cho các vấn đề nghiêm trọng
- Trả lời chi tiết và dễ hiểu

TRẢ LỜI:"""
    
    def query(self, question: str, max_tokens: int = DEFAULT_MAX_TOKENS, stream: bool = False) -> Dict:
        """Hàm chính để truy vấn RAG"""
        try:
            # 1. Tìm kiếm tài liệu
            documents = self._search_documents(question)
            
            # 2. Deduplicate sources by title
            unique_docs = {}
            for doc in documents:
                metadata = doc.get('metadata', {})
                title = metadata.get('title', metadata.get('name', ''))
                url = metadata.get('url', metadata.get('source', ''))
                
                # Tạo key để deduplicate
                if title.strip():
                    key = title.strip().lower()
                elif url.strip():
                    key = url.strip()
                else:
                    # Fallback nếu không có title hay url
                    key = f"doc_{len(unique_docs)}"
                
                # Chỉ giữ lại document có score cao nhất cho mỗi key
                if key not in unique_docs or doc.get('score', 0) > unique_docs[key].get('score', 0):
                    unique_docs[key] = doc
            
            # Filter docs theo threshold
            high_quality_docs = [doc for doc in unique_docs.values() if doc.get('score', 0) >= 0.6]
            
            if high_quality_docs:
                # Nếu có docs chất lượng cao (>= 0.6), chỉ hiển thị những docs này
                deduplicated_docs = sorted(high_quality_docs, key=lambda x: x.get('score', 0), reverse=True)[:10]
            else:
                # Nếu không có docs >= 0.6, hiển thị tất cả và filter frontend sẽ handle
                all_docs = list(unique_docs.values())
                deduplicated_docs = sorted(all_docs, key=lambda x: x.get('score', 0), reverse=True)[:10]
            
            # Tạo prompt với context
            prompt = self._generate_context_prompt(question, deduplicated_docs)
            
            # Sinh câu trả lời
            response = self.llm_pipeline(prompt, max_tokens=max_tokens, stream=stream)
            
            result = {
                'question': question,
                'sources': deduplicated_docs,
                'context_used': len(deduplicated_docs) > 0
            }
            
            if stream:
                result['answer_stream'] = response
            else:
                result['answer'] = response
                
            return result
            
        except Exception as e:
            logger.error(f"Lỗi truy vấn RAG: {e}")
            return {
                'question': question,
                'answer': f"Xin lỗi, đã có lỗi xảy ra: {str(e)}",
                'sources': [],
                'context_used': False
            }
    
    def get_stats(self) -> Dict:
        """Lấy thống kê của pipeline"""
        try:
            if not self.vector_store.client:
                return {'status': 'error', 'message': 'Vector Store chưa được kết nối'}
            
            collections = self.vector_store.client.get_collections().collections
            collection_info = None
            
            for coll in collections:
                if coll.name == self.collection_name:
                    collection_info = self.vector_store.client.get_collection(self.collection_name)
                    break
            
            if collection_info:
                return {
                    'status': 'active',
                    'collection_name': self.collection_name,
                    'vector_count': getattr(collection_info, 'points_count', 0),
                    'embedding_model': EMBEDDING_MODEL,
                    'llm_model': self.model_name,
                    'llm_provider': 'Groq API',
                    'vector_store': 'Qdrant Cloud'
                }
            
            return {
                'status': 'collection_not_found',
                'message': f'Không tìm thấy collection "{self.collection_name}"',
                'available_collections': [coll.name for coll in collections]
            }
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def cleanup(self) -> None:
        """Dọn dẹp tài nguyên"""
        if self.vector_store:
            self.vector_store.cleanup()
    
    def change_model(self, new_model_name: str) -> bool:
        """Thay đổi model LLM"""
        try:
            self.model_name = new_model_name
            llm_config = ModelManager.load_llm_model(model_name=new_model_name)
            if llm_config['type'] != 'groq':
                raise Exception(f"Lỗi tải LLM: {llm_config.get('message', 'Lỗi không xác định')}")
            
            self.llm_pipeline = ModelManager.create_llm_pipeline(llm_config)
            logger.info(f"✅ Đã chuyển sang model {new_model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi chuyển model: {e}")
            return False
    
    def __del__(self):
        """Destructor để dọn dẹp tài nguyên"""
        try:
            self.cleanup()
        except:
            pass

def create_pipeline(collection_name: str = DEFAULT_COLLECTION, model_name: Optional[str] = None) -> MedicalRAGPipeline:
    """Factory function để tạo RAG pipeline"""
    if model_name is None:
        model_name = DEFAULT_MODEL
    
    try:
        return MedicalRAGPipeline(
            collection_name=collection_name,
            model_name=model_name
        )
    except Exception as e:
        logger.error(f"Lỗi tạo pipeline: {e}")
        raise 