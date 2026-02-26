# Docker Build Error Fix

## Error Message
```
Finished Step #0 - "Build"
ERROR: build step 0 "gcr.io/cloud-builders/docker" failed: step exited with non-zero status: 1
```

## What This Means
The Docker build process failed during the image creation. This is usually due to:
1. Missing required files
2. Syntax errors in Dockerfile
3. Python initialization script failing
4. Missing dependencies

## Fix Applied

### Changed Dockerfile to:
1. Remove complex one-liner Python commands
2. Create a separate `init_chroma.py` script during build
3. Simplify the initialization process
4. Remove dependency on `startup.sh`

### Files Required for Build:
- ✅ app.py
- ✅ analytics.py
- ✅ jokes.json
- ✅ requirements.txt
- ✅ templates/index.html
- ✅ templates/admin_dashboard.html

## Verify Before Deploying

Run this to check all files exist:
```bash
bash test_build.sh
```

## Deploy Again

```bash
gcloud run deploy joke-bot \
    --source . \
    --region europe-west2 \
    --allow-unauthenticated \
    --set-secrets OPENROUTER_API_KEY=openrouter-api-key:latest
```

## If Still Failing

### Get Detailed Error Logs:
```bash
gcloud builds list --limit=1
gcloud builds log <BUILD_ID>
```

### Common Issues:

#### 1. Missing jokes.json
**Error**: `FileNotFoundError: jokes.json`
**Fix**: Make sure jokes.json is in the root directory
```bash
ls -la jokes.json
```

#### 2. ChromaDB Installation Fails
**Error**: `ERROR: Could not build wheels for chromadb`
**Fix**: Already handled - we install gcc in Dockerfile

#### 3. Python Syntax Error
**Error**: `SyntaxError` during init
**Fix**: The new Dockerfile uses a proper Python script instead of one-liner

#### 4. Out of Memory During Build
**Error**: `Killed` or memory errors
**Fix**: Reduce ChromaDB initialization or use Cloud Build with more memory:
```bash
gcloud builds submit --machine-type=e2-highcpu-8
```

## Test Locally (Optional)

Build and test the Docker image locally:
```bash
# Build
docker build -t joke-bot-test .

# Run
docker run -p 8080:8080 \
    -e OPENROUTER_API_KEY="your-key" \
    joke-bot-test

# Test
curl http://localhost:8080
```

## Alternative: Simpler Dockerfile

If the build still fails, use this minimal version:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Create empty ChromaDB directory
RUN mkdir -p chroma_db && echo "[]" > analytics.json

ENV PORT=8080
EXPOSE 8080

# Initialize ChromaDB on startup instead of build time
CMD python -c "import chromadb; import json; client = chromadb.PersistentClient(path='./chroma_db'); collection = client.get_or_create_collection(name='jokes'); jokes = json.load(open('jokes.json')); [collection.add(documents=[j.get('joke','') if j.get('type')=='single' else f\"{j.get('setup','')} {j.get('delivery','')}\"], metadatas=[{'category':j.get('category','Unknown')}], ids=[f'joke_{i}']) for i,j in enumerate(jokes) if collection.count()==0]; print('Ready')" && exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
```

## Success Indicators

After successful deployment, you should see:
```
✓ Creating Revision...
✓ Routing traffic...
Done.
Service [joke-bot] revision [joke-bot-00001-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://joke-bot-xxxxx-ew.a.run.app
```

## Next Steps

Once deployed successfully:
1. Check logs: `gcloud run services logs read joke-bot --region europe-west2 --limit 20`
2. Look for: `Initialized ChromaDB with 100 jokes`
3. Test the endpoint: `curl https://your-url.run.app/api/joke`
