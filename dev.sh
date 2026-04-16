#!/bin/bash

# SchemaFlow AI - Development Environment Setup
# This script initializes the development environment

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║   SchemaFlow AI - Development Setup            ║"
echo "║   Converting NL → ER → SQL with Gemini         ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install: https://docs.docker.com/compose/install/"
    exit 1
fi
echo "✅ Docker Compose: $(docker-compose --version)"

echo ""
echo "📝 Configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for API key
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from template"
    fi
fi

# Display configuration status
if [ -f backend/.env ]; then
    API_KEY=$(grep GEMINI_API_KEY backend/.env | cut -d= -f2)
    if [ ! -z "$API_KEY" ]; then
        echo "✅ Gemini API Key configured (${#API_KEY} chars)"
    else
        echo "⚠️  Gemini API Key not set in backend/.env"
    fi
else
    echo "⚠️  backend/.env not found"
fi

echo ""
echo "🚀 Starting Services:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start services
echo "Starting docker-compose services..."
docker-compose down 2>/dev/null || true  # Clean up any existing containers

# Check if rebuild is needed
if [ "$1" == "--build" ] || [ "$1" == "-b" ]; then
    echo "Building fresh containers..."
    docker-compose up --build
else
    docker-compose up
fi

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📊 Endpoints:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend:        http://localhost:3000"
echo "Backend API:     http://localhost:8000"
echo "API Docs:        http://localhost:8000/docs"
echo "API ReDoc:       http://localhost:8000/redoc"
echo ""
echo "💡 Tips:"
echo "• Press Ctrl+C to stop services"
echo "• Use 'make dev' for the same functionality"
echo "• Check logs with 'docker-compose logs -f'"
echo ""
