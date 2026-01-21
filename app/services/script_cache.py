"""
Topic Usage Cache Service

This module tracks which topics have been used for video generation
to prevent repetitive content. It maintains a 90-day history and
helps select unused or least-recently-used topics.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


# Cache file location - in config directory so it can be committed
CACHE_DIR = Path(__file__).parent.parent.parent / "config"
CACHE_FILE = CACHE_DIR / "topic_history.json"

# How long to retain topic usage history (90 days)
RETENTION_DAYS = 90


class TopicCache:
    """
    Manages topic usage history to prevent repetitive content.
    
    The cache stores:
    - topic: The topic string
    - channel: Which channel used it
    - timestamp: When it was used
    - count: How many times used in retention period
    """
    
    def __init__(self, cache_file: Path = CACHE_FILE):
        self.cache_file = cache_file
        self.history: List[Dict[str, Any]] = []
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk and clean expired entries."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                    logger.info(f"Loaded {len(self.history)} topic history entries")
            except Exception as e:
                logger.warning(f"Failed to load topic cache: {e}")
                self.history = []
        
        # Clean expired entries
        self._cleanup_expired()
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'history': self.history
                }, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.history)} topic history entries")
        except Exception as e:
            logger.error(f"Failed to save topic cache: {e}")
    
    def _cleanup_expired(self) -> None:
        """Remove entries older than RETENTION_DAYS."""
        cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
        original_count = len(self.history)
        
        self.history = [
            entry for entry in self.history
            if datetime.fromisoformat(entry['timestamp']) > cutoff
        ]
        
        removed = original_count - len(self.history)
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired topic history entries")
            self._save_cache()
    
    def record_usage(self, channel: str, topic: str) -> None:
        """
        Record that a topic was used for a channel.
        
        Args:
            channel: Channel name
            topic: Topic string that was used
        """
        self.history.append({
            'channel': channel,
            'topic': topic,
            'timestamp': datetime.now().isoformat()
        })
        self._save_cache()
        logger.info(f"Recorded topic usage: {channel} -> {topic[:50]}...")
    
    def get_usage_count(self, channel: str, topic: str) -> int:
        """
        Get how many times a topic was used for a channel in retention period.
        
        Args:
            channel: Channel name
            topic: Topic to check
            
        Returns:
            Number of times used
        """
        return sum(
            1 for entry in self.history
            if entry['channel'] == channel and entry['topic'] == topic
        )
    
    def get_recent_topics(self, channel: str, limit: int = 10) -> List[str]:
        """
        Get the most recently used topics for a channel.
        
        Args:
            channel: Channel name
            limit: Maximum number of topics to return
            
        Returns:
            List of recently used topic strings
        """
        channel_entries = [
            entry for entry in self.history
            if entry['channel'] == channel
        ]
        # Sort by timestamp descending
        channel_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Return unique topics in order
        seen = set()
        result = []
        for entry in channel_entries:
            if entry['topic'] not in seen:
                seen.add(entry['topic'])
                result.append(entry['topic'])
                if len(result) >= limit:
                    break
        return result
    
    def get_unused_topic(self, channel: str, available_topics: List[str]) -> Optional[str]:
        """
        Get a topic that hasn't been used yet for a channel.
        
        Args:
            channel: Channel name
            available_topics: List of all available topics
            
        Returns:
            An unused topic, or None if all have been used
        """
        used_topics = set(
            entry['topic'] for entry in self.history
            if entry['channel'] == channel
        )
        
        unused = [t for t in available_topics if t not in used_topics]
        
        if unused:
            import random
            return random.choice(unused)
        
        return None
    
    def get_least_used_topic(self, channel: str, available_topics: List[str]) -> str:
        """
        Get the least frequently used topic for a channel.
        If multiple have the same count, picks randomly among them.
        
        Args:
            channel: Channel name
            available_topics: List of all available topics
            
        Returns:
            The least used topic
        """
        import random
        
        # Count usage for each topic
        usage_counts = {}
        for topic in available_topics:
            usage_counts[topic] = self.get_usage_count(channel, topic)
        
        # Find minimum count
        min_count = min(usage_counts.values())
        
        # Get all topics with minimum count
        least_used = [t for t, c in usage_counts.items() if c == min_count]
        
        return random.choice(least_used)
    
    def get_smart_topic(self, channel: str, available_topics: List[str]) -> str:
        """
        Smart topic selection: prefer unused, fall back to least used.
        
        Args:
            channel: Channel name
            available_topics: List of all available topics
            
        Returns:
            Selected topic
        """
        # First try to get an unused topic
        unused = self.get_unused_topic(channel, available_topics)
        if unused:
            logger.info(f"Selected unused topic for {channel}")
            return unused
        
        # Fall back to least used
        logger.info(f"All topics used for {channel}, selecting least used")
        return self.get_least_used_topic(channel, available_topics)


# Global instance for easy access
_cache_instance: Optional[TopicCache] = None


def get_topic_cache() -> TopicCache:
    """Get or create the global TopicCache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TopicCache()
    return _cache_instance


if __name__ == "__main__":
    # Test the cache
    cache = get_topic_cache()
    
    test_topics = ["topic 1", "topic 2", "topic 3"]
    
    # Record some usage
    cache.record_usage("test_channel", "topic 1")
    cache.record_usage("test_channel", "topic 2")
    
    # Get smart topic (should return unused "topic 3")
    smart = cache.get_smart_topic("test_channel", test_topics)
    print(f"Smart topic selection: {smart}")
    
    # Get recent topics
    recent = cache.get_recent_topics("test_channel", limit=5)
    print(f"Recent topics: {recent}")
