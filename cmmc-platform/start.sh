#!/bin/bash

# CMMC Compliance Platform - Startup Script
# Starts the full application stack (database, backend, frontend)

set -e

echo "🚀 Starting CMMC Compliance Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p database/seeds
mkdir -p api/logs
mkdir -p frontend/logs

# Start services
echo "📦 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U cmmc_user -d cmmc_platform > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready"
fi

# Check API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is ready"
else
    echo "⚠️  API is not ready yet (may take a few moments)"
fi

echo ""
echo "🎉 CMMC Compliance Platform is starting!"
echo ""
echo "📍 Services:"
echo "   - Frontend:  http://localhost:3000"
echo "   - API:       http://localhost:8000"
echo "   - API Docs:  http://localhost:8000/api/docs"
echo "   - Database:  localhost:5432"
echo ""
echo "📋 Useful commands:"
echo "   - View logs:     docker-compose logs -f"
echo "   - Stop all:      docker-compose down"
echo "   - Restart:       docker-compose restart"
echo ""
