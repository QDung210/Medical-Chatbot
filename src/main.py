import os
import shutil 
import time 
import threading
from fastapi import FastAPI, HTTPException, Response 
from pydantic import BaseModel
from langchain_groq import ChatGroq 
from src.model_setup import load_model
from src.rag_pipeline import generate_answer
from src.utils import (DEFAULT_MODEL, AVAILABLE_MODELS, logger, validate_model_name, get_model_info)

class ChatRequest(BaseModel):
    messages: str

class ChangeModelRequest(BaseModel):
    model_name: str

class ModelState:
    def __init__(self):
        self.llm_loaded = False 
        self.qa_pipeline = {}
        self.model = None 
        self.current_model = None  

model_state = ModelState()

app = FastAPI()

def load_llm(model_name=DEFAULT_MODEL):
    try:
        # Force import và init RAG pipeline trước
        from src.rag_pipeline import embeddings, qdrant_vectorstore
        logger.info("RAG pipeline components loaded")
        
        model_state.model = load_model(model_name)
        model_state.llm_loaded = True
        model_state.current_model = model_name  
        logger.info(f"Model {model_name} loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load model {model_name}")
    
@app.get("/health")
async def health_check(response: Response):
    health_status = {"status": "healthy"}

    if not model_state.llm_loaded:
        health_status["status"] = "unhealthy"
        health_status["message"] = "Model not loaded"
        response.status_code = 503
    return health_status

@app.post("/api/chat", description="Chat with the model")
async def chat_endpoint(request: ChatRequest):
    if not model_state.llm_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        response = generate_answer(request.messages, model_state.model)
        return {"answer": response}
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/available_models", description="Get list of available models")
def get_available_models():
    model_info = get_model_info()
    model_info["current_model"] = model_state.current_model
    return model_info

@app.post("/api/change_model", description="Change the current model")
def change_model(request: ChangeModelRequest):
    if not validate_model_name(request.model_name):
        raise HTTPException(
            status_code=400, 
            detail=f"Model {request.model_name} not available. Available models: {AVAILABLE_MODELS}"
        )
    
    try:
        load_llm(request.model_name)
        return {
            "message": f"Model successfully changed to {request.model_name}",
            "previous_model": model_state.current_model if hasattr(model_state, 'current_model') else None,
            "current_model": request.model_name
        }
    except Exception as e:
        logger.error(f"Error changing model to {request.model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to change model to {request.model_name}")

@app.get("/api/current_model", description="Get current model information")
def get_current_model():
    if not model_state.llm_loaded:
        return {"current_model": None, "status": "No model loaded"}
    
    return {
        "current_model": model_state.current_model,
        "status": "Model loaded",
        "available_models": AVAILABLE_MODELS
    }

if __name__ == "__main__":
    import uvicorn 
    import argparse

    parser = argparse.ArgumentParser(description="Start the FastAPI server")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, choices=AVAILABLE_MODELS, help="Model to use for the chat")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the FastAPI server on")
    args = parser.parse_args()

    # Load the model 
    load_llm(model_name=args.model)
    # Start the FastAPI server  
    logger.info(f"You can now access the Swagger UI at http://localhost:{args.port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=args.port)