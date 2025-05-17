"""Security utilities for CSS Extractor."""

import os
import re
import hashlib
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manage security-related functionality."""
    
    def __init__(self):
        """Initialize security manager."""
        self.allowed_domains: List[str] = []
        self.blocked_domains: List[str] = []
        self.allowed_paths: List[str] = []
        self.blocked_paths: List[str] = []
        
    def add_allowed_domain(self, domain: str) -> None:
        """Add allowed domain.
        
        Args:
            domain: Domain to allow
        """
        if domain not in self.allowed_domains:
            self.allowed_domains.append(domain)
            
    def add_blocked_domain(self, domain: str) -> None:
        """Add blocked domain.
        
        Args:
            domain: Domain to block
        """
        if domain not in self.blocked_domains:
            self.blocked_domains.append(domain)
            
    def add_allowed_path(self, path: str) -> None:
        """Add allowed path.
        
        Args:
            path: Path to allow
        """
        if path not in self.allowed_paths:
            self.allowed_paths.append(path)
            
    def add_blocked_path(self, path: str) -> None:
        """Add blocked path.
        
        Args:
            path: Path to block
        """
        if path not in self.blocked_paths:
            self.blocked_paths.append(path)
            
    def is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is allowed, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Check blocked domains first
            if domain in self.blocked_domains:
                return False
                
            # Check allowed domains
            if self.allowed_domains:
                return domain in self.allowed_domains
                
            return True
        except Exception as e:
            logger.error(f"Error checking URL: {e}")
            return False
            
    def is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is allowed, False otherwise
        """
        try:
            # Check blocked paths first
            if path in self.blocked_paths:
                return False
                
            # Check allowed paths
            if self.allowed_paths:
                return path in self.allowed_paths
                
            return True
        except Exception as e:
            logger.error(f"Error checking path: {e}")
            return False
            
    def sanitize_url(self, url: str) -> Optional[str]:
        """Sanitize URL.
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL or None if invalid
        """
        try:
            parsed_url = urlparse(url)
            
            # Check scheme
            if parsed_url.scheme not in ['http', 'https']:
                return None
                
            # Check domain
            if not parsed_url.netloc:
                return None
                
            # Check path
            if not self.is_path_allowed(parsed_url.path):
                return None
                
            return url
        except Exception as e:
            logger.error(f"Error sanitizing URL: {e}")
            return None
            
    def sanitize_path(self, path: str) -> Optional[str]:
        """Sanitize path.
        
        Args:
            path: Path to sanitize
            
        Returns:
            Sanitized path or None if invalid
        """
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(path)
            
            # Check if path exists
            if not os.path.exists(abs_path):
                return None
                
            # Check if path is allowed
            if not self.is_path_allowed(abs_path):
                return None
                
            return abs_path
        except Exception as e:
            logger.error(f"Error sanitizing path: {e}")
            return None
            
    def validate_css(self, css: str) -> bool:
        """Validate CSS content.
        
        Args:
            css: CSS content to validate
            
        Returns:
            True if CSS is valid, False otherwise
        """
        try:
            # Check for basic CSS syntax
            if not re.match(r'^\s*[^{]*{[^}]*}\s*$', css):
                return False
                
            # Check for dangerous properties
            dangerous_properties = [
                'expression',
                'javascript:',
                'vbscript:',
                'data:',
                'url('
            ]
            
            for prop in dangerous_properties:
                if prop in css.lower():
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating CSS: {e}")
            return False
            
    def validate_html(self, html: str) -> bool:
        """Validate HTML content.
        
        Args:
            html: HTML content to validate
            
        Returns:
            True if HTML is valid, False otherwise
        """
        try:
            # Check for basic HTML syntax
            if not re.match(r'^\s*<[^>]+>.*</[^>]+>\s*$', html):
                return False
                
            # Check for dangerous tags
            dangerous_tags = [
                '<script',
                '<iframe',
                '<object',
                '<embed',
                '<applet'
            ]
            
            for tag in dangerous_tags:
                if tag in html.lower():
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating HTML: {e}")
            return False
            
    def hash_content(self, content: str) -> str:
        """Hash content.
        
        Args:
            content: Content to hash
            
        Returns:
            Hash of content
        """
        return hashlib.sha256(content.encode()).hexdigest()
        
    def verify_hash(self, content: str, hash_value: str) -> bool:
        """Verify content hash.
        
        Args:
            content: Content to verify
            hash_value: Hash value to verify against
            
        Returns:
            True if hash matches, False otherwise
        """
        return self.hash_content(content) == hash_value
        
    def get_file_permissions(self, path: str) -> Dict[str, bool]:
        """Get file permissions.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with permission information
        """
        try:
            return {
                'readable': os.access(path, os.R_OK),
                'writable': os.access(path, os.W_OK),
                'executable': os.access(path, os.X_OK)
            }
        except Exception as e:
            logger.error(f"Error getting file permissions: {e}")
            return {
                'readable': False,
                'writable': False,
                'executable': False
            }
            
    def check_file_integrity(self, path: str) -> bool:
        """Check file integrity.
        
        Args:
            path: Path to check
            
        Returns:
            True if file is intact, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(path):
                return False
                
            # Check file permissions
            permissions = self.get_file_permissions(path)
            if not permissions['readable']:
                return False
                
            # Check file size
            if os.path.getsize(path) == 0:
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking file integrity: {e}")
            return False
            
    def log_security_event(self, event: str, details: Dict[str, Any]) -> None:
        """Log security event.
        
        Args:
            event: Event description
            details: Event details
        """
        logger.warning(
            f"Security Event: {event}\n"
            f"Details: {details}"
        ) 