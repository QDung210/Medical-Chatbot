import logging
import os
from pathlib import Path
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from prometheus_client import Counter, Histogram, Gauge
import psutil
import threading
import time

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "rag-pipeline-service"})
    )
)
jaeger_exporter = JaegerExporter(
    collector_endpoint="http://jaeger:14268/api/traces"
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

tracer = trace.get_tracer("rag-pipeline", "0.1.0")



# Prometheus metrics definitions
REQUEST_COUNT = Counter("chatbot_requests_total", "Total requests to chatbot")
LATENCY = Histogram("chatbot_request_latency_seconds", "Chatbot request latency")
MODEL_LOAD_TIME = Histogram("chatbot_model_load_time_seconds", "Time to load the LLM model")
VECTOR_SEARCH_TIME = Histogram("chatbot_vector_search_seconds", "Vector search latency")
MEMORY_USAGE = Gauge("chatbot_memory_usage_bytes", "Memory usage in bytes")
ERROR_COUNT = Counter("chatbot_errors_total", "Total number of errors", ["error_type"])

# Memory monitoring function
def monitor_memory_usage():
    """Monitor memory usage continuously"""
    while True:
        try:
            process = psutil.Process()
            memory_bytes = process.memory_info().rss
            MEMORY_USAGE.set(memory_bytes)
            time.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Error monitoring memory: {e}")
            time.sleep(30)  # Wait longer if error

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "llama-3.1-8b-instant"
COLLECTION = "medical_data"
CACHE_DIR = Path(__file__).parent.parent.parent / ".cache"
EMBEDDINGS_MODEL = CACHE_DIR / "model"

def download_model_if_needed():
    """
    Tải về embedding model nếu thư mục .cache/model chưa tồn tại
    """
    try:
        # Kiểm tra xem thư mục .cache có tồn tại không
        if not CACHE_DIR.exists():
            logger.info(f"Tạo thư mục .cache tại: {CACHE_DIR}")
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Kiểm tra xem model đã được tải về chưa
        if not EMBEDDINGS_MODEL.exists() or not any(EMBEDDINGS_MODEL.iterdir()):
            logger.info("Thư mục model chưa tồn tại hoặc rỗng. Đang tải embedding model...")
            logger.info("Quá trình này có thể mất vài phút...")
            EMBEDDINGS_MODEL.mkdir(parents=True, exist_ok=True)
            model_name = "strongpear/M3-retriever-MEDICAL" 
            temp_model = SentenceTransformer(model_name)
            
            # Lưu model vào thư mục cache
            temp_model.save(str(EMBEDDINGS_MODEL))
            logger.info(f"Đã tải và lưu model tại: {EMBEDDINGS_MODEL}")
            
        else:
            logger.info(f"Model đã tồn tại tại: {EMBEDDINGS_MODEL}")
            
    except Exception as e:
        logger.error(f"Lỗi khi tải model: {e}")
        raise

class Resources:
    def __init__(self):
        self.client = None
        self.embedder = None
        self._init_resources()
    
    def _init_resources(self):
        """Initialize Qdrant client and embedder"""
        try:
            logger.info("Khởi tạo Qdrant client và embedder...")
            
            # Đảm bảo model đã được tải về
            download_model_if_needed()
            
            # Initialize Qdrant client
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            self.client = QdrantClient(url=qdrant_url)
            
            # Initialize embedder
            self.embedder = SentenceTransformer(str(EMBEDDINGS_MODEL))
            
            logger.info("Khởi tạo resources thành công")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo resources: {e}")
            raise

# Global resources instance
resources = Resources()

def get_hardware():
    """Get hardware info"""
    return "cpu" 
    # Uncomment chỗ này nếu có GPU
    # import torch
    # if torch.cuda.is_available():
    #     return "cuda"
    # else:
    #     return "cpu" 