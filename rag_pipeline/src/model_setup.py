import os
import requests
from sentence_transformers import SentenceTransformer
from typing import Dict, Callable, Optional, Union
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
AVAILABLE_MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
EMBEDDING_MODEL = 'strongpear/M3-retriever-MEDICAL'

class ModelManager:
    @staticmethod
    def load_embedding_model() -> SentenceTransformer:
        """Load medical embedding model"""
        return SentenceTransformer(EMBEDDING_MODEL)

    @staticmethod
    def load_llm_model(model_name: Optional[str] = None) -> Dict:
        """Load LLM configuration"""
        if not GROQ_API_KEY:
            return {'type': 'error', 'message': 'GROQ_API_KEY not found'}
        
        model_name = model_name or AVAILABLE_MODELS[0]
        if model_name not in AVAILABLE_MODELS:
            return {
                'type': 'error',
                'message': f'Model {model_name} not available. Available models: {AVAILABLE_MODELS}'
            }
        
        return {
            'type': 'groq',
            'model_name': model_name,
            'api_key': GROQ_API_KEY,
            'api_url': GROQ_API_URL
        }

    @staticmethod
    def create_llm_pipeline(model_config: Dict) -> Callable[[str], str]:
        """Create text generation pipeline"""
        if model_config['type'] == 'groq':
            def generate(prompt: str) -> str:
                try:
                    response = requests.post(
                        model_config['api_url'],
                        headers={'Authorization': f'Bearer {model_config["api_key"]}'},
                        json={
                            'model': model_config['model_name'],
                            'messages': [{'role': 'user', 'content': prompt}],
                            'max_tokens': 1024,
                            'temperature': 0.3,
                            'top_p': 0.9,
                            'frequency_penalty': 0.5,
                            'presence_penalty': 0.5
                        },
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        return response.json()['choices'][0]['message']['content']
                    return f"API Error: {response.status_code}"
                        
                except Exception as e:
                    return f"Connection Error: {str(e)}"
            
            return generate
        
        def error_response(*args, **kwargs) -> str:
            return model_config.get('message', 'Model not available')
        
        return error_response
