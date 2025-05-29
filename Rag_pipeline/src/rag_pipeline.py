import os
import logging
from typing import List, Dict
from model_setup import load_llm_model, create_llm_pipeline, load_embedding_model
from vector_store import connect_to_qdrant, get_qdrant_retriever
import atexit

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global pipeline instance for singleton pattern
_global_pipeline = None

class MedicalRAGPipeline:
    def __init__(self, qdrant_storage_path="./qdrant_storage", collection_name="medical_data", model_name=None):
        """Initialize Medical RAG Pipeline"""
        self.collection_name = collection_name
        # Use relative path for better compatibility
        self.qdrant_storage_path = qdrant_storage_path
        self.model_name = model_name or 'llama-3.3-70b-versatile'
        
        # Initialize components
        self.embedding_model = None
        self.qdrant_client = None
        self.retriever = None
        self.llm_pipeline = None
        
        self._setup_pipeline()
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def _setup_pipeline(self):
        """Setup all pipeline components"""
        logger.info("🔄 Setting up Medical RAG Pipeline...")
        
        # 1. Load embedding model
        logger.info("📊 Loading embedding model...")
        self.embedding_model = load_embedding_model()
        
        # 2. Connect to Qdrant
        logger.info(f"🗄️ Connecting to Qdrant at: {self.qdrant_storage_path}")
        self.qdrant_client = connect_to_qdrant(self.qdrant_storage_path)
        
        if not self.qdrant_client:
            logger.warning("⚠️ Qdrant connection issue, but continuing...")
            # Don't raise exception, just log warning
        else:
            # 3. Setup retriever
            logger.info("🔍 Setting up retriever...")
            self.retriever = get_qdrant_retriever(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding_model=self.embedding_model,
                top_k=3
            )
        
        # 4. Load LLM
        logger.info(f"🤖 Loading LLM: {self.model_name}")
        llm_config = load_llm_model(model_name=self.model_name)
        if llm_config['type'] != 'groq':
            raise Exception(f"LLM loading failed: {llm_config.get('message', 'Unknown error')}")
        
        self.llm_pipeline = create_llm_pipeline(llm_config)
        
        logger.info("✅ RAG Pipeline setup completed!")
    
    def change_model(self, new_model_name: str):
        """Change the LLM model"""
        if new_model_name != self.model_name:
            logger.info(f"🔄 Changing model from {self.model_name} to {new_model_name}")
            self.model_name = new_model_name
            
            # Reload only the LLM part
            llm_config = load_llm_model(model_name=self.model_name)
            if llm_config['type'] == 'groq':
                self.llm_pipeline = create_llm_pipeline(llm_config)
                logger.info(f"✅ Model changed to {new_model_name}")
                return True
            else:
                logger.error(f"❌ Failed to change model: {llm_config.get('message')}")
                return False
        return True
    
    def search_documents(self, query: str, limit: int = 3) -> List[Dict]:
        """Search relevant documents"""
        if not self.retriever:
            return []
        
        results = self.retriever(query, limit=limit)
        return results
    
    def generate_context_prompt(self, query: str, documents: List[Dict]) -> str:
        """Generate context-aware prompt"""
        if not documents:
            context = "Không tìm thấy tài liệu liên quan."
        else:
            context_parts = []
            for i, doc in enumerate(documents, 1):
                content = doc.get('content', '')
                score = doc.get('score', 0)
                context_parts.append(f"[Tài liệu {i}] (Độ tương đồng: {score:.2f})\n{content}\n")
            
            context = "\n".join(context_parts)
        
        prompt = f"""Bạn là một trợ lý y tế thông minh. Hãy trả lời câu hỏi dựa trên thông tin y tế được cung cấp.

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
        
        return prompt
    
    def query(self, question: str, max_tokens: int = 1024, stream: bool = False) -> Dict:
        """Main RAG query function"""
        try:
            # 1. Search relevant documents
            logger.info(f"🔍 Searching for: {question}")
            documents = self.search_documents(question)
            
            # 2. Generate context prompt
            prompt = self.generate_context_prompt(question, documents)
            
            # 3. Generate response
            logger.info("🤖 Generating response...")
            response = self.llm_pipeline(prompt, max_tokens=max_tokens, stream=stream)
            
            if stream:
                # Return streaming response with context
                return {
                    'question': question,
                    'answer_stream': response,
                    'sources': documents,
                    'context_used': len(documents) > 0
                }
            else:
                # Regular response
                return {
                    'question': question,
                    'answer': response,
                    'sources': documents,
                    'context_used': len(documents) > 0
                }
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                'question': question,
                'answer': f"Xin lỗi, đã có lỗi xảy ra: {str(e)}",
                'sources': [],
                'context_used': False
            }
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics"""
        try:
            if not self.qdrant_client:
                return {
                    'status': 'error', 
                    'message': 'Qdrant client not connected. Check if qdrant_storage path exists.',
                    'qdrant_path': self.qdrant_storage_path
                }
            
            collections = self.qdrant_client.get_collections().collections
            collection_info = None
            
            for coll in collections:
                if coll.name == self.collection_name:
                    collection_info = self.qdrant_client.get_collection(self.collection_name)
                    break
            
            if collection_info:
                return {
                    'status': 'active',
                    'collection_name': self.collection_name,
                    'vector_count': collection_info.points_count,
                    'embedding_model': 'strongpear/M3-retriever-MEDICAL',
                    'llm_model': self.model_name
                }
            else:
                return {
                    'status': 'collection_not_found',
                    'message': f'Collection "{self.collection_name}" not found in Qdrant',
                    'available_collections': [coll.name for coll in collections]
                }
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def cleanup(self):
        """Cleanup resources properly"""
        try:
            if self.qdrant_client:
                logger.info("🧹 Cleaning up Qdrant connection...")
                self.qdrant_client.close()
                self.qdrant_client = None
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

# Convenience function
def create_rag_pipeline(qdrant_path="./qdrant_storage", model_name=None) -> MedicalRAGPipeline:
    """Create and return RAG pipeline instance with singleton pattern"""
    global _global_pipeline
    
    # Check if we can reuse existing pipeline
    if _global_pipeline is not None:
        try:
            # Test if existing pipeline is still working
            stats = _global_pipeline.get_stats()
            if stats['status'] == 'active':
                # Just change model if needed
                if model_name and model_name != _global_pipeline.model_name:
                    _global_pipeline.change_model(model_name)
                logger.info("♻️ Reusing existing RAG pipeline")
                return _global_pipeline
            else:
                # Cleanup broken pipeline
                _global_pipeline.cleanup()
                _global_pipeline = None
        except:
            _global_pipeline = None
    
    # Create new pipeline
    logger.info("🆕 Creating new RAG pipeline")
    _global_pipeline = MedicalRAGPipeline(qdrant_storage_path=qdrant_path, model_name=model_name)
    return _global_pipeline

if __name__ == "__main__":
    # Test the pipeline
    pipeline = create_rag_pipeline()
    
    # Test query
    test_question = "căng cơ đùi là gì"
    result = pipeline.query(test_question)
    
    print("=== TEST RAG PIPELINE ===")
    print(f"Câu hỏi: {result['question']}")
    print(f"Trả lời: {result['answer']}")
    print(f"Số tài liệu tìm thấy: {len(result['sources'])}")
    print(f"Có sử dụng context: {result['context_used']}")
    
    # Show detailed sources
    if result['sources']:
        print("\n=== SOURCES DETAILS ===")
        for i, source in enumerate(result['sources'], 1):
            metadata = source.get('metadata', {})
            print(f"\nSource {i}:")
            print(f"  Score: {source.get('score', 'N/A')}")
            print(f"  Title: {metadata.get('title', 'N/A')}")
            print(f"  URL: {metadata.get('url', 'N/A')}")
            print(f"  Content: {source.get('content', '')[:100]}...")
    
    # Show stats
    stats = pipeline.get_stats()
    print(f"\nThống kê: {stats}") 