"""HTML content handling functionality."""

import os
import re
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from .retry import retry_with_backoff
from .validation import validate_html_content

def get_html_content(source: str, verify_ssl: bool = True) -> str:
    """Get HTML content from a source (URL or file).
    
    Args:
        source: URL or file path
        verify_ssl: Whether to verify SSL certificates
        
    Returns:
        HTML content as string
        
    Raises:
        ValueError: If source is invalid
        requests.RequestException: If URL request fails
        IOError: If file read fails
    """
    try:
        if is_valid_url(source):
            return get_html_from_url(source, verify_ssl)
        else:
            return get_html_from_file(source)
            
    except Exception as e:
        logging.error(f"Error getting HTML content: {e}")
        raise

@retry_with_backoff
def get_html_from_url(url: str, verify_ssl: bool = True) -> str:
    """Get HTML content from a URL.
    
    Args:
        url: URL to fetch
        verify_ssl: Whether to verify SSL certificates
        
    Returns:
        HTML content as string
        
    Raises:
        requests.RequestException: If request fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, verify=verify_ssl, timeout=30)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            raise ValueError(f"Invalid content type: {content_type}")
            
        # Get encoding
        if response.encoding:
            html = response.content.decode(response.encoding)
        else:
            html = response.content.decode('utf-8')
            
        # Validate HTML
        if not validate_html_content(html):
            raise ValueError("Invalid HTML content")
            
        return html
        
    except requests.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        raise

def get_html_from_file(file_path: str) -> str:
    """Get HTML content from a file.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        HTML content as string
        
    Raises:
        IOError: If file read fails
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Detect encoding
        encoding = detect_encoding(file_path)
        
        # Read file
        with open(file_path, 'r', encoding=encoding) as f:
            html = f.read()
            
        # Validate HTML
        if not validate_html_content(html):
            raise ValueError("Invalid HTML content")
            
        return html
        
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        raise

def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML content.
    
    Args:
        html: HTML content to parse
        
    Returns:
        BeautifulSoup object
        
    Raises:
        ValueError: If HTML is invalid
    """
    try:
        if not validate_html_content(html):
            raise ValueError("Invalid HTML content")
            
        return BeautifulSoup(html, 'html.parser')
        
    except Exception as e:
        logging.error(f"Error parsing HTML: {e}")
        raise

def extract_meta_tags(html: str) -> Dict[str, Any]:
    """Extract meta tags from HTML.
    
    Args:
        html: HTML content
        
    Returns:
        Dictionary of meta tags
    """
    try:
        soup = parse_html(html)
        meta_tags = {}
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                meta_tags[name] = content
                
        return meta_tags
        
    except Exception as e:
        logging.error(f"Error extracting meta tags: {e}")
        return {}

def extract_title(html: str) -> Optional[str]:
    """Extract title from HTML.
    
    Args:
        html: HTML content
        
    Returns:
        Page title or None
    """
    try:
        soup = parse_html(html)
        title_tag = soup.find('title')
        return title_tag.string if title_tag else None
        
    except Exception as e:
        logging.error(f"Error extracting title: {e}")
        return None

def extract_base_url(html: str, current_url: str = '') -> Optional[str]:
    """Extract base URL from HTML.
    
    Args:
        html: HTML content
        current_url: Current URL for relative path resolution
        
    Returns:
        Base URL or None
    """
    try:
        soup = parse_html(html)
        
        # Check for base tag
        base_tag = soup.find('base', href=True)
        if base_tag:
            return urljoin(current_url, base_tag['href'])
            
        # Use current URL as base
        if current_url:
            return current_url
            
        return None
        
    except Exception as e:
        logging.error(f"Error extracting base URL: {e}")
        return None

def normalize_url(url: str, base_url: str = '') -> str:
    """Normalize URL.
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative path resolution
        
    Returns:
        Normalized URL
    """
    try:
        # Handle relative URLs
        if base_url and not urlparse(url).netloc:
            url = urljoin(base_url, url)
            
        # Remove fragments
        url = url.split('#')[0]
        
        # Normalize path
        parsed = urlparse(url)
        path = os.path.normpath(parsed.path).replace('\\', '/')
        
        # Reconstruct URL
        return parsed._replace(path=path).geturl()
        
    except Exception as e:
        logging.error(f"Error normalizing URL: {e}")
        return url

def detect_encoding(file_path: str) -> str:
    """Detect file encoding.
    
    Args:
        file_path: Path to file
        
    Returns:
        Detected encoding
    """
    try:
        import chardet
        
        # Read file in binary mode
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            
        # Detect encoding
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        
        # Fallback to utf-8 if detection fails
        if not encoding:
            encoding = 'utf-8'
            
        return encoding
        
    except Exception as e:
        logging.error(f"Error detecting encoding: {e}")
        return 'utf-8'

def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
        
    except Exception:
        return False 