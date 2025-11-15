#!/bin/bash

# CMMC Compliance Platform - Development Mode Startup Script
# Starts backend and frontend in development mode (without Docker)

set -e

echo "🚀 Starting CMMC Compliance Platform in Development Mode..."

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL is not running on localhost:5432"
    echo "   You can start it with Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=cmmc_password postgres:15"
    echo "   Or use Docker Compose: docker-compose up -d postgres"
    exit 1
fi

echo "✅ PostgreSQL is running"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi

# Start backend
echo "📦 Starting Backend API..."
cd api
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
python app.py &
BACKEND_PID=$!
cd ..

echo "✅ Backend started (PID: $BACKEND_PID)"

# Start frontend
echo "📦 Starting Frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ Frontend started (PID: $FRONTEND_PID)"

# Save PIDs
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

echo ""
echo "🎉 CMMC Compliance Platform is running in development mode!"
echo ""
echo "📍 Services:"
echo "   - Frontend:  http://localhost:3000"
echo "   - API:       http://localhost:8000"
echo "   - API Docs:  http://localhost:8000/api/docs"
echo ""
echo "📋 To stop: ./stop-dev.sh"
echo ""
