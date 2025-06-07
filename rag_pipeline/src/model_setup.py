from langchain_groq import ChatGroq
from .utils import logger
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
load_dotenv(env_file)

def load_model(model_name="llama-3.1-8b-instant", streaming=True):
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error(f"GROQ_API_KEY not found. Checked .env file at: {env_file}")
            logger.error(f"Available env vars: {[k for k in os.environ.keys() if 'GROQ' in k]}")
            raise ValueError("GROQ_API_KEY not found in environment. Please add GROQ_API_KEY=your_key to .env file")
        
        model = ChatGroq(
            model=model_name,
            groq_api_key=api_key,
            max_tokens=1024,
            streaming=streaming,
            temperature=0.1,
        )
        
        logger.info(f"Streaming model {model_name} loaded successfully")
        return model
        
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        raise 