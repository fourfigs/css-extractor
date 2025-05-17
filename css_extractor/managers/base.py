"""Base manager class for CSS Extractor."""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from ..utils.error import CSSExtractorError

class BaseManager(ABC):
    """Base class for all resource managers."""
    
    def __init__(self):
        """Initialize base manager."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def check_resources(self) -> None:
        """Check resource usage against limits."""
        pass
        
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics."""
        pass
        
    def log_error(self, message: str, error: Optional[Exception] = None) -> None:
        """Log error message.
        
        Args:
            message: Error message
            error: Optional exception
        """
        if error:
            self.logger.error(f"{message}: {error}")
        else:
            self.logger.error(message)
            
    def log_warning(self, message: str) -> None:
        """Log warning message.
        
        Args:
            message: Warning message
        """
        self.logger.warning(message)
        
    def log_info(self, message: str) -> None:
        """Log info message.
        
        Args:
            message: Info message
        """
        self.logger.info(message)
        
    def log_debug(self, message: str) -> None:
        """Log debug message.
        
        Args:
            message: Debug message
        """
        self.logger.debug(message)
        
    def handle_error(self, error: Exception, message: str) -> None:
        """Handle error with logging and cleanup.
        
        Args:
            error: Exception to handle
            message: Error message
        """
        self.log_error(message, error)
        self.cleanup()
        raise CSSExtractorError(f"{message}: {error}")
        
    def cleanup(self) -> None:
        """Clean up resources."""
        pass
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

# Exported class
__all__ = ['BaseManager'] 