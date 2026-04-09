FROM python:3.12.7-slim

# Install system dependencies (cairo for pycairo/svglib, tesseract for OCR)
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    tesseract-ocr \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Default command (Railway overrides this with start command)
CMD ["celery", "-A", "docshift", "worker", "--loglevel=info", "--concurrency=1"]
