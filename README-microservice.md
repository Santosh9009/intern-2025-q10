# Chatbot FastAPI Micro-service

A production-ready FastAPI micro-service that packages the Q9 chatbot with comprehensive CI/CD pipeline.

## 🚀 Features

- **FastAPI REST API** with automatic OpenAPI documentation
- **Docker containerization** with multi-stage builds and security best practices
- **GitHub Actions CI/CD** with automated testing, security scanning, and deployment
- **Health checks** and monitoring endpoints
- **Container registry** integration (GitHub Container Registry)
- **Multi-platform builds** (AMD64 + ARM64)

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message to the chatbot |
| `GET` | `/history` | Retrieve chat history (paginated) |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/stats` | Database statistics |
| `DELETE` | `/history` | Clear chat history |
| `GET` | `/docs` | Interactive API documentation |

## 🐳 Docker Usage

### Building the image

```bash
docker build -t chatbot-api .
```

### Running the container

```bash
# Create environment file
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Run container
docker run -d \
  --name chatbot-api \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  chatbot-api
```

### Using docker-compose

```yaml
version: '3.8'
services:
  chatbot-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=your_api_key_here
      - GEMINI_MODEL=gemini-2.5-flash
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Health Checks

The container includes built-in health checks:

```bash
# Check health
curl http://localhost:8000/health

# Response
{
  "status": "healthy",
  "database": "connected",
  "total_entries": 42
}
```

## 🔄 CI/CD Pipeline

The GitHub Actions workflow includes:

### 1. **Testing Phase**
- Python 3.11 testing matrix
- Pytest execution with coverage
- Code quality checks (Black, isort, flake8)
- Dependency caching for faster builds

### 2. **Security Scanning**
- Trivy vulnerability scanner
- SARIF results uploaded to GitHub Security tab
- Dependency vulnerability checks

### 3. **Build & Push**
- Multi-platform Docker builds (AMD64 + ARM64)
- GitHub Container Registry (GHCR) integration
- Build caching for optimization
- Artifact attestation for supply chain security

### 4. **Deployment**
- Staging deployment on `develop` branch
- Production deployment on `main` branch
- Environment-specific configurations

## 🏃‍♂️ Running in Production

### Pull from GitHub Container Registry

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull the latest image
docker pull ghcr.io/username/intern-2025-q10:latest

# Run in production
docker run -d \
  --name chatbot-prod \
  -p 80:8000 \
  --restart unless-stopped \
  --env-file .env.prod \
  -v /opt/chatbot/data:/app/data \
  ghcr.io/username/intern-2025-q10:latest
```

### Environment Variables

Required environment variables:

```bash
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash  # optional, defaults to gemini-2.5-flash
```

### Data Persistence

Mount a volume for SQLite database persistence:

```bash
-v /path/to/data:/app/data
```

## 🔒 Security Features

- **Non-root user** in container
- **Minimal base image** (Python slim)
- **Security scanning** in CI pipeline
- **Dependency vulnerability checks**
- **Environment variable validation**
- **Input sanitization** via Pydantic models

## 📊 Monitoring

### Health Check Endpoint

```bash
GET /health
```

Response:
```json
{
  "status": "healthy|unhealthy",
  "database": "connected|error",
  "total_entries": 123,
  "error": "error_message_if_any"
}
```

### Database Statistics

```bash
GET /stats
```

Response:
```json
{
  "total_entries": 456,
  "total_tokens_used": 12345,
  "cached_entries": 89,
  "cache_hit_rate": 67.5,
  "latest_timestamp": "2025-08-24T10:30:15"
}
```

## 🚀 Scaling & Performance

### Horizontal Scaling

The service is stateless except for the SQLite database. For production scaling:

1. **Use external database** (PostgreSQL/MySQL)
2. **Redis for caching** instead of in-memory cache
3. **Load balancer** for multiple instances
4. **Container orchestration** (Kubernetes/Docker Swarm)

### Vertical Scaling

Resource requirements:
- **CPU**: 0.5-1 cores per instance
- **Memory**: 512MB-1GB per instance
- **Storage**: Depends on chat history retention

## 🔧 Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m src.main api 8000

# Or use uvicorn directly
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_main.py::test_database_logging -v

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .
```

## 📝 API Examples

### Send Chat Message

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you today?"}'
```

### Get Chat History

```bash
curl "http://localhost:8000/history?limit=10"
```

### Clear History

```bash
curl -X DELETE "http://localhost:8000/history"
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   ChatbotClient  │    │  Google Gemini  │
│                 │────│                  │────│      API        │
│  • REST API     │    │  • Memory Mgmt   │    │                 │
│  • Health Check │    │  • Rate Limiting │    └─────────────────┘
│  • OpenAPI Docs │    │  • Caching       │              
└─────────────────┘    └──────────────────┘    ┌─────────────────┐
         │                       │              │  SQLite Database│
         │                       └──────────────│                 │
         │                                      │  • Chat History │
         └──────────────────────────────────────│  • Token Usage │
                                                │  • Timestamps   │
                                                └─────────────────┘
```

## 📦 Container Registry

Images are automatically built and pushed to GitHub Container Registry:

- **Latest**: `ghcr.io/username/intern-2025-q10:latest`
- **Branch**: `ghcr.io/username/intern-2025-q10:main`
- **SHA**: `ghcr.io/username/intern-2025-q10:main-abc1234`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Ensure CI passes
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
