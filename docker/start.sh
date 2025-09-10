#!/bin/bash
set -e

echo "🚀 Starting AI Tutor Backend in production mode..."

# Check required environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ ERROR: GEMINI_API_KEY environment variable is required"
    exit 1
fi

# Set default values
export WORKERS=${WORKERS:-4}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
export LOG_LEVEL=${LOG_LEVEL:-info}

echo "📋 Configuration:"
echo "  Workers: $WORKERS"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Log Level: $LOG_LEVEL"
echo "  Environment: ${ENVIRONMENT:-production}"

# Wait for dependencies (if any)
echo "⏳ Checking dependencies..."

# Validate Gemini API key
python -c "
import os
import google.generativeai as genai
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-pro')
    print('✅ Gemini API key is valid')
except Exception as e:
    print(f'❌ Gemini API key validation failed: {e}')
    exit(1)
"

# Start the application
echo "🎯 Starting application server..."

if [ "$ENVIRONMENT" = "development" ]; then
    # Development mode with auto-reload
    exec uvicorn app.main:app \
        --host $HOST \
        --port $PORT \
        --reload \
        --log-level $LOG_LEVEL
else
    # Production mode with Gunicorn
    exec gunicorn app.main:app \
        --config gunicorn.conf.py \
        --bind $HOST:$PORT \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --access-logfile - \
        --error-logfile - \
        --log-level $LOG_LEVEL \
        --preload
fi


