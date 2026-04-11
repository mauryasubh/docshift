FROM python:3.12.7-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    tesseract-ocr \
    tesseract-ocr-eng \
    gcc \
    && rm -rf /var/lib/apt/lists/*

ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

WORKDIR /app

# IMPORTANT: Install CPU-only PyTorch first!
# This prevents pip from downloading 2.5GB+ of NVIDIA CUDA GPU drivers
# which causes the Railway build to time out.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Default command
CMD ["celery", "-A", "docshift", "worker", "--loglevel=info", "--concurrency=1"]
