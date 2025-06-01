import os
import requests
import logging
from sentence_transformers import SentenceTransformer
from typing import Dict, Callable, Optional, Union
from rag_pipeline.src.utils import HardwareUtils
from rag_pipeline.src.config import (
    GROQ_API_KEY, GROQ_API_URL, AVAILABLE_MODELS,
    EMBEDDING_MODEL, FALLBACK_EMBEDDING_MODEL
)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env file in the rag_pipeline directory
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
except ImportError:
    print("python-dotenv not installed. Using system environment variables only.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelManager:
    @staticmethod
    def load_embedding_model() -> SentenceTransformer:
        """Tải model embedding y tế"""
        try:
            # Chỉ lấy device, không set cache directory
            device = HardwareUtils.get_device()
            logger.info(f"Tải model embedding {EMBEDDING_MODEL} trên {device}")
            
            model = SentenceTransformer(
                EMBEDDING_MODEL,
                device=device
            )
            return model
            
        except Exception as e:
            logger.warning(f"Không thể tải model y tế: {e}")
            logger.info(f"Tải model dự phòng {FALLBACK_EMBEDDING_MODEL}")
            return SentenceTransformer(
                FALLBACK_EMBEDDING_MODEL,
                device=device
            )

    @staticmethod
    def check_groq_connection(api_key: Optional[str] = None) -> bool:
        """Kiểm tra kết nối tới Groq API"""
        api_key = api_key or GROQ_API_KEY
        if not api_key:
            return False
        
        try:
            response = requests.get(
                'https://api.groq.com/openai/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def load_llm_model(
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict:
        """Tải cấu hình LLM model"""
        api_key = api_key or GROQ_API_KEY
        if not api_key:
            return {'type': 'error', 'message': 'GROQ_API_KEY không tìm thấy'}
        
        model_name = model_name or AVAILABLE_MODELS[0]
        if model_name not in AVAILABLE_MODELS:
            return {
                'type': 'error',
                'message': f'Model {model_name} không có sẵn. Danh sách model: {AVAILABLE_MODELS}'
            }
        
        if ModelManager.check_groq_connection(api_key):
            return {
                'type': 'groq',
                'model_name': model_name,
                'api_key': api_key,
                'api_url': GROQ_API_URL
            }
        
        return {'type': 'error', 'message': 'Không thể kết nối tới Groq API'}

    @staticmethod
    def create_llm_pipeline(
        model_config: Dict
    ) -> Callable[[str, int, bool], Union[str, requests.Response]]:
        """Tạo pipeline sinh văn bản"""
        
        if model_config['type'] == 'groq':
            def generate(
                prompt: str,
                max_tokens: int = 1024,
                stream: bool = False
            ) -> Union[str, requests.Response]:
                try:
                    response = requests.post(
                        model_config['api_url'],
                        headers={'Authorization': f'Bearer {model_config["api_key"]}'},
                        json={
                            'model': model_config['model_name'],
                            'messages': [{'role': 'user', 'content': prompt}],
                            'max_tokens': max_tokens,
                            'temperature': 0.7,
                            'stream': stream
                        },
                        timeout=60,
                        stream=stream
                    )
                    
                    if stream:
                        return response
                    
                    if response.status_code == 200:
                        return response.json()['choices'][0]['message']['content']
                    return f"Lỗi API: {response.status_code}"
                        
                except Exception as e:
                    return f"Lỗi kết nối: {str(e)}"
            
            return generate
        
        def error_response(*args, **kwargs) -> str:
            return model_config.get('message', 'Model không khả dụng')
        
        return error_response
