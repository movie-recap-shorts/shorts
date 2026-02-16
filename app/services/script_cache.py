import json
import os
from typing import Set, List
from datetime import datetime

class TopicCache:
    """Manages used topics to prevent content repetition/spam."""
    
    def __init__(self, cache_file: str = "topic_cache.json"):
        self.cache_file = cache_file
        self.used_topics: Set[str] = self._load_cache()

    def _load_cache(self) -> Set[str]:
        if not os.path.exists(self.cache_file):
            return set()
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                return set(data.get('used_topics', []))
        except Exception:
            return set()

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'used_topics': list(self.used_topics)
            }, f, indent=2)

    def is_used(self, topic: str) -> bool:
        """Check if a topic has already been used."""
        return topic.lower().strip() in self.used_topics

    def mark_used(self, topic: str):
        """Mark a topic as used."""
        if topic:
            self.used_topics.add(topic.lower().strip())
            self._save_cache()

    def filter_topics(self, topics: List[str]) -> List[str]:
        """Return only unused topics from a list."""
        return [t for t in topics if not self.is_used(t)]
