"""Network management for CSS Extractor."""

import time
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple, Callable
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..utils.concurrency import ThreadSafeDict, RateLimiter, ThreadPool
from ..utils.error import NetworkError

logger = logging.getLogger(__name__)

class NetworkManager:
    """Manage network resources with connection pooling."""
    
    def __init__(self, max_requests: Optional[int] = None,
                 request_timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit: int = 10,
                 pool_connections: int = 100,
                 pool_maxsize: int = 100,
                 batch_size: int = 10,
                 batch_timeout: int = 5,
                 proxy: Optional[str] = None,
                 verify_ssl: bool = True):
        """Initialize network manager.
        
        Args:
            max_requests: Maximum number of concurrent requests
            request_timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            rate_limit: Maximum requests per second
            pool_connections: Number of connection pools
            pool_maxsize: Maximum size of each connection pool
            batch_size: Maximum number of requests per batch
            batch_timeout: Maximum time to wait for batch completion
            proxy: Optional proxy URL
            verify_ssl: Whether to verify SSL certificates
            
        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate parameters
        if request_timeout <= 0:
            raise ValueError("Request timeout must be positive")
        if max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        if rate_limit <= 0:
            raise ValueError("Rate limit must be positive")
        if pool_connections <= 0:
            raise ValueError("Pool connections must be positive")
        if pool_maxsize <= 0:
            raise ValueError("Pool maxsize must be positive")
        if batch_size <= 0:
            raise ValueError("Batch size must be positive")
        if batch_timeout <= 0:
            raise ValueError("Batch timeout must be positive")
            
        self.max_requests = max_requests
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.proxy = proxy
        self.verify_ssl = verify_ssl
        self.request_count = 0  # For backward compatibility with tests
        
        # Initialize session with connection pooling
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=Retry(
                total=max_retries,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=['GET', 'POST', 'HEAD', 'OPTIONS']
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Configure proxy if provided
        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
            
        # Configure SSL verification
        self.session.verify = verify_ssl
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rate_limit)
        
        # Initialize thread pool for request batching
        self.thread_pool = ThreadPool(max_workers=pool_maxsize)
        
        # Initialize request queue
        self.request_queue: List[Tuple[str, str, Dict[str, Any], float]] = []
        
        # Initialize statistics
        self.stats = ThreadSafeDict()
        self.stats.update({
            'request_count': 0,
            'error_count': 0,
            'total_bytes': 0,
            'start_time': time.time(),
            'batch_count': 0,
            'retry_count': 0,
            'ssl_errors': 0,
            'proxy_errors': 0,
            'dns_errors': 0,
            'pool_exhaustion': 0,
            'timeout_errors': 0,
            'connection_errors': 0
        })
        
    def check_network_usage(self) -> bool:
        """Check if network usage is within limits.
        
        Returns:
            True if within limits, False otherwise
        """
        try:
            if self.max_requests is None:
                return True
                
            return self.request_count < self.max_requests
        except Exception as e:
            logger.error(f"Error checking network usage: {e}")
            return False
            
    def make_request(self, url: str, method: str = 'GET',
                    priority: float = 1.0, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with rate limiting and retries.
        
        Args:
            url: URL to request
            method: HTTP method
            priority: Request priority (higher is more important)
            **kwargs: Additional request parameters
            
        Returns:
            Response object if successful, None otherwise
            
        Raises:
            NetworkError: If request fails due to network issues
        """
        try:
            if not self.check_network_usage():
                logger.warning("Network request limit reached")
                return None
                
            if not self.is_valid_url(url):
                logger.error(f"Invalid URL: {url}")
                return None
                
            # Add request to queue with priority
            self.request_queue.append((url, method, kwargs, priority))
            
            # Sort queue by priority
            self.request_queue.sort(key=lambda x: x[3], reverse=True)
            
            # Process batch if queue is full
            if len(self.request_queue) >= self.batch_size:
                return self._process_batch()
                
            # Process single request
            return self._make_single_request(url, method, **kwargs)
        except Exception as e:
            logger.error(f"Error making request: {e}")
            self.stats['error_count'] += 1
            raise NetworkError(f"Request failed: {e}")
            
    def _make_single_request(self, url: str, method: str,
                           **kwargs) -> Optional[requests.Response]:
        """Make a single HTTP request.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response object if successful, None otherwise
            
        Raises:
            NetworkError: If request fails due to network issues
        """
        try:
            # Apply rate limiting
            with self.rate_limiter:
                # Make request
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.request_timeout,
                    verify=self.verify_ssl,
                    **kwargs
                )
                
                # Update statistics
                self.stats['request_count'] += 1
                self.request_count += 1  # For backward compatibility
                self.stats['total_bytes'] += len(response.content)
                
                if not response.ok:
                    self.stats['error_count'] += 1
                    self.stats['retry_count'] += 1
                    
                return response
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error: {e}")
            self.stats['error_count'] += 1
            self.stats['ssl_errors'] += 1
            raise NetworkError(f"SSL error: {e}")
        except requests.exceptions.ProxyError as e:
            logger.error(f"Proxy error: {e}")
            self.stats['error_count'] += 1
            self.stats['proxy_errors'] += 1
            raise NetworkError(f"Proxy error: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            self.stats['error_count'] += 1
            self.stats['connection_errors'] += 1
            if "Name or service not known" in str(e):
                self.stats['dns_errors'] += 1
            raise NetworkError(f"Connection error: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            self.stats['error_count'] += 1
            self.stats['timeout_errors'] += 1
            raise NetworkError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            self.stats['error_count'] += 1
            raise NetworkError(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"Error making request: {e}")
            self.stats['error_count'] += 1
            raise NetworkError(f"Error making request: {e}")
            
    def _process_batch(self) -> Optional[requests.Response]:
        """Process a batch of requests.
        
        Returns:
            Response object if successful, None otherwise
            
        Raises:
            NetworkError: If batch processing fails
        """
        try:
            if not self.request_queue:
                return None
                
            # Get batch of requests
            batch = self.request_queue[:self.batch_size]
            self.request_queue = self.request_queue[self.batch_size:]
            
            # Check thread pool capacity
            if len(self.thread_pool._futures) >= self.thread_pool._max_workers:
                self.stats['pool_exhaustion'] += 1
                logger.warning("Thread pool exhausted, processing requests sequentially")
                return self._process_sequential(batch)
                
            # Submit batch to thread pool
            futures = []
            for url, method, kwargs, _ in batch:
                future = self.thread_pool.submit(
                    self._make_single_request,
                    url=url,
                    method=method,
                    **kwargs
                )
                futures.append(future)
                
            # Wait for batch completion
            start_time = time.time()
            while time.time() - start_time < self.batch_timeout:
                if all(future.done() for future in futures):
                    break
                time.sleep(0.1)
                
            # Get results
            responses = []
            for future in futures:
                try:
                    response = future.result()
                    if response is not None:
                        responses.append(response)
                except Exception as e:
                    logger.error(f"Error getting batch result: {e}")
                    
            self.stats['batch_count'] += 1
            
            # Return first successful response
            for response in responses:
                if response.ok:
                    return response
                    
            return None
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise NetworkError(f"Batch processing failed: {e}")
            
    def _process_sequential(self, batch: List[Tuple[str, str, Dict[str, Any], float]]) -> Optional[requests.Response]:
        """Process requests sequentially.
        
        Args:
            batch: List of requests to process
            
        Returns:
            Response object if successful, None otherwise
        """
        for url, method, kwargs, _ in batch:
            try:
                response = self._make_single_request(url, method, **kwargs)
                if response is not None and response.ok:
                    return response
            except Exception as e:
                logger.error(f"Error processing sequential request: {e}")
                continue
        return None
            
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            logger.error(f"Error validating URL: {e}")
            return False
            
    def extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain if valid, None otherwise
        """
        try:
            if not self.is_valid_url(url):
                return None
                
            return urlparse(url).netloc
        except Exception as e:
            logger.error(f"Error extracting domain: {e}")
            return None
            
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics.
        
        Returns:
            Dictionary with network statistics
        """
        try:
            return {
                'request_count': self.request_count,
                'max_requests': self.max_requests,
                'elapsed_time': time.time() - self.stats['start_time']
            }
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return {
                'request_count': 0,
                'max_requests': self.max_requests,
                'elapsed_time': 0
            }
            
    def reset_stats(self) -> None:
        """Reset network statistics."""
        try:
            self.stats.update({
                'request_count': 0,
                'error_count': 0,
                'total_bytes': 0,
                'start_time': time.time(),
                'batch_count': 0,
                'retry_count': 0,
                'ssl_errors': 0,
                'proxy_errors': 0,
                'dns_errors': 0,
                'pool_exhaustion': 0,
                'timeout_errors': 0,
                'connection_errors': 0
            })
            self.request_count = 0  # For backward compatibility
            self.request_queue.clear()
        except Exception as e:
            logger.error(f"Error resetting network stats: {e}")
            
    def cleanup(self) -> None:
        """Clean up network resources."""
        try:
            # Cancel any pending requests
            for future in self.thread_pool._futures:
                future.cancel()
                
            # Shutdown thread pool
            self.thread_pool.shutdown()
            
            # Close session
            self.session.close()
            
            # Clear queue
            self.request_queue.clear()
        except Exception as e:
            logger.error(f"Error cleaning up network: {e}")
            
    def __enter__(self) -> 'NetworkManager':
        """Enter context manager."""
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.cleanup()

    def get_stats(self) -> Dict[str, Any]:
        return self.get_network_stats()

# Exported class
__all__ = ['NetworkManager'] 