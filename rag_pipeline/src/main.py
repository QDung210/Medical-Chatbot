import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict

from .rag_pipeline import MedicalRAGPipeline, create_pipeline

# Configuration
DEFAULT_MODEL = 'llama-3.3-70b-versatile'
DEFAULT_COLLECTION = 'medical_data'
AVAILABLE_MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
API_HOST = "127.0.0.1"
API_PORT = 8000

# FastAPI app
app = FastAPI(
    title="Medical RAG API",
    description="Medical Assistant AI API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline
pipeline: Optional[MedicalRAGPipeline] = None

# Pydantic models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict]

class ModelChangeRequest(BaseModel):
    model_name: str

@app.on_event("startup")
async def startup_event():
    global pipeline
    try:
        pipeline = create_pipeline(
            collection_name=DEFAULT_COLLECTION,
            model_name=DEFAULT_MODEL
        )
    except Exception as e:
        pipeline = None

@app.on_event("shutdown")
async def shutdown_event():
    global pipeline
    if pipeline:
        pipeline.cleanup()

@app.get("/")
async def root():
    return {"message": "Medical RAG API is running", "status": "active"}

@app.get("/health")
async def health_check():
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not ready")
    return {"status": "healthy"}

@app.post("/query", response_model=QueryResponse)
async def query_pipeline(request: QueryRequest):
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not ready")
    
    try:
        result = pipeline.query(question=request.question)
        return QueryResponse(
            question=result['question'],
            answer=result['answer'],
            sources=result['sources']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/change-model")
async def change_model(request: ModelChangeRequest):
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not ready")
    
    if request.model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model not supported: {AVAILABLE_MODELS}")
    
    try:
        pipeline = create_pipeline(
            collection_name=DEFAULT_COLLECTION,
            model_name=request.model_name
        )
        return {"status": "success", "message": f"Switched to {request.model_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def get_available_models():
    return {"available_models": AVAILABLE_MODELS, "default_model": DEFAULT_MODEL}

@app.get("/stats")
async def get_stats():
    global pipeline
    if not pipeline:
        return {"status": "error", "message": "Pipeline not initialized"}
    return {"status": "active", "model": pipeline.model_name}

def start_server():
    """Start the FastAPI server"""
    uvicorn.run("rag_pipeline.src.main:app", host=API_HOST, port=API_PORT, reload=False)

if __name__ == "__main__":
    start_server() 