"""Concurrency utilities for CSS Extractor."""

import os
import time
import queue
import threading
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, RLock, Event

logger = logging.getLogger(__name__)

class ThreadSafeDict(dict):
    """Thread-safe dictionary implementation."""
    
    def __init__(self):
        """Initialize thread-safe dictionary."""
        super().__init__()
        self._lock = RLock()
        
    def __getitem__(self, key: str) -> Any:
        """Get item from dictionary.
        
        Args:
            key: Key to get
            
        Returns:
            Value for key
        """
        with self._lock:
            return super().__getitem__(key)
            
    def __setitem__(self, key: str, value: Any) -> None:
        """Set item in dictionary.
        
        Args:
            key: Key to set
            value: Value to set
        """
        with self._lock:
            super().__setitem__(key, value)
            
    def __delitem__(self, key: str) -> None:
        """Delete item from dictionary.
        
        Args:
            key: Key to delete
        """
        with self._lock:
            super().__delitem__(key)
            
    def __contains__(self, key: str) -> bool:
        """Check if key is in dictionary.
        
        Args:
            key: Key to check
            
        Returns:
            True if key is in dictionary, False otherwise
        """
        with self._lock:
            return super().__contains__(key)
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get item from dictionary with default.
        
        Args:
            key: Key to get
            default: Default value if key not found
            
        Returns:
            Value for key or default
        """
        with self._lock:
            return super().get(key, default)
            
    def items(self) -> List[tuple]:
        """Get all items from dictionary.
        
        Returns:
            List of (key, value) pairs
        """
        with self._lock:
            return list(super().items())
            
    def keys(self) -> List[str]:
        """Get all keys from dictionary.
        
        Returns:
            List of keys
        """
        with self._lock:
            return list(super().keys())
            
    def values(self) -> List[Any]:
        """Get all values from dictionary.
        
        Returns:
            List of values
        """
        with self._lock:
            return list(super().values())
            
    def clear(self) -> None:
        """Clear dictionary."""
        with self._lock:
            super().clear()
            
    def update(self, other: Dict[str, Any]) -> None:
        """Update dictionary with other dictionary.
        
        Args:
            other: Dictionary to update with
        """
        with self._lock:
            super().update(other)

    def __len__(self):
        with self._lock:
            return super().__len__()

    def __eq__(self, other):
        with self._lock:
            if isinstance(other, dict):
                return dict(self.items()) == other
            return super().__eq__(other)

class ThreadSafeSet:
    """Thread-safe set implementation."""
    
    def __init__(self):
        """Initialize thread-safe set."""
        self._set: Set[Any] = set()
        self._lock = RLock()
        
    def add(self, item: Any) -> None:
        """Add item to set.
        
        Args:
            item: Item to add
        """
        with self._lock:
            self._set.add(item)
            
    def remove(self, item: Any) -> None:
        """Remove item from set.
        
        Args:
            item: Item to remove
        """
        with self._lock:
            self._set.remove(item)
            
    def __contains__(self, item: Any) -> bool:
        """Check if item is in set.
        
        Args:
            item: Item to check
            
        Returns:
            True if item is in set, False otherwise
        """
        with self._lock:
            return item in self._set
            
    def clear(self) -> None:
        """Clear set."""
        with self._lock:
            self._set.clear()
            
    def update(self, other: Set[Any]) -> None:
        """Update set with other set.
        
        Args:
            other: Set to update with
        """
        with self._lock:
            self._set.update(other)

class ThreadPool:
    """Thread pool for concurrent operations."""
    
    def __init__(self, max_workers: Optional[int] = None):
        """Initialize thread pool.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: Set[Any] = set()
        self._lock = Lock()
        
    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Submit task to thread pool.
        
        Args:
            fn: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Future object
        """
        future = self.executor.submit(fn, *args, **kwargs)
        with self._lock:
            self._futures.add(future)
        return future
        
    def map(self, fn: Callable, *iterables: Any) -> List[Any]:
        """Map function over iterables.
        
        Args:
            fn: Function to execute
            *iterables: Iterables to map over
            
        Returns:
            List of results
        """
        return list(self.executor.map(fn, *iterables))
        
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown thread pool.
        
        Args:
            wait: Whether to wait for tasks to complete
        """
        self.executor.shutdown(wait=wait)
        
    def __enter__(self) -> 'ThreadPool':
        """Enter context manager."""
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.shutdown()

class FileLock:
    """File locking implementation."""
    
    def __init__(self, path: str):
        """Initialize file lock.
        
        Args:
            path: Path to lock
        """
        self.path = path
        self.lock_path = f"{path}.lock"
        self._lock = None
        self._pid = os.getpid()
        self._thread_id = threading.get_ident()
        self._lock_count = 0
        self._thread_lock = threading.RLock()
        
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire file lock.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        with self._thread_lock:
            if self._lock_count > 0:
                # Already locked by this thread
                self._lock_count += 1
                return True
                
            logger.debug(f"Attempting to acquire lock for {self.path}")
            start_time = time.time()
            while True:
                try:
                    # Try to create lock file
                    logger.debug(f"Creating lock file: {self.lock_path}")
                    self._lock = open(self.lock_path, 'x')
                    # Write PID and thread ID to lock file
                    self._lock.write(f"{self._pid}:{self._thread_id}")
                    self._lock.flush()
                    os.fsync(self._lock.fileno())
                    self._lock_count = 1
                    logger.debug("Lock acquired successfully")
                    return True
                except FileExistsError:
                    # Check if lock is stale
                    try:
                        logger.debug("Lock file exists, checking if stale")
                        with open(self.lock_path, 'r') as f:
                            pid_thread = f.read().strip().split(':')
                            if len(pid_thread) == 2:
                                pid, thread_id = map(int, pid_thread)
                                if pid == self._pid and thread_id == self._thread_id:
                                    # Lock is held by this thread
                                    self._lock_count += 1
                                    return True
                        # Check if process exists
                        try:
                            os.kill(pid, 0)
                            logger.debug(f"Lock is held by process {pid}")
                        except (OSError, ProcessLookupError):
                            # Process doesn't exist, remove stale lock
                            logger.debug(f"Lock is stale (process {pid} not found)")
                            try:
                                os.remove(self.lock_path)
                                logger.debug("Removed stale lock")
                                continue
                            except OSError:
                                logger.debug("Failed to remove stale lock")
                                pass
                    except (ValueError, OSError):
                        # Lock file is corrupted, remove it
                        logger.debug("Lock file is corrupted")
                        try:
                            os.remove(self.lock_path)
                            logger.debug("Removed corrupted lock")
                            continue
                        except OSError:
                            logger.debug("Failed to remove corrupted lock")
                            pass
                            
                    if timeout is not None and time.time() - start_time > timeout:
                        logger.debug("Lock acquisition timed out")
                        return False
                    time.sleep(0.1)
                
    def release(self) -> None:
        """Release file lock."""
        with self._thread_lock:
            if self._lock_count > 0:
                self._lock_count -= 1
                if self._lock_count == 0:
                    try:
                        logger.debug(f"Releasing lock for {self.path}")
                        if self._lock is not None:
                            self._lock.close()
                            self._lock = None
                        os.remove(self.lock_path)
                        logger.debug("Lock released successfully")
                    except OSError as e:
                        logger.debug(f"Error releasing lock: {e}")
                        pass
            
    def __enter__(self) -> 'FileLock':
        """Enter context manager."""
        if not self.acquire():
            raise TimeoutError("Failed to acquire file lock")
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.release()

class RateLimiter:
    """Rate limiter implementation."""
    
    def __init__(self, rate: float):
        """Initialize rate limiter.
        
        Args:
            rate: Rate in operations per second
        """
        self.rate = rate
        self.interval = 1.0 / rate
        self.last_time = 0.0
        self._lock = Lock()
        
    def acquire(self) -> None:
        """Acquire rate limit."""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_time
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_time = time.time()
            
    def __enter__(self) -> 'RateLimiter':
        """Enter context manager."""
        self.acquire()
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        pass

class Semaphore:
    """Semaphore implementation."""
    
    def __init__(self, value: int = 1):
        """Initialize semaphore.
        
        Args:
            value: Initial value
        """
        self._value = value
        self._lock = Lock()
        self._condition = threading.Condition(self._lock)
        
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire semaphore.
        
        Args:
            blocking: Whether to block
            timeout: Timeout in seconds
            
        Returns:
            True if acquired, False otherwise
        """
        with self._lock:
            if not blocking:
                if self._value <= 0:
                    return False
                self._value -= 1
                return True
                
            if timeout is None:
                while self._value <= 0:
                    self._condition.wait()
                self._value -= 1
                return True
                
            end_time = time.time() + timeout
            while self._value <= 0:
                remaining = end_time - time.time()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            self._value -= 1
            return True
            
    def release(self) -> None:
        """Release semaphore."""
        with self._lock:
            self._value += 1
            self._condition.notify()
            
    def __enter__(self) -> 'Semaphore':
        """Enter context manager."""
        self.acquire()
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.release()

class Event:
    """Event implementation."""
    
    def __init__(self):
        """Initialize event."""
        self._event = threading.Event()
        
    def set(self) -> None:
        """Set event."""
        self._event.set()
        
    def clear(self) -> None:
        """Clear event."""
        self._event.clear()
        
    def is_set(self) -> bool:
        """Check if event is set.
        
        Returns:
            True if event is set, False otherwise
        """
        return self._event.is_set()
        
    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for event.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            True if event is set, False if timeout
        """
        return self._event.wait(timeout) 