import logging 
import time 
from model_setup import load_model
from utils import (get_model_dir, logger, MODEL_LOAD_TIME) 


class ModelState:
    def __init__(self):
        """State holder for the local LLM
        """
        self.llm_loaded = False
        self.qa_pipelines = {}
        self.model = None
        
# LLM global variables
model_state = ModelState()

def load_llm(model_name="Qwen/Qwen2.5-0.5B-Instruct"):
    """Function to load LLM on startup.

    Args:
        model_name (str, optional): Model name on [Hugging Face](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct). 
        Defaults to "Qwen/Qwen2.5-0.5B-Instruct".
    """
    # Removed tracer.start_as_current_span - will add back later
    # with tracer.start_as_current_span("load_llm") as load_llm:
    
    start_time = time.time()
    
    try:
        # Loading LLM Model
        logger.info("🔄 Loading LLM ...")
        local_dir = get_model_dir(model_name)
        model_state.model = load_model(model_name=model_name, local_dir=local_dir)           
        MODEL_LOAD_TIME.observe(time.time() - start_time)
        model_state.llm_loaded = True
        logger.info("✅ LLM Model Loaded Successfully")
    except Exception as e:
        logger.error(f"❌ LLM Model Load Failed: {e}", exc_info=True)
        model_state.llm_loaded = False