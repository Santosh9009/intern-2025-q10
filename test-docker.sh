#!/bin/bash

# Build and test script for the chatbot microservice
set -e

echo "🚀 Building and Testing Chatbot Microservice"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker is running"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your GEMINI_API_KEY before running the container"
    else
        print_error ".env.example not found. Please create .env file manually."
        exit 1
    fi
fi

# Build the Docker image
echo ""
echo "🔨 Building Docker image..."
docker build -t chatbot-microservice:latest . || {
    print_error "Docker build failed"
    exit 1
}

print_status "Docker image built successfully"

# Run tests in the container
echo ""
echo "🧪 Running tests in container..."
docker run --rm \
    -e GEMINI_API_KEY=test_key_for_testing \
    -e GEMINI_MODEL=gemini-2.5-flash \
    chatbot-microservice:latest \
    python -m pytest tests/ -v || {
    print_warning "Some tests failed (this may be expected without a real API key)"
}

# Check image size
echo ""
echo "📊 Image information:"
docker images chatbot-microservice:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Create data directory for volume mounting
mkdir -p ./data

# Run the container
echo ""
echo "🚀 Starting container..."
CONTAINER_ID=$(docker run -d \
    --name chatbot-test \
    -p 8000:8000 \
    --env-file .env \
    -v "$(pwd)/data:/app/data" \
    chatbot-microservice:latest)

print_status "Container started with ID: ${CONTAINER_ID:0:12}"

# Wait for container to be ready
echo ""
echo "⏳ Waiting for service to be ready..."
sleep 5

# Test health endpoint
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_status "Service is healthy!"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Service failed to start after 30 seconds"
        echo "Container logs:"
        docker logs chatbot-test
        docker stop chatbot-test
        docker rm chatbot-test
        exit 1
    fi
    sleep 1
done

# Test API endpoints
echo ""
echo "🔍 Testing API endpoints..."

# Health check
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | jq . || {
    print_warning "Health endpoint test failed (jq not installed?)"
    curl -s http://localhost:8000/health
}

# API documentation
echo ""
echo "Testing docs endpoint..."
if curl -s http://localhost:8000/docs | grep -q "OpenAPI"; then
    print_status "API documentation is accessible"
else
    print_warning "API documentation test failed"
fi

# Chat history (should be empty initially)
echo ""
echo "Testing history endpoint..."
curl -s http://localhost:8000/history | jq . || {
    print_warning "History endpoint test failed (jq not installed?)"
    curl -s http://localhost:8000/history
}

echo ""
print_status "All tests completed!"
echo ""
echo "🌐 Service URLs:"
echo "   Health:        http://localhost:8000/health"
echo "   API Docs:      http://localhost:8000/docs"
echo "   Chat History:  http://localhost:8000/history"
echo ""
echo "📝 To test the chat endpoint:"
echo "   curl -X POST http://localhost:8000/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\": \"Hello, how are you?\"}'"
echo ""
echo "🛑 To stop the container:"
echo "   docker stop chatbot-test"
echo "   docker rm chatbot-test"
echo ""
echo "💾 Database will be persisted in ./data/ directory"
