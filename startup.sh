#!/bin/bash
set -e

echo "Starting Joke Bot..."

# Check if ChromaDB is initialized
if [ ! -d "./chroma_db" ] || [ -z "$(ls -A ./chroma_db)" ]; then
    echo "Initializing ChromaDB..."
    python -c "
import chromadb
import json

client = chromadb.PersistentClient(path='./chroma_db')
collection = client.get_or_create_collection(name='jokes')

if collection.count() == 0:
    with open('jokes.json') as f:
        jokes = json.load(f)
    
    docs = []
    metas = []
    ids = []
    
    for i, joke in enumerate(jokes):
        if joke.get('type') == 'single':
            joke_text = joke.get('joke', '')
        else:
            joke_text = f\"{joke.get('setup', '')} {joke.get('delivery', '')}\"
        
        docs.append(joke_text)
        metas.append({
            'category': joke.get('category', 'Unknown'),
            'type': joke.get('type', 'unknown'),
            'id': str(joke.get('id', i))
        })
        ids.append(f'joke_{i}')
    
    collection.add(documents=docs, metadatas=metas, ids=ids)
    print(f'Initialized ChromaDB with {len(docs)} jokes')
else:
    print(f'ChromaDB already initialized with {collection.count()} jokes')
"
fi

echo "Starting Gunicorn..."
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
