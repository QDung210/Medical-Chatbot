import json
import time
import threading
from pydantic import BaseModel
from .model_setup import load_model
from fastapi import FastAPI, HTTPException
from .rag_pipeline import generate_answer_stream
from fastapi.responses import StreamingResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from .utils import (DEFAULT_MODEL, logger, tracer, 
                   REQUEST_COUNT, LATENCY, MODEL_LOAD_TIME, 
                   ERROR_COUNT, monitor_memory_usage)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ModelState:
    def __init__(self):
        self.llm_loaded = False 
        self.model = None

model_state = ModelState()
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
def load_llm(model_name=DEFAULT_MODEL):
    """Load the language model"""
    with tracer.start_as_current_span("load_llm") as span:
        span.set_attribute("model.name", model_name)
        start_time = time.time()
        try:
            logger.info(f"Attempting to load model: {model_name}")
            model_state.model = load_model(model_name, streaming=True)
            model_state.llm_loaded = True
            span.set_attribute("model.loaded", True)
            
            # Record model load time in Prometheus
            load_time = time.time() - start_time
            MODEL_LOAD_TIME.observe(load_time)
            
            logger.info(f"Model {model_name} loaded successfully in {load_time:.2f}s")
        except Exception as e:
            span.set_attribute("model.loaded", False)
            span.record_exception(e)
            ERROR_COUNT.labels(error_type="model_load").inc()
            logger.error(f"Error loading model {model_name}: {e}")
            model_state.llm_loaded = False
            raise HTTPException(status_code=500, detail=f"Failed to load model {model_name}")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting up FastAPI server...")
    
    # Start memory monitoring in background thread
    memory_thread = threading.Thread(target=monitor_memory_usage, daemon=True)
    memory_thread.start()
    logger.info("📊 Memory monitoring started")
    
    # Initialize database first
    try:
        from .database.postgres_memory import init_database
        init_database()
    except ImportError:
        from database.postgres_memory import init_database
        init_database()
    
    # Then load the model
    load_llm()

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint with PostgreSQL memory"""
    if not model_state.llm_loaded:
        logger.error("Model not loaded - rejecting chat request")
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Track request metrics
    REQUEST_COUNT.inc()
    start_time = time.time()
    
    try:
        logger.info(f"Processing chat request for session: {request.session_id}")
        logger.info(f"Message: {request.message[:50]}...")  # Log first 50 chars
        
        def generate():
            for chunk in generate_answer_stream(
                request.message, 
                model_state.model, 
                session_id=request.session_id
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
            
            # Record latency after streaming completes
            request_time = time.time() - start_time
            LATENCY.observe(request_time)
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        ERROR_COUNT.labels(error_type="chat_request").inc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

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