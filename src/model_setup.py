import os 
import logging 
from langchain_groq import ChatGroq
from src.utils import DEFAULT_MODEL
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_model(model_name: str) -> any:
    try: 
        model = ChatGroq(
            model = model_name,
            temperature = 0.1,
            max_tokens = 512,
            timeout=30,
            api_key=os.getenv("GROQ_API_KEY")
        )
        return model
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        raise RuntimeError(f"Failed to load model {model_name}") from e
    
if __name__ =="__main__":
    model = load_model(model_name=DEFAULT_MODEL)
    print("Model loaded successfully")
