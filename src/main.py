from src.llm_client import ChatbotWithMemory
from src.config import env
from src.rate_limiter import RateLimitError
import sys

def show_database_stats(chatbot):
    """Show database statistics."""
    stats = chatbot.get_database_stats()
    print("\n📊 Database Statistics:")
    print("-" * 40)
    print(f"Total chat entries: {stats['total_entries']}")
    print(f"Total tokens used: {stats['total_tokens_used']:,}")
    print(f"Cached responses: {stats['cached_entries']}")
    print(f"Database cache hit rate: {stats['cache_hit_rate']}%")
    if stats['latest_timestamp']:
        print(f"Latest entry: {stats['latest_timestamp']}")
    print("-" * 40)

def show_database_history(chatbot, limit=10):
    """Show recent database history."""
    history = chatbot.get_chat_history_from_db(limit)
    if not history:
        print("📜 No chat history in database yet.")
        return
    
    print(f"\n📜 Last {len(history)} Database Entries:")
    print("-" * 60)
    for entry in history:
        timestamp = entry['timestamp'][:19]  # Remove microseconds
        cached_marker = "📋" if entry['was_cached'] else "🌐"
        prompt_preview = entry['prompt'][:50] + "..." if len(entry['prompt']) > 50 else entry['prompt']
        response_preview = entry['response'][:50] + "..." if len(entry['response']) > 50 else entry['response']
        print(f"ID {entry['id']} - {timestamp} {cached_marker}")
        print(f"  👤 {prompt_preview}")
        print(f"  🤖 {response_preview}")
        print(f"  📊 {entry['tokens_used']} tokens")
        print()
    print("-" * 60)

def main():
    """
    CLI Chatbot with memory that remembers the last 4 user-assistant turns.
    Includes rate limiting: 10 requests per minute maximum.
    Features LRU cache with TTL: max 50 entries, 5 min TTL for identical prompts.
    All chat turns are logged to SQLite database with full history persistence.
    """
    
    # Check for API server mode
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        from src.api import run_server
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        run_server(port=port, reload=True)
        return
    
    print("=" * 60)
    print("🤖 Welcome to the CLI Chatbot with Memory, Cache & Database!")
    print("💭 I'll remember our last 4 conversation turns.")
    print("⚡ Rate limit: 10 requests per minute")
    print("🗄️  Cache: LRU with 50 max entries, 5 min TTL")
    print("🗃️  Database: All chats logged to SQLite")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.")
    print("Type 'clear' to clear conversation memory.")
    print("Type 'history' to see conversation history.")
    print("Type 'status' to see rate limit status.")
    print("Type 'cache' to see cache statistics.")
    print("Type 'clear-cache' to clear response cache.")
    print("Type 'db-stats' to see database statistics.")
    print("Type 'db-history' to see recent database entries.")
    print("Type 'clear-db' to clear database history.")
    print("Type 'api' to start FastAPI server mode.")
    print("=" * 60)
    
    try:
        # Initialize the chatbot with memory
        print(f"🔧 Initializing with model: {env('GEMINI_MODEL')}")
        chatbot = ChatbotWithMemory()
        print("✅ Chatbot initialized successfully!\n")
        
        conversation_count = 0
        
        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Goodbye! Thanks for chatting!")
                    break
                    
                elif user_input.lower() == 'clear':
                    chatbot.clear_memory()
                    conversation_count = 0
                    print(" Conversation memory cleared!")
                    continue
                    
                elif user_input.lower() == 'history':
                    history = chatbot.get_conversation_history()
                    if not history:
                        print("📜 No conversation history yet.")
                    else:
                        print("\n📜 Conversation History:")
                        print("-" * 40)
                        for i, msg in enumerate(history, 1):
                            if hasattr(msg, 'content'):
                                role = "👤 You" if msg.__class__.__name__ == "HumanMessage" else "🤖 Assistant"
                                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                                print(f"{i}. {role}: {content}")
                        print("-" * 40)
                    continue
                    
                elif user_input.lower() == 'status':
                    status = chatbot.get_rate_limit_status()
                    print("\n⚡ Rate Limit Status:")
                    print("-" * 40)
                    print(f"Requests per minute: {status['requests_per_minute']}")
                    print(f"Available tokens: {status['available_tokens']}")
                    print(f"Capacity: {status['capacity']}")
                    if status['time_until_next_token'] > 0:
                        print(f"Next token in: {status['time_until_next_token']:.1f} seconds")
                    else:
                        print("Next token: Available now")
                    print("-" * 40)
                    continue
                
                elif user_input.lower() == 'cache':
                    stats = chatbot.get_cache_stats()
                    print("\n🗄️  Cache Statistics:")
                    print("-" * 40)
                    print(f"Cache size: {stats['size']}/{stats['max_size']} entries")
                    print(f"Hit rate: {stats['hit_rate']}%")
                    print(f"Cache hits: {stats['hits']}")
                    print(f"Cache misses: {stats['misses']}")
                    print(f"TTL: {stats['ttl_seconds']} seconds (5 minutes)")
                    print("-" * 40)
                    continue
                
                elif user_input.lower() == 'clear-cache':
                    chatbot.clear_cache()
                    print("🗑️  Response cache cleared!")
                    continue
                
                elif user_input.lower() == 'db-stats':
                    show_database_stats(chatbot)
                    continue
                
                elif user_input.lower() == 'db-history':
                    show_database_history(chatbot, limit=10)
                    continue
                
                elif user_input.lower() == 'clear-db':
                    deleted_count = chatbot.clear_database_history()
                    print(f"🗑️  Cleared {deleted_count} database entries!")
                    continue
                
                elif user_input.lower() == 'api':
                    print("🚀 Starting FastAPI server...")
                    print("💡 Tip: Run 'python -m src.main api' to start in API mode")
                    from src.api import run_server
                    try:
                        run_server(port=8000, reload=False)
                    except KeyboardInterrupt:
                        print("\n⏹️  API server stopped.")
                    continue
                    
                elif not user_input:
                    print("⚠️  Please enter a message or 'quit' to exit.")
                    continue
                
                # Get response from chatbot
                print("🤖 Assistant: ", end="", flush=True)
                
                # Track cache stats before the request
                stats_before = chatbot.get_cache_stats()
                hits_before = stats_before['hits']
                
                response = chatbot.chat(user_input)
                
                # Check if this was a cache hit
                stats_after = chatbot.get_cache_stats()
                hits_after = stats_after['hits']
                was_cache_hit = hits_after > hits_before
                
                print(response)
                
                conversation_count += 1
                
                # Show memory status and cache info
                history_length = len(chatbot.get_conversation_history())
                turns = history_length // 2  # Each turn has user + assistant message
                if turns >= 4:
                    memory_status = "Remembering last 4 turns (older messages forgotten)"
                else:
                    memory_status = f"Remembering {turns} turn(s)"
                
                cache_info = "📋 (cached response)" if was_cache_hit else "🌐 (new API call)"
                print(f"💭 Memory: {memory_status}")
                print(f"{cache_info} | Cache: {stats_after['hit_rate']}% hit rate")
                    
            except RateLimitError as e:
                print(f"\n🚫 {e.message}")
                print("⏱️  You can check rate limit status with 'status' command.")
                continue
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user. Type 'quit' to exit gracefully.")
                continue
            except Exception as e:
                print(f"\n❌ Error during chat: {e}")
                print("🔄 Please try again or type 'quit' to exit.")
                continue
                
    except Exception as e:
        print(f"❌ Error initializing chatbot: {e}")
        print("🔧 Please check your configuration and try again.")

if __name__ == "__main__":
    main()