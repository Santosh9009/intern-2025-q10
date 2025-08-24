#!/bin/bash

# Simple Docker test script
set -e

echo "🐳 Testing Docker connectivity..."

# Test Docker daemon
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

echo "✅ Docker daemon is running"

# Test network connectivity
echo "🌐 Testing network connectivity..."
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "✅ Network connectivity is good"
else
    echo "❌ Network connectivity issues"
    exit 1
fi

# Try pulling a simpler image first
echo "🔄 Testing with a simple image..."
if docker pull hello-world; then
    echo "✅ Docker pull works with hello-world"
    docker run --rm hello-world
else
    echo "❌ Docker pull failed"
    exit 1
fi

echo "🎉 Docker is working correctly!"
