FROM python:3.10 as builder

WORKDIR /app

RUN pip install --user --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch>=2.0.0+cpu
    
COPY rag_pipeline/requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /root/.local /root/.local

COPY rag_pipeline/ ./rag_pipeline/
COPY .env .env

ENV PATH=/root/.local/bin:$PATH

RUN mkdir -p /app/.cache/model

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uvicorn", "rag_pipeline.src.main:app", "--host", "0.0.0.0", "--port", "8000"]