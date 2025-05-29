import os
import requests
import logging
from sentence_transformers import SentenceTransformer
from utils import get_hardware, get_model_dir

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

def load_embedding_model():
    """Load medical embedding model"""
    try:
        return SentenceTransformer('strongpear/M3-retriever-MEDICAL')
    except Exception as e:
        logger.warning(f"Failed to load medical model: {e}")
        return SentenceTransformer('all-mpnet-base-v2')

def check_groq_connection(api_key=None):
    """Check Groq API connection"""
    if not api_key:
        api_key = os.getenv('GROQ_API_KEY')
    
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

def load_llm_model(api_key=None, model_name=None):
    """Load LLM model configuration"""
    if not api_key:
        api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        return {'type': 'error', 'message': 'GROQ_API_KEY not found'}
    
    # Default model if none specified
    if not model_name:
        model_name = 'llama-3.3-70b-versatile'
    
    # Available models on Groq
    available_models = [
        'llama-3.3-70b-versatile',
        'qwen-qwq-32b',
        'llama-3.1-8b-instant',
        'mixtral-8x7b-32768',
        'gemma2-9b-it'
    ]
    
    if model_name not in available_models:
        return {'type': 'error', 'message': f'Model {model_name} not available. Available: {available_models}'}
    
    if check_groq_connection(api_key):
        return {
            'type': 'groq',
            'model_name': model_name,
            'api_key': api_key,
            'api_url': 'https://api.groq.com/openai/v1/chat/completions'
        }
    
    return {'type': 'error', 'message': 'Cannot connect to Groq API'}

def create_llm_pipeline(model_config):
    """Create LLM generation pipeline"""
    
    if model_config['type'] == 'groq':
        def generate(prompt, max_tokens=1024, stream=False):
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
                    # Return streaming response
                    return response
                else:
                    # Regular non-streaming response
                    if response.status_code == 200:
                        result = response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        return f"API Error: {response.status_code}"
                        
            except Exception as e:
                return f"Connection Error: {str(e)}"
        
        return generate
    
    else:
        def error_response(prompt, max_tokens=1024, stream=False):
            return model_config.get('message', 'Model not available')
        
        return error_response

if __name__ == "__main__":
    # Test the Groq API configuration
    model_config = load_llm_model()
    if model_config['type'] == 'groq':
        pipeline = create_llm_pipeline(model_config)
        test_response = pipeline("Hello, this is a test message.")
        print("Test response:", test_response)
        print("Groq API configured successfully!")
    else:
        print("Error:", model_config['message'])