# Dockerfile
FROM python:3.10-slim

# Avoid Python .pyc files and enable buffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Cloud Run listens on 8080
ENV PORT=8080

WORKDIR /app

# System deps (optional: remove if you don’t need them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (better cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Start the server (expects "app:app")
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8080"]
