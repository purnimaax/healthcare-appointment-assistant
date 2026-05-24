FROM python:3.12-slim

# System deps for ChromaDB / sqlite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist runtime data outside the image at /data via volume
ENV SQLITE_DB_PATH=/data/app.db \
    CHECKPOINT_DB_PATH=/data/checkpoints.db \
    CHROMA_PERSIST_DIR=/data/chroma \
    UPLOAD_DIR=/data/uploads
RUN mkdir -p /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
