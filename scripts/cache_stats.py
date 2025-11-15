"""View API cache statistics."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.api_cache import api_cache


def main():
    """Display cache statistics."""
    print("📊 API Cache Statistics\n")
    print("=" * 60)
    
    stats = api_cache.get_stats()
    
    if not stats:
        print("No cache data found.")
        return
    
    total_entries = 0
    for api_name, api_stats in stats.items():
        print(f"\n{api_name.upper()}:")
        print(f"  Entries: {api_stats['total_entries']}")
        print(f"  Location: {api_stats['cache_dir']}")
        total_entries += api_stats['total_entries']
    
    print(f"\n{'=' * 60}")
    print(f"Total cached responses: {total_entries}")
    print(f"Cache directory: {api_cache.cache_dir}")
    
    print("\n💡 Tips:")
    print("  - Cached responses avoid hitting API rate limits")
    print("  - All APIs: 90 day (3 month) TTL")
    print("  - Cache persists across development sessions")
    print("  - Force refresh: rm -rf .cache/")


if __name__ == "__main__":
    main()

