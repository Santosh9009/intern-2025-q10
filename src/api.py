from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from src.database import get_database
from src.llm_client import ChatbotWithMemory
from src.config import env
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Chat History API",
    description="API for retrieving chat history from SQLite database",
    version="1.0.0"
)

# Initialize database
database = get_database()

class ChatHistoryResponse(BaseModel):
    """Response model for chat history entries."""
    id: int
    prompt: str
    response: str
    tokens_used: int
    timestamp: str
    model_name: Optional[str] = None
    was_cached: bool = False

class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics."""
    total_entries: int
    total_tokens_used: int
    cached_entries: int
    cache_hit_rate: float
    latest_timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    model: Optional[str] = None

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    tokens_used: int
    was_cached: bool
    model_name: str

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Chat History API",
        "version": "1.0.0",
        "endpoints": [
            "/history - Get recent chat history",
            "/stats - Get database statistics",
            "/chat - Send a chat message",
            "/docs - API documentation"
        ]
    }

@app.get("/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    limit: int = Query(20, ge=1, le=100, description="Number of entries to retrieve")
):
    """
    Get the most recent chat history entries from the database.
    
    Args:
        limit: Maximum number of entries to return (default: 20, max: 100)
        
    Returns:
        List of chat history entries ordered by timestamp (most recent first)
    """
    try:
        history = database.get_recent_history(limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats():
    """
    Get database statistics including total entries, tokens used, and cache hit rate.
    
    Returns:
        Database statistics
    """
    try:
        stats = database.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    """
    Send a message to the chatbot and get a response.
    The chat turn will be automatically logged to the database.
    
    Args:
        request: Chat request containing the message and optional model
        
    Returns:
        Chat response with token usage and cache information
    """
    try:
        # Initialize chatbot with specified model or default
        chatbot = ChatbotWithMemory(model=request.model)
        
        # Track cache stats before the request
        cache_stats_before = chatbot.get_cache_stats()
        hits_before = cache_stats_before['hits']
        
        # Get response from chatbot (automatically logs to database)
        response = chatbot.chat(request.message)
        
        # Check if this was a cache hit
        cache_stats_after = chatbot.get_cache_stats()
        hits_after = cache_stats_after['hits']
        was_cached = hits_after > hits_before
        
        # Estimate tokens (this is already calculated in the chat method)
        from src.database import estimate_tokens
        total_tokens = estimate_tokens(request.message) + estimate_tokens(response)
        
        return ChatResponse(
            response=response,
            tokens_used=total_tokens,
            was_cached=was_cached,
            model_name=chatbot.model_name
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.delete("/history")
async def clear_chat_history():
    """
    Clear all chat history from the database.
    
    Returns:
        Number of entries deleted
    """
    try:
        deleted_count = database.clear_history()
        return {"message": f"Cleared {deleted_count} chat history entries"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        total_entries = database.get_total_entries()
        return {
            "status": "healthy",
            "database": "connected",
            "total_entries": total_entries
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "error",
                "error": str(e)
            }
        )

def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """
    Run the FastAPI server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    print(f"🚀 Starting Chat History API server...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"📖 API documentation: http://{host}:{port}/docs")
    print(f"🔍 Chat history endpoint: http://{host}:{port}/history")
    
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    run_server(reload=True)
