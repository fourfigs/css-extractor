"""Retry functionality for handling transient failures."""

import time
import random
import logging
from functools import wraps
from typing import Callable, Any, Optional, Type, Tuple, Union

def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    **kwargs
) -> Any:
    """Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        retry_on_exceptions: Exception type(s) to retry on
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function call
        
    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
            
        except retry_on_exceptions as e:
            last_exception = e
            
            if attempt == max_retries:
                logging.error(f"All {max_retries} retry attempts failed")
                raise last_exception
                
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            
            # Add jitter if enabled
            if jitter:
                delay = delay * (0.5 + random.random())
                
            logging.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                f"Retrying in {delay:.2f} seconds..."
            )
            
            time.sleep(delay)
            
    raise last_exception

def retryable(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
) -> Callable:
    """Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        retry_on_exceptions: Exception type(s) to retry on
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retry_on_exceptions=retry_on_exceptions,
                **kwargs
            )
        return wrapper
    return decorator

class RetryContext:
    """Context manager for retrying operations."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
    ):
        """Initialize retry context.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retry_on_exceptions: Exception type(s) to retry on
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions
        self.attempt = 0
        self.last_exception = None
        
    def __enter__(self):
        """Enter the retry context."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the retry context."""
        if exc_type is None:
            return True
            
        if not isinstance(exc_val, self.retry_on_exceptions):
            return False
            
        self.last_exception = exc_val
        self.attempt += 1
        
        if self.attempt > self.max_retries:
            logging.error(f"All {self.max_retries} retry attempts failed")
            return False
            
        # Calculate delay with exponential backoff
        delay = min(self.base_delay * (self.exponential_base ** (self.attempt - 1)), self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random())
            
        logging.warning(
            f"Attempt {self.attempt}/{self.max_retries} failed: {str(exc_val)}. "
            f"Retrying in {delay:.2f} seconds..."
        )
        
        time.sleep(delay)
        return True  # Suppress the exception and retry 