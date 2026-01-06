#!/bin/bash
set -e

export MINERU_MODEL_SOURCE=local

# Default API key
export MINERU_API_KEY="${MINERU_API_KEY:-mamaistdiebeste}"
export API_KEY="${API_KEY:-$MINERU_API_KEY}"

# Start the FastAPI server in the background
echo "🚀 Starting MinerU FastAPI server..."
mineru-api --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for the server to be ready
echo "⏳ Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Server failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Run warmup test
echo "🔥 Running warmup test..."
cd /app/mineru
if python3 simple_test.py; then
    echo "✅ Warmup test passed!"
else
    echo "❌ Warmup test failed!"
    kill $API_PID
    exit 1
fi

# If a command was provided, execute it
if [ $# -gt 0 ]; then
    exec "$@"
else
    # Otherwise, keep the API server running and wait
    echo "🎉 MinerU API is ready and running on port 8000"
    wait $API_PID
fi
