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

def get_model_dir(model_name: str = "google/gemma-3-4b-it") -> str:
    """Get directory of the saved LLM model

    Args:
        model_name (str, optional): Model name on [Hugging Face](https://huggingface.co/google/gemma-3-4b-it). 
        Defaults to "google/gemma-3-4b-it".

    Returns:
        str: _description_
    """
    model_dir = os.path.join(get_root_dir(), "rag-pipeline/models/" + model_name)
    return model_dir

