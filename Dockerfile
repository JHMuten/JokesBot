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

# Create directories for persistent data
RUN mkdir -p chroma_db

# Create analytics file if it doesn't exist
RUN echo "[]" > analytics.json

# Create initialization script
RUN echo 'import chromadb\n\
import json\n\
\n\
client = chromadb.PersistentClient(path="./chroma_db")\n\
collection = client.get_or_create_collection(name="jokes")\n\
\n\
if collection.count() == 0:\n\
    with open("jokes.json") as f:\n\
        jokes = json.load(f)\n\
    \n\
    docs = []\n\
    metas = []\n\
    ids = []\n\
    \n\
    for i, joke in enumerate(jokes):\n\
        if joke.get("type") == "single":\n\
            joke_text = joke.get("joke", "")\n\
        else:\n\
            joke_text = f"{joke.get(\"setup\", \"\")} {joke.get(\"delivery\", \"\")}"\n\
        \n\
        docs.append(joke_text)\n\
        metas.append({\n\
            "category": joke.get("category", "Unknown"),\n\
            "type": joke.get("type", "unknown"),\n\
            "id": str(joke.get("id", i))\n\
        })\n\
        ids.append(f"joke_{i}")\n\
    \n\
    collection.add(documents=docs, metadatas=metas, ids=ids)\n\
    print(f"Initialized ChromaDB with {len(docs)} jokes")\n\
else:\n\
    print(f"ChromaDB already has {collection.count()} jokes")' > init_chroma.py

# Initialize ChromaDB
RUN python init_chroma.py

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
