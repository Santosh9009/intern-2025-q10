#!/usr/bin/env python3
"""
Demo script for Q9: Database Logging & FastAPI

This script demonstrates:
1. Chat turns being logged to SQLite database
2. Database statistics and history viewing
3. FastAPI endpoint for retrieving chat history
4. Persistent storage across sessions
"""

import os
import sys
import time
import requests
import subprocess
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.llm_client import ChatbotWithMemory
from src.database import get_database
from src.config import env

def demo_database_logging():
    """Demonstrate database logging functionality."""
    print("🗃️  Demo: Database Logging")
    print("=" * 50)
    
    # Initialize chatbot
    try:
        chatbot = ChatbotWithMemory()
        print("✅ Chatbot initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing chatbot: {e}")
        print("💡 Make sure you have GEMINI_API_KEY in your .env file")
        return
    
    # Sample conversations to demonstrate logging
    demo_conversations = [
        "Hello, my name is Alice",
        "What's my name?",
        "What's the weather like today?",
        "Tell me a joke",
        "Hello, my name is Alice"  # This should hit cache
    ]
    
    print("\n📝 Running sample conversations...")
    
    for i, message in enumerate(demo_conversations, 1):
        print(f"\n--- Conversation {i} ---")
        print(f"👤 User: {message}")
        
        try:
            # Track cache stats
            stats_before = chatbot.get_cache_stats()
            hits_before = stats_before['hits']
            
            response = chatbot.chat(message)
            
            # Check cache hit
            stats_after = chatbot.get_cache_stats()
            hits_after = stats_after['hits']
            was_cached = hits_after > hits_before
            
            print(f"🤖 Assistant: {response}")
            cache_indicator = "📋 (cached)" if was_cached else "🌐 (new API call)"
            print(f"   {cache_indicator}")
            
            # Small delay between requests
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Show database statistics
    print("\n" + "=" * 50)
    print("📊 Database Statistics:")
    stats = chatbot.get_database_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Total tokens: {stats['total_tokens_used']:,}")
    print(f"Cached responses: {stats['cached_entries']}")
    print(f"Cache hit rate: {stats['cache_hit_rate']}%")
    
    # Show recent history from database
    print("\n📜 Recent Chat History from Database:")
    history = chatbot.get_chat_history_from_db(limit=5)
    for entry in history:
        timestamp = entry['timestamp'][:19]
        cached_marker = "📋" if entry['was_cached'] else "🌐"
        print(f"ID {entry['id']} - {timestamp} {cached_marker}")
        print(f"  👤 {entry['prompt'][:60]}...")
        print(f"  🤖 {entry['response'][:60]}...")
        print(f"  📊 {entry['tokens_used']} tokens")
    
    print("\n✅ Database logging demo completed!")
    return chatbot

def test_api_endpoints():
    """Test the FastAPI endpoints."""
    print("\n🌐 Demo: FastAPI Endpoints")
    print("=" * 50)
    
    # Start API server in background
    print("� Starting FastAPI server...")
    
    # Start server process
    try:
        server_process = subprocess.Popen([
            sys.executable, "-m", "src.main", "api", "8001"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(3)
        
        base_url = "http://127.0.0.1:8001"
        
        # Test endpoints
        print(f"\n📍 Testing API endpoints at {base_url}")
        
        # Test health endpoint
        try:
            response = requests.get(f"{base_url}/health")
            print(f"✅ Health check: {response.status_code}")
            if response.status_code == 200:
                print(f"   {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Health check failed: {e}")
        
        # Test history endpoint
        try:
            response = requests.get(f"{base_url}/history?limit=5")
            print(f"✅ History endpoint: {response.status_code}")
            if response.status_code == 200:
                history = response.json()
                print(f"   Retrieved {len(history)} entries")
                for entry in history[:2]:  # Show first 2
                    print(f"   ID {entry['id']}: {entry['prompt'][:40]}...")
        except requests.exceptions.RequestException as e:
            print(f"❌ History endpoint failed: {e}")
        
        # Test stats endpoint
        try:
            response = requests.get(f"{base_url}/stats")
            print(f"✅ Stats endpoint: {response.status_code}")
            if response.status_code == 200:
                stats = response.json()
                print(f"   Total entries: {stats['total_entries']}")
                print(f"   Total tokens: {stats['total_tokens_used']}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Stats endpoint failed: {e}")
        
        # Test chat endpoint
        try:
            chat_data = {"message": "This is a test via API"}
            response = requests.post(f"{base_url}/chat", json=chat_data)
            print(f"✅ Chat endpoint: {response.status_code}")
            if response.status_code == 200:
                chat_response = response.json()
                print(f"   Response: {chat_response['response'][:50]}...")
                print(f"   Tokens: {chat_response['tokens_used']}")
                print(f"   Cached: {chat_response['was_cached']}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Chat endpoint failed: {e}")
        
        print(f"\n📖 API Documentation available at: {base_url}/docs")
        print(f"🔍 Full history endpoint: {base_url}/history")
        
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
    finally:
        # Clean up server process
        try:
            server_process.terminate()
            server_process.wait(timeout=5)
            print("⏹️  API server stopped")
        except:
            pass

def main():
    """Run the complete demo."""
    print("� Q9 Demo: Database Logging & FastAPI")
    print("=" * 60)
    
    # Check environment
    api_key = env("GEMINI_API_KEY")
    if not api_key:
        print("❌ Missing GEMINI_API_KEY environment variable")
        print("� Create a .env file with your Gemini API key:")
        print("   GEMINI_API_KEY=your_api_key_here")
        return
    
    # Run database demo
    chatbot = demo_database_logging()
    
    if chatbot:
        # Test API endpoints
        test_api_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Run 'python -m src.main' for CLI mode")
        print("   2. Run 'python -m src.main api' for API server mode")
        print("   3. Visit http://127.0.0.1:8000/docs for API documentation")
        print("   4. Use 'db-stats' and 'db-history' commands in CLI")
        
        # Show database file location
        db_path = Path("chat_history.db").absolute()
        print(f"\n🗃️  Database file: {db_path}")
        if db_path.exists():
            size_kb = db_path.stat().st_size / 1024
            print(f"   Size: {size_kb:.1f} KB")

if __name__ == "__main__":
    main()
