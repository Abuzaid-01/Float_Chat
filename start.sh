#!/bin/bash

# Navigate to FloatChat directory
cd "$(dirname "$0")"

echo "=================================================="
echo "🌊 Starting FloatChat AI Backend & Frontend"
echo "=================================================="

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $(jobs -p) 2>/dev/null
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 0. Clean up any existing processes on ports 8000 and 3000
echo "🧹 Freeing ports 8000 & 3000 if in use..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# 1. Start Backend (FastAPI on Port 8000)
echo "🚀 [1/2] Starting FastAPI Backend on port 8000..."
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend health check
echo "⏳ Waiting for backend to initialize..."
until curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Backend is UP & running at http://localhost:8000"

# 2. Start Frontend (Next.js on Port 3000)
echo "✨ [2/2] Starting Next.js Frontend on port 3000..."
cd nexus-saa-s-ai-platform
pnpm dev --port 3000 &
FRONTEND_PID=$!

echo ""
echo "=================================================="
echo "🎉 FloatChat AI is Ready!"
echo "👉 Frontend App:  http://localhost:3000"
echo "👉 Backend API:   http://localhost:8000"
echo "👉 API Swagger:   http://localhost:8000/docs"
echo "=================================================="
echo "💡 Press Ctrl+C anytime to stop both servers."
echo ""

wait
