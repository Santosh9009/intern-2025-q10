import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

class ChatDatabase:
    """
    SQLite database manager for storing chat turns.
    
    Each chat turn is stored with:
    - id: Primary key (auto-increment)
    - prompt: User's input prompt
    - response: Assistant's response
    - tokens_used: Number of tokens used (estimated)
    - timestamp: When the chat turn occurred
    """
    
    def __init__(self, db_path: str = "chat_history.db"):
        """
        Initialize the database connection and create tables if they don't exist.
        
        Args:
            db_path: Path to the SQLite database file
        """
        # Ensure the database directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create the chat_history table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    model_name TEXT,
                    was_cached BOOLEAN DEFAULT FALSE
                )
            ''')
            conn.commit()
    
    def log_chat_turn(
        self, 
        prompt: str, 
        response: str, 
        tokens_used: int,
        model_name: Optional[str] = None,
        was_cached: bool = False,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Log a chat turn to the database.
        
        Args:
            prompt: User's input prompt
            response: Assistant's response
            tokens_used: Number of tokens used
            model_name: Name of the model used
            was_cached: Whether the response was served from cache
            timestamp: When the chat occurred (defaults to now)
            
        Returns:
            The ID of the inserted record
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history (prompt, response, tokens_used, timestamp, model_name, was_cached)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (prompt, response, tokens_used, timestamp, model_name, was_cached))
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get the most recent chat history entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of dictionaries containing chat history
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, prompt, response, tokens_used, timestamp, model_name, was_cached
                FROM chat_history
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_total_entries(self) -> int:
        """Get the total number of chat entries in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM chat_history')
            return cursor.fetchone()[0]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute('SELECT COUNT(*) FROM chat_history')
            total_entries = cursor.fetchone()[0]
            
            # Total tokens used
            cursor.execute('SELECT SUM(tokens_used) FROM chat_history')
            total_tokens = cursor.fetchone()[0] or 0
            
            # Cache hit rate
            cursor.execute('SELECT COUNT(*) FROM chat_history WHERE was_cached = TRUE')
            cached_entries = cursor.fetchone()[0]
            
            # Most recent entry
            cursor.execute('SELECT timestamp FROM chat_history ORDER BY timestamp DESC LIMIT 1')
            latest_result = cursor.fetchone()
            latest_timestamp = latest_result[0] if latest_result else None
            
            cache_hit_rate = (cached_entries / total_entries * 100) if total_entries > 0 else 0
            
            return {
                'total_entries': total_entries,
                'total_tokens_used': total_tokens,
                'cached_entries': cached_entries,
                'cache_hit_rate': round(cache_hit_rate, 1),
                'latest_timestamp': latest_timestamp
            }
    
    def clear_history(self) -> int:
        """
        Clear all chat history from the database.
        
        Returns:
            Number of rows deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_history')
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def get_current_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.
        
        Returns:
            Current timestamp as ISO string
        """
        return datetime.now().isoformat()

# Global database instance
_db_instance = None

def get_database(db_path: str = "chat_history.db") -> ChatDatabase:
    """
    Get a singleton database instance.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        ChatDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = ChatDatabase(db_path)
    return _db_instance

def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.
    This is a rough approximation: ~4 characters per token for English text.
    
    Args:
        text: Input text to estimate tokens for
        
    Returns:
        Estimated number of tokens
    """
    # Rough estimate: 4 characters per token on average
    return len(text) // 4 + 1
