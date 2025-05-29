import os
import sys
# Add the parent directory and src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from model_setup import check_groq_connection, load_llm_model, create_llm_pipeline  # type: ignore

def test_groq_setup():
    """Test Groq API setup"""
    print("Testing Groq API Setup...")
    print("="*50)
    
    # Check API key
    api_key = os.getenv('GROQ_API_KEY')
    if api_key:
        print(f"API Key found: {api_key[:10]}...{api_key[-10:]}")
    else:
        print("No API Key found!")
        return False
    
    # Test connection
    print("\nTesting Groq connection...")
    connection_ok = check_groq_connection(api_key)
    
    if connection_ok:
        print("Groq API connection successful!")
        
        # Test model loading
        print("\nLoading Llama 4 model...")
        model_config = load_llm_model(api_key)
        
        if model_config['type'] == 'groq':
            print(f"Model loaded: {model_config['model_name']}")
            
            # Test generation
            print("\nTesting text generation...")
            llm_pipeline = create_llm_pipeline(model_config)
            
            test_prompt = "Xin chào! Bạn có thể giúp tôi về vấn đề y tế không?"
            response = llm_pipeline(test_prompt, max_tokens=100)
            
            print(f"Test prompt: {test_prompt}")
            print(f"Response: {response}")
            print("\nGroq setup hoàn tất!")
            return True
        else:
            print(f"Model loading failed: {model_config.get('message', 'Unknown error')}")
            return False
    else:
        print("Groq API connection failed!")
        return False

if __name__ == "__main__":
    success = test_groq_setup()
    if success:
        print("\nGroq API sẵn sàng sử dụng!")
    else:
        print("\nGroq setup thất bại. Vui lòng kiểm tra lại!")