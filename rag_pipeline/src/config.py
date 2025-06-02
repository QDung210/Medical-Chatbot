import os
from dotenv import load_dotenv

# Cấu hình đường dẫn .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Cấu hình Qdrant
QDRANT_CLOUD_URL = os.getenv('QDRANT_CLOUD_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Cấu hình Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Danh sách model có sẵn trên Groq
AVAILABLE_MODELS = [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant'
]

# Cấu hình mặc định
DEFAULT_MODEL = 'llama-3.3-70b-versatile'
DEFAULT_COLLECTION = 'medical_data'
DEFAULT_TOP_K = 3
DEFAULT_MAX_TOKENS = 1024

# Cấu hình embedding model
EMBEDDING_MODEL = 'strongpear/M3-retriever-MEDICAL'
FALLBACK_EMBEDDING_MODEL = 'all-mpnet-base-v2' 