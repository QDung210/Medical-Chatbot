import torch 
import logging 
DEFAULT_MODEL = "llama-3.1-8b-instant"
AVAILABLE_MODELS = ["llama-3.1-8b-instant","llama-guard-3-8b"]


def get_hardware() -> dict:
    """Get the hardware configuration as a dictionary"""
    if torch.cuda.is_available():
        return {"device": "cuda"}
    elif torch.backends.mps.is_available():
        return {"device": "mps"}
    else:
        return {"device": "cpu"}

def validate_model_name(model_name: str) -> bool:
    """Validate if the model name is in available models list"""
    return model_name in AVAILABLE_MODELS

def get_model_info() -> dict:
    """Get information about available models and default model"""
    return {
        "available_models": AVAILABLE_MODELS,
        "default_model": DEFAULT_MODEL,
        "total_models": len(AVAILABLE_MODELS)
    }

# Initialize logger 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
        