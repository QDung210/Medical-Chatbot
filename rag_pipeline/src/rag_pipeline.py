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
DEFAULT_MAX_TOKENS =512
EMBEDDING_MODEL = 'strongpear/M3-retriever-MEDICAL'

from .model_setup import ModelManager
from .vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalRAGPipeline:
    def __init__(self, collection_name: str = DEFAULT_COLLECTION, model_name: str = DEFAULT_MODEL):
        """Initialize RAG pipeline with basic setup"""
        self.collection_name = collection_name
        self.model_name = model_name
        
        # Setup components
        self.embedding_model = ModelManager.load_embedding_model()
        self.vector_store = VectorStore()
        self.retriever = self.vector_store.create_retriever(
            collection_name=self.collection_name,
            embedding_model=self.embedding_model,
            top_k=DEFAULT_TOP_K
        )
        self.llm_pipeline = ModelManager.create_llm_pipeline(
            ModelManager.load_llm_model(model_name=self.model_name)
        )

    def _deduplicate_docs(self, documents: List[Dict]) -> List[Dict]:
        """Simple deduplication based on title or URL"""
        unique_docs = {}
        for doc in documents:
            metadata = doc.get('metadata', {})
            key = metadata.get('title', metadata.get('url', f"doc_{len(unique_docs)}"))
            if key not in unique_docs or doc.get('score', 0) > unique_docs[key].get('score', 0):
                unique_docs[key] = doc
        return list(unique_docs.values())

    def _filter_docs(self, documents: List[Dict], threshold: float = 0.44) -> List[Dict]:
        """Filter documents by similarity score"""
        return [doc for doc in documents if doc.get('score', 0) >= threshold]

    def _create_prompt(self, question: str, documents: List[Dict]) -> str:
        """Create a detailed prompt with context"""
        # Base prompt template
        base_prompt = """Bạn là một trợ lý y tế thông minh, thân thiện và đáng tin cậy. Nhiệm vụ của bạn là giúp người dùng hiểu rõ về các vấn đề sức khỏe một cách dễ hiểu, đầy đủ và chính xác.

Hãy thực hiện các yêu cầu sau:
1. Trả lời câu hỏi một cách chi tiết, dễ hiểu với người không có chuyên môn y tế
2. Nếu có nhiều khả năng xảy ra, hãy nêu từng khả năng cùng giải thích và khuyến nghị tương ứng
3. Cung cấp thông tin về:
   - Định nghĩa/giải thích rõ ràng
   - Các triệu chứng/biểu hiện (nếu có), không có thì thôi, bỏ qua cái này.
   - Nguyên nhân (nếu có), không có thì thôi, bỏ qua cái này.
   - Cách điều trị/phòng ngừa (nếu có), không có thì thôi, bỏ qua cái này.
   - Khi nào cần gặp bác sĩ (nếu có), không có thì thôi, bỏ qua cái này.
   - Lời khuyên hữu ích
4. Kết thúc bằng lời khuyên phù hợp hoặc khuyến khích người dùng tham khảo bác sĩ nếu cần
5. Nếu không phải là câu hỏi liên quan đến y tế thì không cần trả lời. """

        # Add context if available
        if documents:
            context = "\n".join([f"- {doc.get('content', '')}" for doc in documents])
            base_prompt += f"\n\nTHÔNG TIN:\n{context}"

        # Add question
        base_prompt += f"\n\nCÂU HỎI:\n{question}\n\nCâu trả lời:"
        
        return base_prompt

    def query(self, question: str) -> Dict:
        """Main query function with simplified flow"""
        # 1. Get relevant documents
        documents = self.retriever(question)
        
        # 2. Deduplicate and filter documents
        unique_docs = self._deduplicate_docs(documents)
        filtered_docs = self._filter_docs(unique_docs)
        
        # 3. Create prompt and get response
        prompt = self._create_prompt(question, filtered_docs)
        response = self.llm_pipeline(prompt)
        
        return {
            'question': question,
            'answer': response,
            'sources': filtered_docs
        }

    def cleanup(self):
        """Cleanup resources"""
        if self.vector_store:
            self.vector_store.cleanup()

def create_pipeline(collection_name: str = DEFAULT_COLLECTION, model_name: Optional[str] = None) -> MedicalRAGPipeline:
    """Factory function to create RAG pipeline"""
    if model_name is None:
        model_name = DEFAULT_MODEL
    
    try:
        return MedicalRAGPipeline(
            collection_name=collection_name,
            model_name=model_name
        )
    except Exception as e:
        logger.error(f"Error creating pipeline: {e}")
        raise 