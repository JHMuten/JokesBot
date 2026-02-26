import chromadb
import json

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="jokes")

if collection.count() == 0:
    with open("jokes.json") as f:
        jokes = json.load(f)
    
    docs = []
    metas = []
    ids = []
    
    for i, joke in enumerate(jokes):
        if joke.get("type") == "single":
            joke_text = joke.get("joke", "")
        else:
            setup = joke.get("setup", "")
            delivery = joke.get("delivery", "")
            joke_text = f"{setup} {delivery}"
        
        docs.append(joke_text)
        metas.append({
            "category": joke.get("category", "Unknown"),
            "type": joke.get("type", "unknown"),
            "id": str(joke.get("id", i))
        })
        ids.append(f"joke_{i}")
    
    collection.add(documents=docs, metadatas=metas, ids=ids)
    print(f"Initialized ChromaDB with {len(docs)} jokes")
else:
    print(f"ChromaDB already has {collection.count()} jokes")
