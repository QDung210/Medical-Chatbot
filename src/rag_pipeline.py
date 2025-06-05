from langchain.prompts import PromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
import os 
import pickle
from pathlib import Path
from qdrant_client import QdrantClient
from src.model_setup import load_model
from dotenv import load_dotenv
from langchain.vectorstores import Qdrant
from src.utils import get_hardware, logger

load_dotenv()
DEFAULT_MODEL = "llama-3.1-8b-instant"

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / ".cache"
EMBEDDINGS_CACHE = CACHE_DIR / "embeddings.pkl"

# Cache documents để tránh retrieve lại
docs_cache = {}

def init_cache():
    """Khởi tạo cache directory"""
    CACHE_DIR.mkdir(exist_ok=True)
    logger.info(f"Cache directory: {CACHE_DIR}")

def load_embeddings():
    """Load embeddings với cache"""
    init_cache()
    
    if EMBEDDINGS_CACHE.exists():
        logger.info("Loading embeddings from cache...")
        try:
            with open(EMBEDDINGS_CACHE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Cache corrupted, rebuilding: {e}")
    
    logger.info("Creating new embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name="strongpear/M3-retriever-MEDICAL",
        model_kwargs=get_hardware()
    )
    
    # Cache embeddings
    try:
        with open(EMBEDDINGS_CACHE, 'wb') as f:
            pickle.dump(embeddings, f)
        logger.info("Embeddings cached successfully")
    except Exception as e:
        logger.warning(f"Failed to cache embeddings: {e}")
    
    return embeddings

def load_vectorstore():
    """Load vectorstore với cache"""
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    vectorstore = Qdrant(
        client=client,
        collection_name="medical_data",
        embeddings=embeddings
    )
    
    return vectorstore

# Load tất cả ngay khi import (startup time)
logger.info("Initializing RAG pipeline...")
embeddings = load_embeddings()
qdrant_vectorstore = load_vectorstore()
logger.info("RAG pipeline ready!")

# Setup prompt
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "Bạn là một trợ lý AI chuyên ngành y tế. Trả lời câu hỏi sau bằng tiếng Việt một cách đầy đủ và chi tiết.\n"
        "Nếu được thì hãy đưa ra nguyên nhân, triệu chứng, cách điều trị và các thông tin liên quan khác.\n"
        "Nếu không phải câu hỏi về y tế, hãy nói rằng bạn không thể giúp.\n"
        "Sau khi trả lời xong, hãy khuyên người hỏi nên tham khảo ý kiến bác sĩ.\n\n"
        "Ngữ cảnh:\n{context}\n\n"
        "Câu hỏi: {question}\n\n"
        "Trả lời:"
    )
)

def generate_answer(question: str, model=None) -> str:
    """Generate answer tối ưu chỉ 1 lần gọi Qdrant với score filtering"""
    if model is None:
        model = load_model(model_name=DEFAULT_MODEL)
    
    # Cache key cho documents
    cache_key = hash(question)
    
    if cache_key not in docs_cache:
        # Chỉ gọi Qdrant 1 lần duy nhất với score
        docs_with_scores = qdrant_vectorstore.similarity_search_with_score(question, k=10)
        # Filter theo score threshold
        filtered_docs = [doc for doc, score in docs_with_scores if score > 0.1]
        docs_cache[cache_key] = filtered_docs
    else:
        filtered_docs = docs_cache[cache_key]
    
    # Format context từ documents đã filter
    context = "\n".join([doc.page_content for doc in filtered_docs])
    
    # Format prompt trực tiếp
    formatted_prompt = prompt.format(context=context, question=question)
    
    # Gọi model trực tiếp
    response = model.invoke(formatted_prompt)
    
    return response.content if hasattr(response, 'content') else str(response)

if __name__ == "__main__":  
    question = "Căng cơ đùi là gì ?"
    answer = generate_answer(question)
    print(f"Question: {question}")
    print(f"Answer: {answer}")


