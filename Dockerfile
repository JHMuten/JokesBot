# Use lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY analytics.py .
COPY jokes.json .
COPY init_chroma.py .
COPY templates/ templates/

# Create directories for persistent data
RUN mkdir -p chroma_db

# Create analytics file if it doesn't exist
RUN echo "[]" > analytics.json

# Initialize ChromaDB with jokes
RUN python init_chroma.py

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
