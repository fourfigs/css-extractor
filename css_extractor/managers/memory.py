"""Memory management for CSS Extractor."""

import os
import gc
import time
import psutil
import logging
from typing import Dict, Any, Optional, List, Tuple
from ..utils.concurrency import ThreadSafeDict
from ..utils.error import MemoryError

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manage memory usage with leak detection."""
    
    def __init__(self, memory_limit: Optional[int] = None,
                 cleanup_interval: int = 300,
                 leak_threshold: float = 0.1,
                 warning_threshold: float = 0.8):
        """Initialize memory manager.
        
        Args:
            memory_limit: Maximum memory usage in bytes
            cleanup_interval: Time between cleanup checks in seconds
            leak_threshold: Threshold for memory leak detection (0.0 to 1.0)
            warning_threshold: Threshold for memory warning (0.0 to 1.0)
            
        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate parameters
        if memory_limit is not None and memory_limit <= 0:
            memory_limit = None  # Treat negative or zero limits as no limit
        if cleanup_interval <= 0:
            raise ValueError("Cleanup interval must be positive")
        if not 0 < leak_threshold < 1:
            raise ValueError("Leak threshold must be between 0 and 1")
        if not 0 < warning_threshold < 1:
            raise ValueError("Warning threshold must be between 0 and 1")
            
        self.memory_limit = memory_limit
        self.cleanup_interval = cleanup_interval
        self.leak_threshold = leak_threshold
        self.warning_threshold = warning_threshold
        
        # Initialize process
        self.process = psutil.Process()
        
        # Initialize memory history
        self.memory_history: List[Tuple[float, float]] = []  # (timestamp, memory_usage)
        self.max_history_size = 100  # Keep last 100 measurements
        
        # Initialize statistics
        self.stats = ThreadSafeDict()
        self.stats.update({
            'total_allocations': 0,
            'total_deallocations': 0,
            'peak_memory': 0,
            'current_memory': 0,
            'leak_count': 0,
            'warning_count': 0,
            'cleanup_count': 0,
            'start_time': time.time()
        })
        
        # Initialize last cleanup time
        self.last_cleanup = time.time()
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in bytes.
        
        Returns:
            Current memory usage in bytes
        """
        try:
            memory_info = self.process.memory_info()
            current_memory = memory_info.rss  # Resident Set Size
            
            # Update statistics
            self.stats['current_memory'] = current_memory
            if current_memory > self.stats['peak_memory']:
                self.stats['peak_memory'] = current_memory
                
            # Add to history
            self.memory_history.append((time.time(), current_memory))
            if len(self.memory_history) > self.max_history_size:
                self.memory_history.pop(0)
                
            return current_memory
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0
            
    def get_memory_percent(self) -> float:
        """Get memory usage as percentage of limit.
        
        Returns:
            Memory usage percentage (0.0 to 1.0)
        """
        try:
            if self.memory_limit is None:
                return 0.0
                
            current_memory = self.get_memory_usage()
            return current_memory / self.memory_limit
        except Exception as e:
            logger.error(f"Error getting memory percent: {e}")
            return 0.0
            
    def check_available_memory(self) -> bool:
        """Check if available memory is above the limit (if set)."""
        try:
            if self.memory_limit is None:
                return True  # Unlimited memory is always available
            if self.memory_limit <= 0:
                return False  # Zero or negative limit is not available
            return self.get_memory_usage() < self.memory_limit
        except Exception as e:
            logger.error(f"Error checking available memory: {e}")
            return False

    def is_memory_critical(self, threshold: float = None) -> bool:
        """Check if memory usage is critical.
        Args:
            threshold: Optional threshold (0.0 to 1.0). If not provided, uses self.warning_threshold.
        Returns:
            True if memory usage is critical, False otherwise
        """
        try:
            use_threshold = threshold if threshold is not None else self.warning_threshold
            return self.get_memory_percent() >= use_threshold
        except Exception as e:
            logger.error(f"Error checking memory critical: {e}")
            return False
            
    def detect_memory_leak(self) -> bool:
        """Detect memory leak by analyzing memory growth.
        
        Returns:
            True if memory leak is detected, False otherwise
        """
        try:
            if len(self.memory_history) < 2:
                return False
                
            # Calculate memory growth rate
            start_time, start_memory = self.memory_history[0]
            end_time, end_memory = self.memory_history[-1]
            
            if end_time <= start_time:
                return False
                
            time_diff = end_time - start_time
            memory_diff = end_memory - start_memory
            
            if time_diff <= 0:
                return False
                
            growth_rate = memory_diff / time_diff
            
            # Check if growth rate exceeds threshold
            if growth_rate > 0 and self.memory_limit is not None:
                leak_threshold_bytes = self.memory_limit * self.leak_threshold
                if growth_rate > leak_threshold_bytes:
                    self.stats['leak_count'] += 1
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error detecting memory leak: {e}")
            return False
            
    def force_garbage_collection(self) -> None:
        """Force garbage collection."""
        try:
            # Collect garbage
            collected = gc.collect()
            
            # Update statistics
            self.stats['total_deallocations'] += collected
            self.stats['cleanup_count'] += 1
            
            # Update last cleanup time
            self.last_cleanup = time.time()
            
            logger.info(f"Garbage collection: {collected} objects collected")
        except Exception as e:
            logger.error(f"Error in garbage collection: {e}")
            
    def check_and_cleanup(self) -> None:
        """Check memory usage and cleanup if needed."""
        try:
            current_time = time.time()
            
            # Check if cleanup interval has passed
            if current_time - self.last_cleanup >= self.cleanup_interval:
                # Check for memory leak
                if self.detect_memory_leak():
                    logger.warning("Memory leak detected, forcing cleanup")
                    self.force_garbage_collection()
                    
                # Check if memory usage is critical
                elif self.is_memory_critical():
                    logger.warning("Memory usage critical, forcing cleanup")
                    self.force_garbage_collection()
                    
                # Check if memory limit is exceeded
                elif self.memory_limit is not None and self.get_memory_usage() > self.memory_limit:
                    logger.warning("Memory limit exceeded, forcing cleanup")
                    self.force_garbage_collection()
        except Exception as e:
            logger.error(f"Error in check and cleanup: {e}")
            
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        try:
            current_memory = self.get_memory_usage()
            elapsed_time = time.time() - self.stats['start_time']
            
            return {
                'current_memory': current_memory,
                'peak_memory': self.stats['peak_memory'],
                'memory_limit': self.memory_limit,
                'memory_percent': self.get_memory_percent(),
                'total_allocations': self.stats['total_allocations'],
                'total_deallocations': self.stats['total_deallocations'],
                'leak_count': self.stats['leak_count'],
                'warning_count': self.stats['warning_count'],
                'cleanup_count': self.stats['cleanup_count'],
                'elapsed_time': elapsed_time,
                'allocation_rate': self.stats['total_allocations'] / elapsed_time if elapsed_time > 0 else 0,
                'deallocation_rate': self.stats['total_deallocations'] / elapsed_time if elapsed_time > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {
                'current_memory': 0,
                'peak_memory': 0,
                'memory_limit': self.memory_limit,
                'memory_percent': 0,
                'total_allocations': 0,
                'total_deallocations': 0,
                'leak_count': 0,
                'warning_count': 0,
                'cleanup_count': 0,
                'elapsed_time': 0,
                'allocation_rate': 0,
                'deallocation_rate': 0
            }
            
    def reset_stats(self) -> None:
        """Reset memory statistics."""
        try:
            self.stats.update({
                'total_allocations': 0,
                'total_deallocations': 0,
                'peak_memory': 0,
                'current_memory': 0,
                'leak_count': 0,
                'warning_count': 0,
                'cleanup_count': 0,
                'start_time': time.time()
            })
            self.memory_history.clear()
            self.last_cleanup = time.time()
        except Exception as e:
            logger.error(f"Error resetting memory stats: {e}")
            
    def cleanup(self) -> None:
        """Clean up memory resources."""
        try:
            # Force garbage collection
            self.force_garbage_collection()
            
            # Clear history
            self.memory_history.clear()
            
            # Reset statistics
            self.reset_stats()
        except Exception as e:
            logger.error(f"Error cleaning up memory: {e}")
            
    def __enter__(self) -> 'MemoryManager':
        """Enter context manager."""
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.cleanup()

    def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics (for compatibility with factory/tests)."""
        return self.get_memory_stats()

# Exported class
__all__ = ['MemoryManager'] 