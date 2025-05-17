"""Cache management for CSS Extractor."""

import os
import time
import json
import hashlib
import logging
import threading
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from ..utils.concurrency import ThreadSafeDict, FileLock
from ..utils.error import CacheError

logger = logging.getLogger(__name__)

class CacheManager:
    """Manage CSS caching with size limits and expiration."""
    
    def __init__(self, cache_dir: str,
                 size_limit: int = 100 * 1024 * 1024,  # 100MB
                 expiration: int = 3600,  # 1 hour
                 cleanup_interval: int = 300):  # 5 minutes
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
            size_limit: Maximum cache size in bytes
            expiration: Cache entry expiration time in seconds
            cleanup_interval: Time between cleanup checks in seconds
            
        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate parameters
        if size_limit <= 0:
            raise ValueError("Size limit must be positive")
        if expiration <= 0:
            raise ValueError("Expiration time must be positive")
        if cleanup_interval <= 0:
            raise ValueError("Cleanup interval must be positive")
            
        self.cache_dir = Path(cache_dir)
        self.size_limit = size_limit
        self.expiration = expiration
        self.cleanup_interval = cleanup_interval
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata file
        self.metadata_file = self.cache_dir / 'metadata.json'
        
        # Initialize thread-safe metadata
        self.metadata = ThreadSafeDict()
        
        # Initialize locks
        self._metadata_lock = FileLock(str(self.metadata_file))
        self._cache_lock = FileLock(str(self.cache_dir / '.cache.lock'))
        
        # Initialize statistics
        self.stats = ThreadSafeDict()
        self.stats.update({
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'errors': 0,
            'start_time': time.time()
        })
        
        # Load metadata
        self._load_metadata()
        
        # Initialize last cleanup time
        self.last_cleanup = time.time()
        
    def _load_metadata(self) -> None:
        """Load cache metadata from file."""
        try:
            if self.metadata_file.exists():
                with self._metadata_lock:
                    with open(self.metadata_file, 'r') as f:
                        data = json.load(f)
                        self.metadata.update(data)
        except Exception as e:
            logger.error(f"Error loading cache metadata: {e}")
            self.metadata.clear()
            
    def _save_metadata(self) -> None:
        """Save cache metadata to file."""
        try:
            with self._metadata_lock:
                with open(self.metadata_file, 'w') as f:
                    json.dump(dict(self.metadata.items()), f)
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")
            
    def _clean_expired(self) -> None:
        """Clean expired cache entries."""
        try:
            with self._cache_lock:
                current_time = time.time()
                expired_keys = []
                
                for key, info in self.metadata.items():
                    if current_time - info['timestamp'] > self.expiration:
                        expired_keys.append(key)
                        
                for key in expired_keys:
                    # Remove file
                    cache_file = self.cache_dir / key
                    if cache_file.exists():
                        cache_file.unlink()
                        
                    # Remove metadata
                    del self.metadata[key]
                    self.stats['expirations'] += 1
                
                # Save metadata
                self._save_metadata()
        except Exception as e:
            logger.error(f"Error cleaning expired entries: {e}")
            self.stats['errors'] += 1
            
    def _check_size_limit(self) -> bool:
        """Check if cache size is within limit.
        
        Returns:
            True if within limit, False otherwise
        """
        try:
            total_size = sum(info['size'] for info in self.metadata.values())
            return total_size <= self.size_limit
        except Exception as e:
            logger.error(f"Error checking size limit: {e}")
            self.stats['errors'] += 1
            return False
            
    def _make_space(self, required_size: int) -> None:
        """Make space in cache for new entry.
        
        Args:
            required_size: Size of new entry in bytes
        """
        try:
            with self._cache_lock:
                if not self._check_size_limit():
                    # Sort entries by timestamp (oldest first)
                    sorted_entries = sorted(
                        self.metadata.items(),
                        key=lambda x: x[1]['timestamp']
                    )
                    
                    # Remove entries until we have enough space
                    for key, info in sorted_entries:
                        if self._check_size_limit():
                            break
                            
                        # Remove file
                        cache_file = self.cache_dir / key
                        if cache_file.exists():
                            cache_file.unlink()
                            
                        # Remove metadata
                        del self.metadata[key]
                        self.stats['evictions'] += 1
                    
                    # Save metadata
                    self._save_metadata()
        except Exception as e:
            logger.error(f"Error making space: {e}")
            self.stats['errors'] += 1
            
    def cache_css(self, css_content: str, key: Optional[str] = None) -> str:
        """Cache CSS content."""
        try:
            logger.debug("Starting cache_css operation")
            
            # Generate key if not provided
            if key is None:
                key = hashlib.sha256(css_content.encode()).hexdigest()
                # Add thread ID and UUID only for auto-generated keys
                thread_id = threading.get_ident()
                key = f"{key}_{thread_id}_{uuid.uuid4().hex}"
            logger.debug(f"Generated/Using key: {key}")
            
            content_size = len(css_content.encode())
            current_time = time.time()
            
            with self._cache_lock:
                # Write file atomically
                cache_file = self.cache_dir / key
                temp_file = self.cache_dir / f"{key}.tmp"
                logger.debug(f"Writing to file: {cache_file}")
                
                try:
                    # Write to temp file first
                    with open(temp_file, 'w') as f:
                        f.write(css_content)
                    
                    # Atomic rename
                    temp_file.rename(cache_file)
                    logger.debug("File write complete")
                    
                    # Update metadata
                    logger.debug("Updating metadata")
                    self.metadata[key] = {
                        'size': content_size,
                        'timestamp': current_time,
                        'original_key': key
                    }
                    
                    # Save metadata
                    logger.debug("Saving metadata")
                    self._save_metadata()
                    logger.debug("Metadata saved")
                    
                    # Check size limit
                    if not self._check_size_limit():
                        self._make_space(content_size)
                        
                    logger.debug("Cache operation completed")
                    return key
                    
                except Exception as e:
                    # Clean up temp file if it exists
                    if temp_file.exists():
                        temp_file.unlink()
                    raise e
                    
        except Exception as e:
            logger.error(f"Error caching CSS: {e}")
            self.stats['errors'] += 1
            raise CacheError(f"Failed to cache CSS: {e}")
            
    def get_cached_css(self, key: str) -> Optional[str]:
        """Get cached CSS content."""
        try:
            with self._cache_lock:
                if key not in self.metadata:
                    self.stats['misses'] += 1
                    return None
                
                info = self.metadata[key]
                if time.time() - info['timestamp'] > self.expiration:
                    self.remove_cached_css(key)
                    self.stats['expirations'] += 1
                    self.stats['misses'] += 1
                    return None
                
                cache_file = self.cache_dir / key
                if not cache_file.exists():
                    self.stats['misses'] += 1
                    return None
                
                # Read file
                with open(cache_file, 'r') as f:
                    content = f.read()
                
                self.stats['hits'] += 1
                return content
                
        except Exception as e:
            logger.error(f"Error getting cached CSS: {e}")
            self.stats['errors'] += 1
            return None
            
    def remove_cached_css(self, key: str) -> None:
        """Remove cached CSS content.
        
        Args:
            key: Cache key
        """
        try:
            with self._cache_lock:
                # Remove file with retry logic
                cache_file = self.cache_dir / key
                for _ in range(5):
                    try:
                        if cache_file.exists():
                            cache_file.unlink()
                        break
                    except PermissionError as e:
                        if hasattr(e, 'winerror') and e.winerror == 32:
                            time.sleep(0.1)
                        else:
                            raise
                # Remove metadata
                if key in self.metadata:
                    del self.metadata[key]
                # Save metadata
                self._save_metadata()
        except Exception as e:
            logger.error(f"Error removing cached CSS: {e}")
            self.stats['errors'] += 1
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            elapsed_time = time.time() - self.stats['start_time']
            total_requests = self.stats['hits'] + self.stats['misses']
            total_size = sum(info['size'] for info in self.metadata.values())
            
            return {
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions'],
                'expirations': self.stats['expirations'],
                'errors': self.stats['errors'],
                'hit_rate': self.stats['hits'] / total_requests if total_requests > 0 else 0,
                'miss_rate': self.stats['misses'] / total_requests if total_requests > 0 else 0,
                'total_size': total_size,
                'size_limit': self.size_limit,
                'total_entries': len(self.metadata),
                'elapsed_time': elapsed_time,
                'requests_per_second': total_requests / elapsed_time if elapsed_time > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expirations': 0,
                'errors': 0,
                'hit_rate': 0,
                'miss_rate': 0,
                'total_size': 0,
                'size_limit': self.size_limit,
                'total_entries': 0,
                'elapsed_time': 0,
                'requests_per_second': 0
            }
            
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        try:
            self.stats.update({
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expirations': 0,
                'errors': 0,
                'start_time': time.time()
            })
        except Exception as e:
            logger.error(f"Error resetting cache stats: {e}")
            
    def cleanup(self) -> None:
        """Clean up cache resources."""
        try:
            # Clean expired entries
            self._clean_expired()
            
            # Save metadata
            self._save_metadata()
            
            # Reset statistics
            self.reset_stats()
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            
    def __enter__(self) -> 'CacheManager':
        """Enter context manager."""
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.cleanup()

    def clear_cache(self) -> None:
        """Clear all cached content."""
        try:
            with self._cache_lock:
                # Remove all cache files with retry logic
                for file in self.cache_dir.glob('*'):
                    if file != self.metadata_file:
                        for _ in range(5):
                            try:
                                if file.exists():
                                    file.unlink()
                                break
                            except PermissionError as e:
                                if hasattr(e, 'winerror') and e.winerror == 32:
                                    time.sleep(0.1)
                                else:
                                    raise
                # Clear metadata
                self.metadata.clear()
                # Save empty metadata
                self._save_metadata()
                # Reset statistics
                self.reset_stats()
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            self.stats['errors'] += 1
            raise CacheError(f"Failed to clear cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return self.get_cache_stats()

# Exported class
__all__ = ['CacheManager'] 