import os
import logging
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM
from utils import get_hardware, get_model_dir

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_model(model_name: str, local_dir: str) -> any:
    """Setup local LLM model for inference.

    Args:
        model_name (str): Path to download the model from Hugging Face Hub.
        local_dir (str): Local directory to save the model.
    """
    # Ensure the directory exists
    os.makedirs(local_dir, exist_ok=True)
    
    if not os.path.exists(os.path.join(local_dir, "config.json")):
        logger.info(f"Model not found locally, downloading to {local_dir}...")
        snapshot_download(repo_id=model_name, local_dir=local_dir)
        logger.info("Model downloaded!")
    else:
        logger.info(f"Model already exists in {local_dir}, skipping download.")
    
    # Get hardware
    hardware = get_hardware()
    
    logger.info(f"Loading model from {local_dir} on {hardware}...")
    model = AutoModelForCausalLM.from_pretrained(
        pretrained_model_name_or_path=local_dir,
        device_map=hardware
        )    

    return model

if __name__ == "__main__":
    model = load_model(
        model_name="google/gemma-3-4b-it",
        local_dir=get_model_dir()
    )
    print("model:", model)
    print("Model loaded successfully!")