"""Core CSS validation functionality."""

import re
from typing import List, Dict, Any, Optional
import logging

def validate_css_content(content: str) -> bool:
    """Validate CSS content."""
    try:
        if not content:
            return False
            
        # Check for basic CSS structure
        if not re.search(r'[^{}]*{[^}]*}', content):
            return False
            
        # Check for valid rules
        rules = split_css_rules(content)
        for rule in rules:
            if not validate_css_rule(rule):
                return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating CSS content: {e}")
        return False

def validate_css_rule(rule: str) -> bool:
    """Validate a single CSS rule."""
    try:
        # Check for valid selector and declaration block
        if not re.match(r'[^{}]*{[^}]*}', rule):
            return False
            
        # Extract selector and properties
        selector, properties = split_rule(rule)
        
        # Validate selector
        if not validate_selector(selector):
            return False
            
        # Validate properties
        if not validate_properties(properties):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating CSS rule: {e}")
        return False

def validate_selector(selector: str) -> bool:
    """Validate a CSS selector."""
    try:
        # Check for empty selector
        if not selector.strip():
            return False
            
        # Check for valid selector syntax
        if not re.match(r'^[a-zA-Z0-9_\-.*#:\[\]()\s>+~]+$', selector):
            return False
            
        # Check for balanced brackets
        if not is_balanced(selector, '[', ']'):
            return False
            
        # Check for balanced parentheses
        if not is_balanced(selector, '(', ')'):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating selector: {e}")
        return False

def validate_properties(properties: str) -> bool:
    """Validate CSS properties."""
    try:
        # Check for empty properties
        if not properties.strip():
            return False
            
        # Split properties
        prop_list = properties.split(';')
        
        # Validate each property
        for prop in prop_list:
            prop = prop.strip()
            if not prop:
                continue
                
            if not validate_property(prop):
                return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating properties: {e}")
        return False

def validate_property(property_str: str) -> bool:
    """Validate a single CSS property."""
    try:
        # Check for property name and value
        if ':' not in property_str:
            return False
            
        name, value = property_str.split(':', 1)
        name = name.strip()
        value = value.strip()
        
        # Validate property name
        if not validate_property_name(name):
            return False
            
        # Validate property value
        if not validate_property_value(value):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating property: {e}")
        return False

def validate_property_name(name: str) -> bool:
    """Validate a CSS property name."""
    try:
        # Check for empty name
        if not name:
            return False
            
        # Check for valid property name syntax
        if not re.match(r'^[a-zA-Z\-]+$', name):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating property name: {e}")
        return False

def validate_property_value(value: str) -> bool:
    """Validate a CSS property value."""
    try:
        # Check for empty value
        if not value:
            return False
            
        # Check for balanced quotes
        if not is_balanced(value, '"', '"'):
            return False
            
        # Check for balanced parentheses
        if not is_balanced(value, '(', ')'):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating property value: {e}")
        return False

def validate_html_content(content: str) -> bool:
    """Validate HTML content."""
    try:
        if not content:
            return False
            
        # Check for basic HTML structure
        if not re.search(r'<html[^>]*>.*</html>', content, re.DOTALL | re.IGNORECASE):
            return False
            
        # Check for balanced tags
        if not are_tags_balanced(content):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating HTML content: {e}")
        return False

def validate_url(url: str) -> bool:
    """Validate a URL."""
    try:
        if not url:
            return False
            
        # Check for valid URL syntax
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', url):
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating URL: {e}")
        return False

def split_css_rules(content: str) -> List[str]:
    """Split CSS content into individual rules."""
    try:
        # Split on closing braces, but keep the brace
        rules = re.split(r'(})', content)
        
        # Recombine rules
        processed_rules = []
        current_rule = ''
        for part in rules:
            current_rule += part
            if part.strip() == '}':
                if current_rule.strip():
                    processed_rules.append(current_rule.strip())
                current_rule = ''
        
        # Add any remaining content
        if current_rule.strip():
            processed_rules.append(current_rule.strip())
        
        return processed_rules
        
    except Exception as e:
        logging.error(f"Error splitting CSS rules: {e}")
        return [content]

def split_rule(rule: str) -> tuple:
    """Split a CSS rule into selector and properties."""
    try:
        # Find the first opening brace
        brace_pos = rule.find('{')
        if brace_pos == -1:
            return '', ''
            
        selector = rule[:brace_pos].strip()
        properties = rule[brace_pos + 1:-1].strip()
        
        return selector, properties
        
    except Exception as e:
        logging.error(f"Error splitting rule: {e}")
        return '', ''

def is_balanced(text: str, open_char: str, close_char: str) -> bool:
    """Check if brackets/parentheses are balanced in text."""
    try:
        count = 0
        for char in text:
            if char == open_char:
                count += 1
            elif char == close_char:
                count -= 1
                if count < 0:
                    return False
        return count == 0
        
    except Exception as e:
        logging.error(f"Error checking balanced characters: {e}")
        return False

def are_tags_balanced(html: str) -> bool:
    """Check if HTML tags are balanced."""
    try:
        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Remove self-closing tags
        html = re.sub(r'<[^>]+/>', '', html)
        
        # Find all tags
        tags = re.findall(r'<([^>]+)>', html)
        
        # Check balance
        stack = []
        for tag in tags:
            if tag.startswith('/'):
                if not stack:
                    return False
                if stack[-1] != tag[1:]:
                    return False
                stack.pop()
            else:
                stack.append(tag)
        
        return len(stack) == 0
        
    except Exception as e:
        logging.error(f"Error checking balanced tags: {e}")
        return False 