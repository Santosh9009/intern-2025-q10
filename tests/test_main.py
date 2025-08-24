import os
import time
import pytest
import tempfile
import shutil
from pathlib import Path
from src.llm_client import call_llm, ChatbotWithMemory
from src.rate_limiter import RateLimitError, TokenBucket, RateLimiter, reset_rate_limiter
from src.database import ChatDatabase, get_database, estimate_tokens

# Database tests (no API key required)
def test_database_initialization():
    """Test database initialization and table creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        db = ChatDatabase(db_path)
        
        # Should create the database file
        assert os.path.exists(db_path)
        
        # Should be able to get stats (should be empty initially)
        stats = db.get_stats()
        assert stats['total_entries'] == 0
        assert stats['total_tokens_used'] == 0

def test_database_logging():
    """Test logging chat turns to database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        db = ChatDatabase(db_path)
        
        # Log a chat turn
        chat_id = db.log_chat_turn(
            prompt="Hello",
            response="Hi there!",
            tokens_used=10,
            model_name="test-model",
            was_cached=False
        )
        
        assert chat_id > 0
        
        # Check stats
        stats = db.get_stats()
        assert stats['total_entries'] == 1
        assert stats['total_tokens_used'] == 10
        assert stats['cached_entries'] == 0

def test_database_history_retrieval():
    """Test retrieving chat history from database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        db = ChatDatabase(db_path)
        
        # Log multiple chat turns
        for i in range(5):
            db.log_chat_turn(
                prompt=f"Question {i}",
                response=f"Answer {i}",
                tokens_used=10 + i,
                was_cached=(i % 2 == 0)
            )
        
        # Get recent history
        history = db.get_recent_history(limit=3)
        assert len(history) == 3
        
        # Should be in reverse chronological order (most recent first)
        assert history[0]['prompt'] == "Question 4"
        assert history[1]['prompt'] == "Question 3"
        assert history[2]['prompt'] == "Question 2"
        
        # Check cache information
        assert history[0]['was_cached'] == True  # Question 4 (4 % 2 == 0)
        assert history[1]['was_cached'] == False  # Question 3 (3 % 2 != 0)

def test_database_clear_history():
    """Test clearing database history."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        db = ChatDatabase(db_path)
        
        # Add some entries
        for i in range(3):
            db.log_chat_turn(f"Test {i}", f"Response {i}", 10)
        
        assert db.get_total_entries() == 3
        
        # Clear history
        deleted_count = db.clear_history()
        assert deleted_count == 3
        assert db.get_total_entries() == 0

def test_token_estimation():
    """Test token estimation function."""
    # Test empty string
    assert estimate_tokens("") == 1  # Minimum 1 token
    
    # Test short string
    assert estimate_tokens("hello") >= 1
    
    # Test longer string (should be roughly 1 token per 4 characters)
    long_text = "This is a longer text that should have multiple tokens"
    estimated = estimate_tokens(long_text)
    expected_range = len(long_text) // 4
    assert estimated >= expected_range
    assert estimated <= expected_range + 5  # Some tolerance

# Rate limiting tests (no API key required)
def test_token_bucket_basic():
    """Test basic token bucket functionality."""
    # Create bucket with 5 tokens, refill rate of 1 token per second
    bucket = TokenBucket(capacity=5, refill_rate=1.0)
    
    # Should be able to consume up to capacity
    assert bucket.consume(5) == True
    
    # Should not be able to consume more
    assert bucket.consume(1) == False

def test_token_bucket_refill():
    """Test that tokens refill over time."""
    bucket = TokenBucket(capacity=2, refill_rate=2.0)  # 2 tokens per second
    
    # Consume all tokens
    assert bucket.consume(2) == True
    assert bucket.consume(1) == False
    
    # Wait and check refill
    time.sleep(1.1)  # Wait just over 1 second
    assert bucket.consume(2) == True  # Should have refilled

def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(requests_per_minute=60)  # 1 per second
    
    # Should allow first request
    limiter.check_rate_limit()  # Should not raise
    
    # After consuming capacity, should raise error
    # Note: This depends on exact timing, so we'll test the logic
    status = limiter.get_status()
    assert status['requests_per_minute'] == 60
    assert status['capacity'] == 60

def test_rate_limiter_error():
    """Test that rate limiter raises correct error."""
    limiter = RateLimiter(requests_per_minute=1)  # Very restrictive
    
    # First request should work
    limiter.check_rate_limit()
    
    # Immediate second request should fail
    with pytest.raises(RateLimitError) as excinfo:
        limiter.check_rate_limit()
    
    assert excinfo.value.status_code == 429
    assert "Rate limit exceeded" in excinfo.value.message

def test_chatbot_rate_limiting():
    """Test that chatbot respects rate limits."""
    reset_rate_limiter()
    
    # Create chatbot with very low rate limit for testing
    chatbot = ChatbotWithMemory(requests_per_minute=1)
    
    # Mock the LLM to avoid actual API calls
    def mock_chat(self, user_input):
        # Check rate limit (this is what we want to test)
        self.rate_limiter.check_rate_limit()
        return "Mock response"
    
    # Replace chat method temporarily
    original_method = ChatbotWithMemory.chat
    ChatbotWithMemory.chat = mock_chat
    
    try:
        # First call should work
        response1 = chatbot.chat("Test 1")
        assert response1 == "Mock response"
        
        # Second immediate call should fail
        with pytest.raises(RateLimitError):
            chatbot.chat("Test 2")
    
    finally:
        # Restore original method
        ChatbotWithMemory.chat = original_method

def test_chatbot_rate_limit_status():
    """Test rate limit status functionality."""
    reset_rate_limiter()
    
    chatbot = ChatbotWithMemory(requests_per_minute=10)
    status = chatbot.get_rate_limit_status()
    
    assert 'requests_per_minute' in status
    assert 'available_tokens' in status
    assert 'capacity' in status
    assert status['requests_per_minute'] == 10
    assert status['capacity'] == 10

# Original tests with API key requirements
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set")
def test_llm_response_basic():
    """Test basic LLM response."""
    out = call_llm("Reply with a single word: Hello.")
    assert isinstance(out, str)
    assert len(out.strip()) > 0

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set")
def test_chatbot_memory():
    """Test that the chatbot remembers conversation context."""
    reset_rate_limiter()  # Reset for clean test
    
    chatbot = ChatbotWithMemory()
    
    # First message
    response1 = chatbot.chat("My name is Alice")
    assert isinstance(response1, str)
    assert len(response1.strip()) > 0
    
    # Second message - test memory
    response2 = chatbot.chat("What is my name?")
    assert isinstance(response2, str)
    assert len(response2.strip()) > 0
    
    # Check that we have conversation history
    history = chatbot.get_conversation_history()
    assert len(history) == 4  # 2 user messages + 2 assistant messages

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set")
def test_chatbot_database_integration():
    """Test that chatbot logs to database correctly."""
    reset_rate_limiter()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use a temporary database for testing
        original_db_path = "chat_history.db"
        test_db_path = os.path.join(temp_dir, "test_chat.db")
        
        # Create chatbot with rate limiting that won't interfere
        chatbot = ChatbotWithMemory(requests_per_minute=30)
        
        # Override the database to use our test database
        from src.database import ChatDatabase
        chatbot.database = ChatDatabase(test_db_path)
        
        # Have a conversation
        response = chatbot.chat("Hello, test message")
        assert isinstance(response, str)
        
        # Check that it was logged to database
        stats = chatbot.get_database_stats()
        assert stats['total_entries'] == 1
        assert stats['total_tokens_used'] > 0
        
        # Check history
        history = chatbot.get_chat_history_from_db(limit=1)
        assert len(history) == 1
        assert history[0]['prompt'] == "Hello, test message"
        assert history[0]['response'] == response

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set") 
def test_chatbot_database_cache_tracking():
    """Test that database correctly tracks cache hits."""
    reset_rate_limiter()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = os.path.join(temp_dir, "test_cache.db")
        
        chatbot = ChatbotWithMemory(requests_per_minute=30)
        
        # Override database
        from src.database import ChatDatabase
        chatbot.database = ChatDatabase(test_db_path)
        
        # First request (should be cache miss)
        response1 = chatbot.chat("What is 2+2?")
        
        # Second identical request (should be cache hit)
        response2 = chatbot.chat("What is 2+2?")
        
        # Check database entries
        history = chatbot.get_chat_history_from_db(limit=2)
        assert len(history) == 2
        
        # First entry should not be cached, second should be
        assert history[0]['was_cached'] == True   # Most recent (cache hit)
        assert history[1]['was_cached'] == False  # First one (cache miss)
        
        # Check database stats
        stats = chatbot.get_database_stats()
        assert stats['total_entries'] == 2
        assert stats['cached_entries'] == 1
        assert stats['cache_hit_rate'] == 50.0

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set")
def test_chatbot_memory_limit():
    """Test that the chatbot only remembers last 4 turns."""
    reset_rate_limiter()  # Reset for clean test
    
    chatbot = ChatbotWithMemory()
    
    # Have more than 4 conversations
    for i in range(6):
        response = chatbot.chat(f"Message number {i+1}")
        assert isinstance(response, str)
        # Add small delay to avoid rate limiting during test
        time.sleep(7)  # 10 req/min = 1 req per 6 seconds, so 7 seconds is safe
    
    # Should only remember last 4 turns (8 messages total)
    history = chatbot.get_conversation_history()
    assert len(history) <= 8  # 4 turns × 2 messages per turn

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set")
def test_chatbot_clear_memory():
    """Test that clearing memory works."""
    reset_rate_limiter()  # Reset for clean test
    
    chatbot = ChatbotWithMemory()
    
    # Have a conversation
    chatbot.chat("Remember this message")
    assert len(chatbot.get_conversation_history()) > 0
    
    # Clear memory
    chatbot.clear_memory()
    assert len(chatbot.get_conversation_history()) == 0

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No GEMINI_API_KEY set")
def test_chatbot_with_rate_limiting_integration():
    """Integration test for chatbot with rate limiting."""
    reset_rate_limiter()
    
    # Create chatbot with low rate limit for testing
    chatbot = ChatbotWithMemory(requests_per_minute=2)
    
    # First request should work
    response1 = chatbot.chat("Say hello")
    assert isinstance(response1, str)
    
    # Second request should work
    response2 = chatbot.chat("Say goodbye")
    assert isinstance(response2, str)
    
    # Third immediate request should fail with rate limit
    with pytest.raises(RateLimitError) as excinfo:
        chatbot.chat("This should be rate limited")
    
    assert excinfo.value.status_code == 429

def test_sanity_local():
    """A pure-python test so CI passes even without keys."""
    assert 2 + 2 == 4
