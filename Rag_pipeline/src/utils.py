import os 
import re 
import torch 


def get_hardware() -> str:
    """Get hardware available for inference.
    """
    hardware = "cpu"
    if torch.cuda.is_available():
        hardware = "cuda"
        print("Using CUDA for inference.")
    else:
        if torch.backends.mps.is_available():
            hardware = "mps"
            print("Using MPS for inference.")
    return hardware

def get_root_dir() -> str:
    """Get root working directory of the project.
    """
    project_root = os.getenv(
        "PROJECT_ROOT", 
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        )
    return project_root

def get_model_dir(model_name: str = None) -> str:
    """Get directory of the saved LLM model (deprecated - using Groq API instead)

    Args:
        model_name (str, optional): Model name for local storage.
        Note: This function is deprecated as we're using Groq API for LLM inference.

    Returns:
        str: Model directory path
    """
    if model_name is None:
        return os.path.join(get_root_dir(), "rag-pipeline/models/")
    model_dir = os.path.join(get_root_dir(), "rag-pipeline/models/" + model_name)
    return model_dir