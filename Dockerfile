# JARVIS.AGI — API server image
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    ffmpeg \
    tesseract-ocr \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY jarvis/ ./jarvis/
COPY config/ ./config/

# Create data directories
RUN mkdir -p .jarvis/chroma .jarvis/knowledge .jarvis/plugins

# Expose FastAPI port
EXPOSE 8000

# Run the API server
CMD ["python", "-m", "jarvis", "serve", "--host", "0.0.0.0", "--port", "8000"]
