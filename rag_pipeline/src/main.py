import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List

from .rag_pipeline import create_pipeline
from .config import DEFAULT_MODEL, DEFAULT_COLLECTION

app = FastAPI(title="Medical Chatbot API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo RAG Pipeline
pipeline = create_pipeline()

class QueryRequest(BaseModel):
    question: str
    max_tokens: int = 1024
    stream: bool = False

class ModelChangeRequest(BaseModel):
    model_name: str

@app.get("/health")
async def health_check():
    stats = pipeline.get_stats()
    if stats['status'] == 'active':
        return {"status": "healthy"}
    return {"status": "unhealthy", "detail": stats.get('message', 'Unknown error')}

@app.get("/stats")
async def get_stats():
    return pipeline.get_stats()

@app.post("/api/query")
async def query(request: QueryRequest):
    try:
        result = pipeline.query(
            question=request.question,
            max_tokens=request.max_tokens,
            stream=request.stream
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/change_model")
async def change_model(request: ModelChangeRequest):
    try:
        global pipeline
        pipeline = create_pipeline(model_name=request.model_name)
        return {"status": "success", "model": request.model_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    """Run the FastAPI server"""
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    run_server()