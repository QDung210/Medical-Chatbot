from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from .rag_pipeline import generate_answer_stream
from .model_setup import load_model
from .utils import DEFAULT_MODEL, logger


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ModelState:
    def __init__(self):
        self.llm_loaded = False 
        self.model = None

model_state = ModelState()
app = FastAPI()

def load_llm(model_name=DEFAULT_MODEL):
    """Load the language model"""
    try:
        logger.info(f"Attempting to load model: {model_name}")
        model_state.model = load_model(model_name, streaming=True)
        model_state.llm_loaded = True
        logger.info(f"Model {model_name} loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        model_state.llm_loaded = False
        raise HTTPException(status_code=500, detail=f"Failed to load model {model_name}")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting up FastAPI server...")
    load_llm()

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint with PostgreSQL memory"""
    if not model_state.llm_loaded:
        logger.error("Model not loaded - rejecting chat request")
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        logger.info(f"Processing chat request for session: {request.session_id}")
        def generate():
            for chunk in generate_answer_stream(
                request.message, 
                model_state.model, 
                session_id=request.session_id
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/chat/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history for a session"""
    try:
        # Import here to avoid circular imports
        try:
            from .database.postgres_memory import get_by_session_id
        except ImportError:
            from database.postgres_memory import get_by_session_id
        
        # Get the memory object and clear it
        memory = get_by_session_id(session_id)
        memory.clear()
        
        return {"message": f"Conversation {session_id} cleared"}
    except Exception as e:
        logger.error(f"Error clearing conversation {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear conversation")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if model_state.llm_loaded else "unhealthy",
        "model_loaded": model_state.llm_loaded,
        "model_name": DEFAULT_MODEL
    }

if __name__ == "__main__":
    import uvicorn 
    import argparse

    parser = argparse.ArgumentParser(description="Start the FastAPI server")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model to use for the chat")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the FastAPI server on")
    args = parser.parse_args()

    # Load the model 
    load_llm(model_name=args.model)
    
    # Start the FastAPI server  
    logger.info(f"You can now access the Swagger UI at http://localhost:{args.port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=args.port) 