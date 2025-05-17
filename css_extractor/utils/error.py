"""Error utility for CSS Extractor."""

class CSSExtractorError(Exception):
    """Base exception for CSS Extractor."""
    pass

class ValidationError(CSSExtractorError):
    """Raised when validation fails."""
    pass

class FileOperationError(CSSExtractorError):
    """Raised when file operations fail."""
    pass

class NetworkError(CSSExtractorError):
    """Raised when network operations fail."""
    pass

class ResourceLimitError(CSSExtractorError):
    """Raised when resource limits are exceeded."""
    pass

class ConfigurationError(CSSExtractorError):
    """Raised when configuration is invalid."""
    pass

class CacheError(CSSExtractorError):
    """Raised when cache operations fail."""
    pass

class MemoryError(CSSExtractorError):
    """Raised when memory operations fail."""
    pass

# Exported exceptions
__all__ = [
    'CSSExtractorError',
    'ValidationError',
    'FileOperationError',
    'NetworkError',
    'CacheError',
    'MemoryError',
    'ResourceLimitError',
    'ConfigurationError',
] 