#!/bin/bash
# Test script to verify all required files exist before building

echo "Checking required files..."

files=(
    "app.py"
    "analytics.py"
    "jokes.json"
    "requirements.txt"
    "templates/index.html"
    "templates/admin_dashboard.html"
)

missing=0
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (MISSING)"
        missing=$((missing + 1))
    fi
done

if [ $missing -eq 0 ]; then
    echo ""
    echo "All required files present!"
    echo "You can now run: gcloud run deploy joke-bot --source . --region europe-west2"
else
    echo ""
    echo "ERROR: $missing file(s) missing. Please add them before deploying."
    exit 1
fi
