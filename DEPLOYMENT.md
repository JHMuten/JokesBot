# Google Cloud Run Deployment Guide

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed: https://cloud.google.com/sdk/docs/install
3. **Docker** installed (optional, for local testing)

## Quick Deployment Steps

### 1. Set Up Google Cloud Project

```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 2. Create Artifact Registry Repository

```bash
# Create a Docker repository in London
gcloud artifacts repositories create joke-bot \
    --repository-format=docker \
    --location=europe-west2 \
    --description="Joke bot container images"

# Configure Docker authentication
gcloud auth configure-docker europe-west2-docker.pkg.dev
```

### 3. Store API Key as Secret

```bash
# Create secret for OpenRouter API key
echo -n "your-openrouter-api-key" | gcloud secrets create openrouter-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding openrouter-api-key \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

Note: Replace `PROJECT_NUMBER` with your actual project number (find it with `gcloud projects describe $PROJECT_ID`)

### 4. Build and Deploy

#### Option A: Direct Deploy (Recommended - Easiest)

```bash
# Deploy directly from source to London (Cloud Build handles everything)
gcloud run deploy joke-bot \
    --source . \
    --region europe-west2 \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --set-secrets OPENROUTER_API_KEY=openrouter-api-key:latest
```

#### Option B: Build Then Deploy

```bash
# Build the container image
gcloud builds submit --tag europe-west2-docker.pkg.dev/$PROJECT_ID/joke-bot/joke-bot:latest

# Deploy to Cloud Run in London
gcloud run deploy joke-bot \
    --image europe-west2-docker.pkg.dev/$PROJECT_ID/joke-bot/joke-bot:latest \
    --region europe-west2 \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --set-secrets OPENROUTER_API_KEY=openrouter-api-key:latest
```

#### Option C: Using YAML Configuration

```bash
# Update cloudrun.yaml with your project details
sed -i "s/PROJECT_ID/$PROJECT_ID/g" cloudrun.yaml

# Build image
gcloud builds submit --tag europe-west2-docker.pkg.dev/$PROJECT_ID/joke-bot/joke-bot:latest

# Deploy using YAML
gcloud run services replace cloudrun.yaml --region europe-west2
```

### 5. Get Your Service URL

```bash
# Get the deployed service URL
gcloud run services describe joke-bot --region europe-west2 --format 'value(status.url)'
```

Your app will be available at: `https://joke-bot-XXXXX-uc.a.run.app`

## Local Testing with Docker

```bash
# Build the image locally
docker build -t joke-bot .

# Run locally
docker run -p 8080:8080 \
    -e OPENROUTER_API_KEY="your-api-key" \
    joke-bot

# Test
curl http://localhost:8080
```

## Cost Optimization

### Lightweight Configuration
- **CPU**: 1 vCPU (can reduce to 0.5 for lower traffic)
- **Memory**: 512Mi (can reduce to 256Mi if needed)
- **Min Instances**: 0 (scales to zero when not in use)
- **Max Instances**: 10 (adjust based on expected traffic)
- **CPU Throttling**: Enabled (reduces cost when idle)

### Estimated Costs (europe-west2 - London)
- **Free Tier**: 2 million requests/month, 360,000 GB-seconds/month
- **After Free Tier**: ~$0.00002640 per request + $0.00001980 per GB-second
- **Typical Usage**: 1,000 requests/day ≈ $0-2/month (within free tier)

Note: London region is slightly more expensive than US regions (~10% higher)

### Cost Reduction Tips
1. **Scale to Zero**: Set `minScale: 0` (already configured)
2. **CPU Throttling**: Enabled in config (reduces idle costs)
3. **Right-size Resources**: Start with 256Mi memory, scale up if needed
4. **Use Secrets Manager**: Avoid hardcoding API keys
5. **Monitor Usage**: Set up billing alerts

## Monitoring & Logs

```bash
# View logs
gcloud run services logs read joke-bot --region europe-west2 --limit 50

# Stream logs in real-time
gcloud run services logs tail joke-bot --region europe-west2

# View metrics in Cloud Console
gcloud run services describe joke-bot --region europe-west2
```

## Updating the Deployment

```bash
# Redeploy with new code
gcloud run deploy joke-bot \
    --source . \
    --region europe-west2

# Update environment variables
gcloud run services update joke-bot \
    --region europe-west2 \
    --update-env-vars KEY=VALUE

# Update secrets
gcloud run services update joke-bot \
    --region europe-west2 \
    --update-secrets OPENROUTER_API_KEY=openrouter-api-key:latest
```

## Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service joke-bot \
    --domain jokes.yourdomain.com \
    --region europe-west2
```

## Troubleshooting

### Container fails to start
```bash
# Check logs
gcloud run services logs read joke-bot --region europe-west2 --limit 100

# Common issues:
# - Missing jokes.json file
# - Invalid API key
# - Port not set to 8080
```

### Out of Memory
```bash
# Increase memory
gcloud run services update joke-bot \
    --region europe-west2 \
    --memory 1Gi
```

### Slow Cold Starts
```bash
# Set minimum instances (costs more)
gcloud run services update joke-bot \
    --region europe-west2 \
    --min-instances 1

# Or enable startup CPU boost (already in config)
```

### Check Service Status
```bash
# Get service details
gcloud run services describe joke-bot --region europe-west2

# Test endpoint
curl https://your-service-url.run.app/api/analytics/stats
```

## Security Best Practices

1. **Use Secrets Manager**: ✅ Already configured
2. **Enable HTTPS**: ✅ Automatic with Cloud Run
3. **Restrict Access**: Add authentication if needed
4. **Set Resource Limits**: ✅ Already configured
5. **Monitor Logs**: Set up log-based alerts

## CI/CD Integration (Optional)

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - id: auth
      uses: google-github-actions/auth@v1
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}
    
    - name: Deploy to Cloud Run
      uses: google-github-actions/deploy-cloudrun@v1
      with:
        service: joke-bot
        region: us-central1
        source: .
```

## Cleanup

```bash
# Delete the service
gcloud run services delete joke-bot --region europe-west2

# Delete the container images
gcloud artifacts repositories delete joke-bot --location europe-west2

# Delete secrets
gcloud secrets delete openrouter-api-key
```

## Support & Resources

- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator
- **Quotas & Limits**: https://cloud.google.com/run/quotas
- **Best Practices**: https://cloud.google.com/run/docs/best-practices

## Quick Reference

```bash
# Deploy to London
gcloud run deploy joke-bot --source . --region europe-west2

# View URL
gcloud run services describe joke-bot --region europe-west2 --format 'value(status.url)'

# View logs
gcloud run services logs tail joke-bot --region europe-west2

# Update
gcloud run deploy joke-bot --source . --region europe-west2

# Delete
gcloud run services delete joke-bot --region europe-west2
```


## Common Issue: "I couldn't find any jokes matching your request"

### Problem
The chatbot always returns "I couldn't find any jokes matching your request" even though jokes.json exists.

### Root Cause
ChromaDB wasn't persisting data between container restarts. The in-memory database was being wiped.

### Solution (Already Fixed)
The updated code now:
1. Uses `PersistentClient` instead of ephemeral `Client()`
2. Pre-initializes ChromaDB during Docker build
3. Verifies initialization on startup

### Verify Fix
Check Cloud Run logs after deployment:
```bash
gcloud run services logs read joke-bot --region europe-west2 --limit 50
```

You should see:
```
Initialized ChromaDB with 100 jokes
```

### Manual Verification
Test the API directly:
```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe joke-bot --region europe-west2 --format 'value(status.url)')

# Test a query
curl -X POST $SERVICE_URL/api/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a programming joke"}'
```

Should return jokes, not "couldn't find any jokes".

### If Still Broken
1. Check if jokes.json is in the container:
```bash
gcloud run services describe joke-bot --region europe-west2
```

2. Rebuild and redeploy:
```bash
gcloud run deploy joke-bot --source . --region europe-west2
```

3. Check ChromaDB initialization in logs:
```bash
gcloud run services logs tail joke-bot --region europe-west2
```
