FROM python:3.12.7-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    tesseract-ocr \
    tesseract-ocr-eng \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
WORKDIR /app

# Install the rest of the Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Default command (Start Web Server)
CMD ["gunicorn", "docshift.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
