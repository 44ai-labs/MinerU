#!/bin/bash
set -e

export MINERU_MODEL_SOURCE=local

# Default API key
export MINERU_API_KEY="${MINERU_API_KEY:-mamaistdiebeste}"
export API_KEY="${API_KEY:-$MINERU_API_KEY}"
export PORT="${PORT:-8000}"

# --- GPU memory & throughput tuning ---

# Override detected VRAM (GB). L4 has 24GB but we report 12 to get a conservative
# batch_ratio=8 instead of 16. This controls how many images are processed in
# parallel for layout detection, formula recognition, and OCR batching.
# (used in: mineru/backend/pipeline/pipeline_analyze.py:batch_image_analyze
#  via mineru/utils/model_utils.py:get_vram)
export MINERU_VIRTUAL_VRAM_SIZE="${MINERU_VIRTUAL_VRAM_SIZE:-12}"

# Max pages fed into the model pipeline per batch. Default is 384 which means
# a 100-page PDF loads all page images into memory at once. Setting to 50 means
# pages are processed in chunks of 50 with memory cleanup between batches.
# (used in: mineru/backend/pipeline/pipeline_analyze.py:doc_analyze, line 81)
export MINERU_MIN_BATCH_INFERENCE_SIZE="${MINERU_MIN_BATCH_INFERENCE_SIZE:-50}"

# Max concurrent requests. Without this, multiple large PDFs can be processed
# simultaneously, compounding GPU memory usage. Returns HTTP 503 when at capacity.
# (used in: mineru/cli/fast_api.py:limit_concurrency via asyncio.Semaphore)
export MINERU_API_MAX_CONCURRENT_REQUESTS="${MINERU_API_MAX_CONCURRENT_REQUESTS:-5}"

# Start the FastAPI server in the background
echo "🚀 Starting MinerU FastAPI server..."
mineru-api --host 0.0.0.0 --port $PORT &
API_PID=$!

# TODO:
# start mineru on 8010
# test with test from 

# Wait for the server to be ready
echo "⏳ Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$PORT/docs > /dev/null 2>&1; then
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
export MINERU_API_PORT=$PORT
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
    echo "🎉 MinerU API is ready and running on port $PORT"
    wait $API_PID
fi
