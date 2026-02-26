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
COPY templates/ templates/
COPY startup.sh .

# Make startup script executable
RUN chmod +x startup.sh

# Create directories for persistent data
RUN mkdir -p chroma_db

# Create analytics file if it doesn't exist
RUN touch analytics.json && echo "[]" > analytics.json

# Pre-initialize ChromaDB with jokes (run once during build)
RUN python -c "import chromadb; import json; \
    client = chromadb.PersistentClient(path='./chroma_db'); \
    collection = client.get_or_create_collection(name='jokes'); \
    with open('jokes.json') as f: jokes = json.load(f); \
    if collection.count() == 0: \
        docs = [j.get('joke', '') if j.get('type')=='single' else f\"{j.get('setup','')} {j.get('delivery','')}\" for j in jokes]; \
        metas = [{'category': j.get('category','Unknown'), 'type': j.get('type','unknown'), 'id': str(j.get('id',i))} for i,j in enumerate(jokes)]; \
        ids = [f'joke_{i}' for i in range(len(jokes))]; \
        collection.add(documents=docs, metadatas=metas, ids=ids); \
        print(f'Initialized ChromaDB with {len(docs)} jokes')"

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run with startup script
CMD ["./startup.sh"]
