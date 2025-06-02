import uvicorn
import logging
import os
import subprocess
import platform
import time
import socket

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .rag_pipeline import MedicalRAGPipeline

# Configuration
DEFAULT_MODEL = 'llama-3.3-70b-versatile'
DEFAULT_COLLECTION = 'medical_data'
AVAILABLE_MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
API_HOST = "127.0.0.1"
API_PORT = 8000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def kill_port(port: int):
    """Kill any process using the specified port"""
    try:
        if platform.system() == "Windows":
            # Find and kill all processes using the port
            result = subprocess.run(
                ["netstat", "-ano"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            killed_any = False
            for line in result.stdout.split('\n'):
                if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid != "0":  # Skip system processes
                            try:
                                subprocess.run(["taskkill", "/PID", pid, "/F"], 
                                             capture_output=True, check=False)
                                logger.info(f"🔧 Đã kill process {pid} trên port {port}")
                                killed_any = True
                            except:
                                pass
            
            # Wait a bit for cleanup if we killed something
            if killed_any:
                time.sleep(2)
                
        else:
            # Unix/Linux/Mac
            result = subprocess.run(f"lsof -ti:{port}", 
                                  shell=True, capture_output=True, text=True, check=False)
            if result.stdout.strip():
                subprocess.run(f"lsof -ti:{port} | xargs kill -9", 
                             shell=True, capture_output=True, check=False)
                logger.info(f"🔧 Đã kill process trên port {port}")
                time.sleep(2)
            
    except Exception as e:
        logger.warning(f"⚠️ Không thể kill port {port}: {e}")

def find_free_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    raise Exception(f"Không tìm thấy port trống từ {start_port} đến {start_port + max_attempts}")

# FastAPI app
app = FastAPI(
    title="Medical RAG API",
    description="API cho hệ thống Trợ lý Y tế AI",
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
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False

class QueryResponse(BaseModel):
    question: str
    answer: Optional[str] = None
    sources: list
    context_used: bool
    status: str = "success"

class ModelChangeRequest(BaseModel):
    model_name: str

@app.on_event("startup")
async def startup_event():
    global pipeline
    try:
        # Kill any existing process on the port
        kill_port(API_PORT)
        
        logger.info("🔄 Khởi tạo RAG Pipeline...")
        from .rag_pipeline import create_pipeline
        pipeline = create_pipeline(
            collection_name=DEFAULT_COLLECTION,
            model_name=DEFAULT_MODEL
        )
        logger.info("✅ RAG Pipeline sẵn sàng!")
    except Exception as e:
        logger.error(f"❌ Lỗi khởi tạo: {str(e)}")
        pipeline = None

@app.on_event("shutdown")
async def shutdown_event():
    global pipeline
    if pipeline:
        try:
            pipeline.cleanup()
        except:
            pass

@app.get("/")
async def root():
    return {"message": "Medical RAG API đang hoạt động", "status": "active"}

@app.get("/health")
async def health_check():
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")
    
    stats = pipeline.get_stats()
    if stats.get('status') != 'active':
        raise HTTPException(status_code=503, detail=f"Pipeline lỗi: {stats.get('message')}")
    
    return {"status": "healthy", "pipeline_stats": stats}

@app.post("/query", response_model=QueryResponse)
async def query_pipeline(request: QueryRequest):
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")
    
    try:
        result = pipeline.query(
            question=request.question,
            max_tokens=request.max_tokens,
            stream=False
        )
        
        return QueryResponse(
            question=result['question'],
            answer=result.get('answer', 'Không có phản hồi'),
            sources=result['sources'],
            context_used=result['context_used']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

@app.get("/stats")
async def get_stats():
    if not pipeline:
        return {"status": "error", "message": "Pipeline chưa khởi tạo"}
    
    try:
        return pipeline.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thống kê: {str(e)}")

@app.post("/change-model")
async def change_model(request: ModelChangeRequest):
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")
    
    if request.model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model không hỗ trợ: {AVAILABLE_MODELS}")
    
    try:
        success = pipeline.change_model(request.model_name)
        if success:
            return {"status": "success", "message": f"Đã chuyển sang {request.model_name}"}
        else:
            raise HTTPException(status_code=500, detail="Không thể chuyển model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi chuyển model: {str(e)}")

@app.get("/models")
async def get_available_models():
    return {"available_models": AVAILABLE_MODELS, "default_model": DEFAULT_MODEL}

def start_server():
    """Start the FastAPI server"""
    # Try to kill existing processes on default port
    kill_port(API_PORT)
    
    # Find a free port
    try:
        free_port = find_free_port(API_PORT)
        if free_port != API_PORT:
            logger.warning(f"⚠️ Port {API_PORT} busy, sử dụng port {free_port}")
        
        logger.info(f"🚀 Khởi động Medical RAG API: http://{API_HOST}:{free_port}")
        uvicorn.run("rag_pipeline.src.main:app", host=API_HOST, port=free_port, reload=False)
        
    except Exception as e:
        logger.error(f"❌ Không thể start server: {e}")
        raise

if __name__ == "__main__":
    start_server() 