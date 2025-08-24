# Intern Assignment Q9: Database Logging with FastAPI

This assignment demonstrates a CLI chatbot with conversation memory, rate limiting protection, LRU caching with TTL, AND comprehensive SQLite database logging with a FastAPI endpoint for history retrieval.

## Features

- 🤖 **Interactive CLI chatbot** with Google's Generative AI (Gemini)
- 💭 **Conversation memory** - remembers last 4 user-assistant turns using LangChain
- 🛡️ **Rate limiting protection** - Token bucket algorithm limiting to 10 requests per minute
- 🗄️ **LRU Cache with TTL** - In-memory cache (max 50 entries, 5 min TTL) for identical prompts
- 🗃️ **SQLite Database Logging** - Persist every chat turn with timestamps and token usage
- 🌐 **FastAPI Endpoint** - GET /history to retrieve last 20 chat entries via REST API
- 🚀 **Performance optimization** - Cache hits avoid API calls and rate limit consumption
- 📊 **Comprehensive statistics** - Cache, rate limit, and database analytics
- 🚫 **429 Error handling** - Returns appropriate error when rate limit exceeded
- 📊 **Database monitoring** - View chat history, stats, and manage database
- 🧹 **Memory management** - clear memory, cache, or database history
- 🔒 **Secure API handling** with environment variables
- ⚡ **Real-time responses** with proper error handling

## Database Schema

Each chat turn is stored in SQLite with the following fields:
- **id**: Primary key (auto-increment)
- **prompt**: User's input prompt
- **response**: Assistant's response  
- **tokens_used**: Estimated number of tokens used
- **timestamp**: When the chat turn occurred
- **model_name**: Model used for the response
- **was_cached**: Whether the response was served from cache

## FastAPI Endpoints

- **GET /history?limit=20** - Get recent chat history (default: 20, max: 100)
- **GET /stats** - Get database statistics (total entries, tokens, cache hit rate)
- **POST /chat** - Send a message to chatbot (logs to database)
- **DELETE /history** - Clear all chat history
- **GET /health** - Health check endpoint
- **GET /docs** - Interactive API documentation

## Cache Details

- **Algorithm**: LRU (Least Recently Used) with TTL (Time To Live)
- **Capacity**: Maximum 50 cached entries
- **TTL**: 5 minutes (300 seconds) - entries expire after this time
- **Cache Key**: Generated from user prompt + model name + conversation context
- **Benefits**: Identical prompts with same context return instantly from cache
- **Automatic cleanup**: Expired entries are automatically removed
- **Statistics**: Track hit rate, cache size, hits/misses for performance monitoring

## Rate Limiting Details

- **Algorithm**: Token bucket implementation
- **Limit**: 10 requests per minute (configurable)
- **Burst capacity**: Allows up to 10 requests immediately, then refills at 1 token per 6 seconds
- **Error handling**: Returns 429 status code with descriptive message when limit exceeded
- **In-memory**: Rate limit state maintained in memory (resets on restart)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Gemini API Key:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the API key

3. **Create .env file:**
   ```bash
   # Create .env file in the project root
   GEMINI_API_KEY=your_actual_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

## Usage

### CLI Mode

Run the chatbot in CLI mode:
```bash
python -m src.main
```

### FastAPI Server Mode

Run the FastAPI server:
```bash
python -m src.main api [port]
```

Example:
```bash
python -m src.main api 8000  # Runs on port 8000
```

The API server will be available at:
- **Server**: http://127.0.0.1:8000
- **Documentation**: http://127.0.0.1:8000/docs
- **History endpoint**: http://127.0.0.1:8000/history

### CLI Commands

- **Chat normally**: Just type your message and press Enter
- **quit/exit/bye**: End the conversation
- **clear**: Clear conversation memory
- **history**: View conversation history (from memory)
- **status**: View current rate limit status
- **cache**: View cache statistics and performance metrics
- **clear-cache**: Clear the response cache
- **db-stats**: View database statistics
- **db-history**: View recent database entries
- **clear-db**: Clear all database history
- **api**: Start FastAPI server from CLI

### API Usage Examples

Get recent chat history:
```bash
curl "http://127.0.0.1:8000/history?limit=10"
```

Get database statistics:
```bash
curl "http://127.0.0.1:8000/stats"
```

Send a chat message:
```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

Clear chat history:
```bash
curl -X DELETE "http://127.0.0.1:8000/history"
```

### Example Session

```
🤖 Welcome to the CLI Chatbot with Memory, Cache & Database!
💭 I'll remember our last 4 conversation turns.
⚡ Rate limit: 10 requests per minute
🗄️  Cache: LRU with 50 max entries, 5 min TTL
🗃️  Database: All chats logged to SQLite

👤 You: Hello, my name is Alice
🤖 Assistant: Hello Alice! Nice to meet you. How can I help you today?
💭 Memory: Remembering 1 turn(s)
🌐 (new API call) | Cache: 0.0% hit rate

👤 You: What's my name?
🤖 Assistant: Your name is Alice, as you just introduced yourself!
💭 Memory: Remembering 2 turn(s)
🌐 (new API call) | Cache: 0.0% hit rate

👤 You: Hello, my name is Alice
🤖 Assistant: Hello Alice! Nice to meet you. How can I help you today?
💭 Memory: Remembering 3 turn(s)
📋 (cached response) | Cache: 33.3% hit rate

👤 You: db-stats
� Database Statistics:
----------------------------------------
Total chat entries: 3
Total tokens used: 145
Cached responses: 1
Database cache hit rate: 33.3%
Latest entry: 2025-08-24 10:30:15
----------------------------------------

👤 You: db-history
📜 Last 3 Database Entries:
------------------------------------------------------------
ID 3 - 2025-08-24 10:30:15 📋
  👤 Hello, my name is Alice
  🤖 Hello Alice! Nice to meet you. How can I help you today?
  📊 48 tokens

ID 2 - 2025-08-24 10:29:45 🌐
  👤 What's my name?
  🤖 Your name is Alice, as you just introduced yourself!
  📊 49 tokens

ID 1 - 2025-08-24 10:29:20 🌐
  👤 Hello, my name is Alice
  🤖 Hello Alice! Nice to meet you. How can I help you today?
  📊 48 tokens
------------------------------------------------------------
```

## Test

Run the test script:
```bash
python -m pytest tests/ -v
```

Run the demo script:
```bash
python demo.py
```

## Technical Details

### LRU Cache with TTL Implementation

- **LRU Algorithm**: Least Recently Used eviction when capacity (50 entries) is exceeded
- **TTL Support**: Entries automatically expire after 5 minutes (300 seconds)
- **Cache Key Generation**: SHA256 hash of prompt + model + conversation context
- **Context-Aware**: Same prompt with different conversation context creates different cache entries
- **Performance**: Cache hits return instantly without API calls or rate limit consumption
- **Automatic Cleanup**: Expired entries are removed during cache operations
- **Memory Efficient**: Fixed maximum size prevents unbounded memory growth

### Cache Benefits

- **API Cost Reduction**: Identical requests don't consume API quota
- **Rate Limit Protection**: Cache hits don't count against rate limits
- **Improved Response Time**: Cached responses return instantly
- **Context Preservation**: Cache respects conversation context for accuracy
- **Monitoring**: Built-in statistics for cache performance analysis

### Rate Limiting Implementation

- **Token Bucket Algorithm**: Allows burst requests up to capacity but maintains average rate
- **Configurable Limits**: Default 10 requests per minute, customizable per instance
- **Automatic Refill**: Tokens refill continuously at 1 token per 6 seconds (for 10 req/min)
- **Precise Timing**: Uses high-resolution timestamps for accurate rate limiting
- **Error Handling**: Returns RateLimitError with 429 status code when limit exceeded

### Memory Management

- Uses **LangChain's ConversationBufferWindowMemory** with `k=4`
- Automatically manages conversation history
- Older messages are forgotten when limit is exceeded
- Memory can be cleared or inspected at any time

### Architecture

- `src/main.py` - CLI interface with interactive chat loop, database commands, and API server option
- `src/llm_client.py` - ChatbotWithMemory class with rate limiting, caching, and database logging
- `src/cache.py` - LRU cache with TTL implementation for response caching
- `src/rate_limiter.py` - Token bucket rate limiting implementation
- `src/database.py` - SQLite database management for chat history persistence
- `src/api.py` - FastAPI application with REST endpoints for chat history
- `src/config.py` - Configuration and environment variable loading
- `requirements.txt` - Python dependencies including LangChain, FastAPI, and database tools

### Database File

- **Location**: `chat_history.db` (created in project root)
- **Type**: SQLite database file
- **Persistence**: Survives application restarts
- **Management**: Can be cleared via CLI or API endpoint

### Dependencies

- **langchain** - Core LangChain framework
- **langchain-google-genai** - Google Generative AI integration
- **google-genai** - Google's Generative AI Python client
- **python-dotenv** - Environment variable management
- **fastapi** - Modern web framework for APIs
- **uvicorn** - ASGI server for FastAPI
- **pydantic** - Data validation for API models

## Available Gemini Models

- `gemini-2.5-flash` - Latest and fastest (default)
- `gemini-1.5-flash` - Fast and efficient
- `gemini-1.5-pro` - More capable but slower
- `gemini-1.0-pro` - Legacy model

## Security

✅ API key is stored in `.env` file (not committed to git)  
✅ Uses official Google Generative AI Python client  
✅ Secure API calls with proper error handling  
✅ LangChain integration for robust conversation management  
✅ **Rate limiting protection** against API abuse and cost control  
✅ **LRU cache with TTL** for performance optimization and cost reduction  
✅ **Proper 429 error handling** with informative messages  
✅ **Context-aware caching** prevents incorrect cached responses  
✅ **SQLite database** for reliable data persistence  
✅ **FastAPI security** with proper input validation and error handling  
✅ **Database isolation** - each instance uses its own database file  
✅ **Token estimation** for cost monitoring and optimization
