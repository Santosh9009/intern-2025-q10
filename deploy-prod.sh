#!/bin/bash

# Production deployment script
set -e

# Configuration
IMAGE_NAME="ghcr.io/santosh9009/intern-2025-q10"
CONTAINER_NAME="chatbot-prod"
PORT="80"
DATA_DIR="/opt/chatbot/data"

echo "🚀 Deploying Chatbot Microservice to Production"
echo "==============================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root or with sudo for production deployment"
    exit 1
fi

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running"
    exit 1
fi

print_status "Docker is ready"

# Create data directory
mkdir -p "$DATA_DIR"
chmod 755 "$DATA_DIR"
print_status "Data directory created: $DATA_DIR"

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    print_error ".env.prod file not found. Please create it with production environment variables."
    echo "Required variables:"
    echo "  GEMINI_API_KEY=your_production_api_key"
    echo "  GEMINI_MODEL=gemini-2.5-flash"
    exit 1
fi

# Stop existing container if running
if docker ps | grep -q "$CONTAINER_NAME"; then
    print_warning "Stopping existing container..."
    docker stop "$CONTAINER_NAME"
fi

# Remove existing container if exists
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    print_warning "Removing existing container..."
    docker rm "$CONTAINER_NAME"
fi

# Pull latest image
print_status "Pulling latest image..."
docker pull "$IMAGE_NAME:latest" || {
    print_error "Failed to pull image. Make sure you're logged in to the registry:"
    echo "  echo \$GITHUB_TOKEN | docker login ghcr.io -u \$GITHUB_USERNAME --password-stdin"
    exit 1
}

print_status "Image pulled successfully"

# Run the container in production mode
print_status "Starting production container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p "$PORT:8000" \
    --env-file .env.prod \
    -v "$DATA_DIR:/app/data" \
    --memory="1g" \
    --cpus="1.0" \
    --log-driver="json-file" \
    --log-opt max-size="10m" \
    --log-opt max-file="3" \
    "$IMAGE_NAME:latest"

# Wait for service to be ready
print_status "Waiting for service to be ready..."
sleep 10

# Health check
for i in {1..30}; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        print_status "Service is healthy and ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Service failed to start after 30 seconds"
        echo "Container logs:"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
    sleep 1
done

# Display service information
echo ""
print_status "Production deployment completed!"
echo ""
echo "🌐 Service Information:"
echo "   Container: $CONTAINER_NAME"
echo "   Port: $PORT"
echo "   Health: http://localhost:$PORT/health"
echo "   API Docs: http://localhost:$PORT/docs"
echo "   Data: $DATA_DIR"
echo ""
echo "📊 Container Status:"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "🔍 Useful Commands:"
echo "   View logs:    docker logs -f $CONTAINER_NAME"
echo "   Stop service: docker stop $CONTAINER_NAME"
echo "   Restart:      docker restart $CONTAINER_NAME"
echo "   Health check: curl http://localhost:$PORT/health"
echo ""

# Test the service
print_status "Testing the deployed service..."
curl -s "http://localhost:$PORT/health" | jq . || {
    print_warning "Health check response (jq not available):"
    curl -s "http://localhost:$PORT/health"
}

echo ""
print_status "Production deployment successful! 🎉"
