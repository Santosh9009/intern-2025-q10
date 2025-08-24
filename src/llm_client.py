from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage
from typing import Optional
from src.config import env
from src.rate_limiter import get_rate_limiter, RateLimitError
from src.cache import get_cache
from src.database import get_database, estimate_tokens

class ChatbotWithMemory:
    """
    A chatbot class that uses LangChain's ConversationBufferWindowMemory 
    to remember the last 4 user-assistant turns.
    
    Includes rate limiting protection (default: 10 requests per minute)
    using token bucket algorithm. Returns 429 error when limit exceeded.
    
    Features LRU cache with TTL (max 50 entries, 5 min TTL) so identical
    prompts hit cache first, avoiding redundant API calls.
    
    All chat turns are logged to SQLite database with timestamps and token usage.
    """
    
    def __init__(self, model: Optional[str] = None, requests_per_minute: int = 10):
        api_key = env("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Put it in a .env file (see .env.example).")

        model_name = model or env("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_name = model_name
        
        # Initialize the LangChain Gemini model
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.7
        )
        
        # Initialize memory to keep last 4 user-assistant turns (k=4)
        # k=4 means keep last 4 messages, but we want 4 turns (8 messages)
        self.memory = ConversationBufferWindowMemory(
            k=8,  # Keep last 8 messages (4 user + 4 assistant)
            return_messages=True
        )
        
        # Initialize rate limiter
        self.rate_limiter = get_rate_limiter(requests_per_minute)
        
        # Initialize cache (LRU with TTL: max 50 entries, 5 min TTL)
        self.cache = get_cache(max_size=50, ttl_seconds=300)
        
        # Initialize database for logging
        self.database = get_database()
    
    def chat(self, user_input: str) -> str:
        """
        Send a message and get a response while maintaining conversation memory.
        Includes rate limiting protection, LRU caching with TTL, and database logging.
        
        Cache key is generated from:
        - User input
        - Model name  
        - Current conversation context (last 4 turns)
        
        This ensures identical prompts with same context hit cache first.
        All chat turns are logged to SQLite database.
        """
        try:
            # Get conversation history for context
            messages = self.memory.chat_memory.messages.copy()
            
            # Create context string from conversation history for cache key
            context_parts = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
                    context_parts.append(f"{role}:{msg.content}")
            context = "|".join(context_parts)
            
            # Check cache first (before rate limiting to save API quota)
            cached_response = self.cache.get(user_input, self.model_name, context)
            if cached_response is not None:
                # Cache hit! Save the conversation turn to memory and return cached response
                self.memory.chat_memory.add_user_message(user_input)
                self.memory.chat_memory.add_ai_message(cached_response)
                
                # Manually enforce the 4-turn (8 message) limit
                all_messages = self.memory.chat_memory.messages
                if len(all_messages) > 8:
                    self.memory.chat_memory.messages = all_messages[-8:]
                
                # Log to database (cache hit)
                total_tokens = estimate_tokens(user_input) + estimate_tokens(cached_response)
                self.database.log_chat_turn(
                    prompt=user_input,
                    response=cached_response,
                    tokens_used=total_tokens,
                    model_name=self.model_name,
                    was_cached=True
                )
                
                return cached_response
            
            # Cache miss - check rate limit before making API call
            self.rate_limiter.check_rate_limit()
            
            # Add the new human message for API call
            messages.append(HumanMessage(content=user_input))
            
            # Get response from the LLM
            response = self.llm.invoke(messages)
            response_content = response.content
            
            # Cache the response for future identical requests
            self.cache.put(user_input, response_content, self.model_name, context)
            
            # Save the conversation turn to memory using memory's methods
            self.memory.chat_memory.add_user_message(user_input)
            self.memory.chat_memory.add_ai_message(response_content)
            
            # Manually enforce the 4-turn (8 message) limit since ConversationBufferWindowMemory
            # might not work exactly as expected
            all_messages = self.memory.chat_memory.messages
            if len(all_messages) > 8:
                # Keep only the last 8 messages (4 turns)
                self.memory.chat_memory.messages = all_messages[-8:]
            
            # Log to database (new API call)
            total_tokens = estimate_tokens(user_input) + estimate_tokens(response_content)
            self.database.log_chat_turn(
                prompt=user_input,
                response=response_content,
                tokens_used=total_tokens,
                model_name=self.model_name,
                was_cached=False
            )
            
            return response_content
            
        except RateLimitError as e:
            # Re-raise rate limit errors with specific handling
            raise e
        except Exception as e:
            raise RuntimeError(f"Chat failed: {str(e)}")
    
    def get_conversation_history(self) -> list:
        """
        Get the current conversation history.
        """
        return self.memory.chat_memory.messages
    
    def clear_memory(self):
        """
        Clear the conversation memory.
        """
        self.memory.clear()
    
    def get_rate_limit_status(self) -> dict:
        """
        Get current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        return self.rate_limiter.get_status()
    
    def get_cache_stats(self) -> dict:
        """
        Get current cache statistics.
        
        Returns:
            Dictionary with cache statistics including hit rate, size, etc.
        """
        return self.cache.get_stats()
    
    def clear_cache(self):
        """
        Clear the response cache.
        """
        self.cache.clear()
    
    def get_database_stats(self) -> dict:
        """
        Get database statistics including total entries, tokens used, etc.
        
        Returns:
            Dictionary with database statistics
        """
        return self.database.get_stats()
    
    def get_chat_history_from_db(self, limit: int = 20) -> list:
        """
        Get recent chat history from the database.
        
        Args:
            limit: Number of recent entries to retrieve
            
        Returns:
            List of chat history entries
        """
        return self.database.get_recent_history(limit)
    
    def clear_database_history(self) -> int:
        """
        Clear all chat history from the database.
        
        Returns:
            Number of entries deleted
        """
        return self.database.clear_history()

def call_llm(prompt: str, model: Optional[str] = None, timeout: int = 30) -> str:
    """
    Legacy function for backward compatibility.
    Creates a new chatbot instance for a single call.
    """
    chatbot = ChatbotWithMemory(model)
    return chatbot.chat(prompt)
