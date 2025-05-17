import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urljoin, urlparse
import validators
import time
import chardet
from pathlib import Path
import cssmin
import cssutils
import logging
import subprocess
import sys
import pkg_resources
import venv
import platform
import shutil
import tempfile
import socket
from packaging import version
from collections import defaultdict
import concurrent.futures
import hashlib
import json
from datetime import datetime
from tqdm import tqdm
import psutil
import gc
import ssl
import urllib3
from typing import Dict, List, Set, Optional, Union, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import weakref
import resource
import signal
from functools import lru_cache
import colorama
from colorama import Fore, Style
import glob

# Disable cssutils logging
cssutils.log.setLevel(logging.CRITICAL)

# Track processed imports to prevent circular dependencies
processed_imports = set()

# Maximum depth for nested imports
MAX_IMPORT_DEPTH = 10

# Maximum file size for CSS files (5MB)
MAX_CSS_SIZE = 5 * 1024 * 1024

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.css_cache')
CACHE_EXPIRY = 24 * 60 * 60  # 24 hours in seconds

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Logging settings
LOG_FILE = 'css_extractor.log'
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Resource limits
MAX_CPU_PERCENT = 80
MAX_MEMORY_PERCENT = 80
MAX_DISK_USAGE = 1024 * 1024 * 1024  # 1GB
MAX_NETWORK_BANDWIDTH = 1024 * 1024  # 1MB/s

# CSS feature flags
SUPPORTED_CSS_FEATURES = {
    'grid': True,
    'container': True,
    'nesting': True,
    'custom_properties': True,
    'houdini': False,
    'scroll_animations': True
}

# Progress bar settings
PROGRESS_BAR_WIDTH = 80
PROGRESS_BAR_COLOR = 'green'

# Directory scanning settings
SUPPORTED_EXTENSIONS = {'.html', '.htm', '.xhtml', '.php', '.asp', '.aspx', '.jsp'}
MAX_DIRECTORY_SIZE = 1024 * 1024 * 1024  # 1GB
MAX_FILES_TO_PROCESS = 1000
MAX_HTML_SIZE = 10 * 1024 * 1024  # 10MB

@dataclass
class ResourceLimits:
    cpu_percent: float = MAX_CPU_PERCENT
    memory_percent: float = MAX_MEMORY_PERCENT
    disk_usage: int = MAX_DISK_USAGE
    network_bandwidth: int = MAX_NETWORK_BANDWIDTH

class ResourceManager:
    """Manages system resources and limits"""
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self._lock = threading.Lock()
        self._resource_usage = {
            'cpu': 0,
            'memory': 0,
            'disk': 0,
            'network': 0
        }
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
        self._process = None
        self._start_time = None
        self._warning_count = defaultdict(int)
        self._warning_threshold = 3  # Number of warnings before taking action

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_monitoring()

    def start_monitoring(self):
        """Start resource monitoring"""
        if self._monitor_thread is None:
            self._stop_monitoring.clear()
            self._process = psutil.Process()
            self._start_time = time.time()
            self._monitor_thread = threading.Thread(target=self._monitor_resources)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop resource monitoring"""
        if self._monitor_thread is not None:
            self._stop_monitoring.set()
            self._monitor_thread.join(timeout=5.0)  # Wait up to 5 seconds
            self._monitor_thread = None
            self._process = None
            self._start_time = None
            self._warning_count.clear()

    def _monitor_resources(self):
        """Monitor system resources"""
        while not self._stop_monitoring.is_set():
            try:
                with self._lock:
                    if self._process is None:
                        break
                        
                    # Get current resource usage
                    self._resource_usage['cpu'] = self._process.cpu_percent()
                    self._resource_usage['memory'] = self._process.memory_percent()
                    self._resource_usage['disk'] = shutil.disk_usage('.').used
                    
                    # Check limits and take action if needed
                    self._check_and_handle_limits()
                    
                    # Reset warning counts if usage is below limits
                    if all(usage <= limit for usage, limit in zip(
                        [self._resource_usage['cpu'], self._resource_usage['memory'], 
                         self._resource_usage['disk']],
                        [self.limits.cpu_percent, self.limits.memory_percent, 
                         self.limits.disk_usage])):
                        self._warning_count.clear()
                
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error in resource monitoring: {e}")
                break

    def _check_and_handle_limits(self):
        """Check resource limits and take action if needed"""
        # Check CPU usage
        if self._resource_usage['cpu'] > self.limits.cpu_percent:
            self._warning_count['cpu'] += 1
            logging.warning(f"CPU usage exceeds limit: {self._resource_usage['cpu']}%")
            if self._warning_count['cpu'] >= self._warning_threshold:
                self._handle_high_cpu()

        # Check memory usage
        if self._resource_usage['memory'] > self.limits.memory_percent:
            self._warning_count['memory'] += 1
            logging.warning(f"Memory usage exceeds limit: {self._resource_usage['memory']}%")
            if self._warning_count['memory'] >= self._warning_threshold:
                self._handle_high_memory()

        # Check disk usage
        if self._resource_usage['disk'] > self.limits.disk_usage:
            self._warning_count['disk'] += 1
            logging.warning(f"Disk usage exceeds limit: {self._resource_usage['disk']} bytes")
            if self._warning_count['disk'] >= self._warning_threshold:
                self._handle_high_disk()

    def _handle_high_cpu(self):
        """Handle high CPU usage"""
        try:
            # Get CPU-intensive threads
            threads = self._process.threads()
            if threads:
                # Sort threads by CPU usage
                sorted_threads = sorted(threads, key=lambda t: t.cpu_percent(), reverse=True)
                # Log top CPU-consuming threads
                for thread in sorted_threads[:3]:
                    logging.warning(f"High CPU thread: {thread.id} ({thread.cpu_percent()}%)")
        except Exception as e:
            logging.error(f"Error handling high CPU: {e}")

    def _handle_high_memory(self):
        """Handle high memory usage"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Log memory usage details
            memory_info = self._process.memory_info()
            logging.warning(f"Memory details: RSS={memory_info.rss/1024/1024:.1f}MB, "
                          f"VMS={memory_info.vms/1024/1024:.1f}MB")
            
            # Check for memory leaks
            if self._start_time:
                elapsed_time = time.time() - self._start_time
                if elapsed_time > 300:  # 5 minutes
                    memory_growth = (memory_info.rss - self._resource_usage.get('initial_memory', 0)) / elapsed_time
                    if memory_growth > 1024 * 1024:  # 1MB per second
                        logging.error(f"Possible memory leak detected: {memory_growth/1024/1024:.1f}MB/s")
        except Exception as e:
            logging.error(f"Error handling high memory: {e}")

    def _handle_high_disk(self):
        """Handle high disk usage"""
        try:
            # Clean up temporary files
            cleanup_resources()
            
            # Log disk usage details
            disk_usage = shutil.disk_usage('.')
            logging.warning(f"Disk usage: {disk_usage.used/1024/1024:.1f}MB used, "
                          f"{disk_usage.free/1024/1024:.1f}MB free")
        except Exception as e:
            logging.error(f"Error handling high disk usage: {e}")

    def check_resources(self) -> bool:
        """Check if resources are within limits"""
        with self._lock:
            return all([
                self._resource_usage['cpu'] <= self.limits.cpu_percent,
                self._resource_usage['memory'] <= self.limits.memory_percent,
                self._resource_usage['disk'] <= self.limits.disk_usage,
                self._resource_usage['network'] <= self.limits.network_bandwidth
            ])

    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage"""
        with self._lock:
            return self._resource_usage.copy()

class CSSFeatureManager:
    """Manages CSS feature support and processing"""
    def __init__(self):
        self.supported_features = SUPPORTED_CSS_FEATURES
        self._feature_patterns = {
            'grid': r'display:\s*grid|grid-template|grid-area|grid-column|grid-row',
            'container': r'container-type|container-name|container-query',
            'nesting': r'&[^{]*{|@nest',
            'custom_properties': r'--[a-zA-Z0-9-]+|var\(--[a-zA-Z0-9-]+\)',
            'houdini': r'@property|@worklet',
            'scroll_animations': r'scroll-timeline|@scroll-timeline'
        }

    def detect_features(self, css_content: str) -> Dict[str, bool]:
        """Detect CSS features used in the content"""
        features = {}
        for feature, pattern in self._feature_patterns.items():
            features[feature] = bool(re.search(pattern, css_content))
        return features

    def process_features(self, css_content: str) -> str:
        """Process and optimize CSS features"""
        try:
            # Process CSS Grid
            if self.supported_features['grid']:
                css_content = self._process_grid(css_content)
            
            # Process Container Queries
            if self.supported_features['container']:
                css_content = self._process_container_queries(css_content)
            
            # Process CSS Nesting
            if self.supported_features['nesting']:
                css_content = self._process_nesting(css_content)
            
            # Process Custom Properties
            if self.supported_features['custom_properties']:
                css_content = self._process_custom_properties(css_content)
            
            return css_content
        
        except Exception as e:
            logging.error(f"Error processing CSS features: {e}")
            return css_content

    def _process_grid(self, css_content: str) -> str:
        """Process CSS Grid properties"""
        # Add vendor prefixes if needed
        grid_properties = {
            'display: grid': ['-ms-grid', '-webkit-grid'],
            'grid-template': ['-ms-grid-template'],
            'grid-area': ['-ms-grid-area'],
            'grid-column': ['-ms-grid-column'],
            'grid-row': ['-ms-grid-row']
        }
        
        for prop, prefixes in grid_properties.items():
            for prefix in prefixes:
                css_content = css_content.replace(prop, f"{prefix}; {prop}")
        
        return css_content

    def _process_container_queries(self, css_content: str) -> str:
        """Process Container Query properties"""
        # Add fallbacks for container queries
        container_pattern = r'@container\s+([^{]+){([^}]+)}'
        
        def add_fallback(match):
            query = match.group(1)
            content = match.group(2)
            return f"@container {query}{{{content}}}@media (min-width: 0px){{{content}}}"
        
        return re.sub(container_pattern, add_fallback, css_content)

    def _process_nesting(self, css_content: str) -> str:
        """Process CSS Nesting"""
        try:
            # Convert nesting to standard CSS
            nesting_pattern = r'&[^{]*{([^}]+)}'
            
            def convert_nesting(match):
                try:
                    nested_content = match.group(1)
                    # Process nested selectors
                    selectors = re.findall(r'([^{]+){', nested_content)
                    if not selectors:
                        return nested_content
                        
                    # Convert nested selectors to standard CSS
                    result = []
                    for selector in selectors:
                        selector = selector.strip()
                        if selector.startswith('&'):
                            # Handle parent reference
                            result.append(selector[1:])
                        else:
                            # Handle child selectors
                            result.append(f"& {selector}")
                    
                    return '\n'.join(result)
                    
                except Exception as e:
                    logging.warning(f"Error processing nested selector: {e}")
                    return nested_content
            
            return re.sub(nesting_pattern, convert_nesting, css_content)
            
        except Exception as e:
            logging.error(f"Error processing CSS nesting: {e}")
            return css_content

    def _process_custom_properties(self, css_content: str) -> str:
        """Process CSS Custom Properties"""
        # Add fallbacks for custom properties
        var_pattern = r'var\(--([^,)]+)(?:,\s*([^)]+))?\)'
        
        def add_fallback(match):
            var_name = match.group(1)
            fallback = match.group(2) or 'initial'
            return f"var(--{var_name}, {fallback})"
        
        return re.sub(var_pattern, add_fallback, css_content)

class CSSOptimizer:
    """Optimizes CSS by removing duplicates and unused rules"""
    def __init__(self):
        self._lock = threading.Lock()
        self._cache = {}
        self._cache_size = 0
        self._max_cache_size = 100 * 1024 * 1024  # 100MB
        self._cache_hits = 0
        self._cache_misses = 0
        self._error_count = defaultdict(int)
        self._max_errors = 3  # Maximum number of errors before giving up

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.clear_cache()

    def clear_cache(self):
        """Clear the optimization cache"""
        with self._lock:
            self._cache.clear()
            self._cache_size = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._error_count.clear()

    def optimize(self, css_content: str, html_content: Optional[str] = None) -> str:
        """Optimize CSS content"""
        try:
            # Check cache first
            cache_key = hash(css_content)
            with self._lock:
                if cache_key in self._cache:
                    self._cache_hits += 1
                    return self._cache[cache_key]

            self._cache_misses += 1

            # Validate input
            if not css_content or not isinstance(css_content, str):
                raise ValueError("Invalid CSS content")

            # Parse CSS
            try:
                sheet = cssutils.parseString(css_content)
            except Exception as e:
                logging.error(f"Error parsing CSS: {e}")
                return css_content

            # Remove duplicates
            try:
                self._remove_duplicates(sheet)
            except Exception as e:
                self._handle_optimization_error("duplicate removal", e)

            # Remove unused rules if HTML content is provided
            if html_content:
                try:
                    self._remove_unused(sheet, html_content)
                except Exception as e:
                    self._handle_optimization_error("unused rule removal", e)

            # Merge similar rules
            try:
                self._merge_rules(sheet)
            except Exception as e:
                self._handle_optimization_error("rule merging", e)

            # Reorder rules
            try:
                self._reorder_rules(sheet)
            except Exception as e:
                self._handle_optimization_error("rule reordering", e)

            # Get optimized CSS
            try:
                optimized_css = sheet.cssText.decode('utf-8')
            except Exception as e:
                logging.error(f"Error encoding optimized CSS: {e}")
                return css_content

            # Cache result if within size limit
            with self._lock:
                if len(optimized_css) <= self._max_cache_size:
                    self._cache[cache_key] = optimized_css
                    self._cache_size += len(optimized_css)

            return optimized_css

        except Exception as e:
            logging.error(f"Error in CSS optimization: {e}")
            return css_content

    def _handle_optimization_error(self, operation: str, error: Exception):
        """Handle optimization errors with retry logic"""
        self._error_count[operation] += 1
        logging.warning(f"Error during {operation}: {error}")
        
        if self._error_count[operation] >= self._max_errors:
            logging.error(f"Too many errors during {operation}, skipping")
            self._error_count[operation] = 0
        else:
            # Retry with exponential backoff
            time.sleep(2 ** self._error_count[operation])

    def _remove_duplicates(self, sheet: cssutils.css.CSSStyleSheet):
        """Remove duplicate CSS rules"""
        try:
            seen_rules = set()
            for rule in sheet:
                if not isinstance(rule, cssutils.css.CSSStyleRule):
                    continue

                normalized = self._normalize_rule(rule)
                if normalized in seen_rules:
                    sheet.deleteRule(rule)
                else:
                    seen_rules.add(normalized)
        except Exception as e:
            self._handle_optimization_error("duplicate removal", e)

    def _normalize_rule(self, rule: cssutils.css.CSSStyleRule) -> str:
        """Normalize a CSS rule for comparison"""
        try:
            # Sort properties
            props = sorted(str(p) for p in rule.style)
            # Sort selectors
            selectors = sorted(str(s) for s in rule.selectorList)
            return f"{' '.join(selectors)}{{{' '.join(props)}}}"
        except Exception as e:
            logging.error(f"Error normalizing rule: {e}")
            return str(rule)

    def _remove_unused(self, sheet: cssutils.css.CSSStyleSheet, html_content: str):
        """Remove unused CSS rules"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for rule in sheet:
                if not isinstance(rule, cssutils.css.CSSStyleRule):
                    continue

                if not self._is_rule_used(rule, soup):
                    sheet.deleteRule(rule)
        except Exception as e:
            self._handle_optimization_error("unused rule removal", e)

    def _is_rule_used(self, rule: cssutils.css.CSSStyleRule, soup: BeautifulSoup) -> bool:
        """Check if a CSS rule is used in the HTML"""
        try:
            for selector in rule.selectorList:
                try:
                    if soup.select(str(selector)):
                        return True
                except Exception as e:
                    logging.warning(f"Error checking selector {selector}: {e}")
            return False
        except Exception as e:
            logging.error(f"Error checking rule usage: {e}")
            return True  # Keep rule if we can't determine usage

    def _merge_rules(self, sheet: cssutils.css.CSSStyleSheet):
        """Merge similar CSS rules"""
        try:
            # Group rules by selector
            rule_groups = defaultdict(list)
            for rule in sheet:
                if not isinstance(rule, cssutils.css.CSSStyleRule):
                    continue

                for selector in rule.selectorList:
                    rule_groups[str(selector)].append(rule)

            # Merge rules in each group
            for selector, rules in rule_groups.items():
                if len(rules) > 1:
                    self._merge_rule_group(sheet, rules)
        except Exception as e:
            self._handle_optimization_error("rule merging", e)

    def _merge_rule_group(self, sheet: cssutils.css.CSSStyleSheet, rules: List[cssutils.css.CSSStyleRule]):
        """Merge a group of similar CSS rules"""
        try:
            # Create new rule with combined properties
            new_rule = cssutils.css.CSSStyleRule()
            new_rule.selectorList = rules[0].selectorList

            # Combine properties
            props = {}
            for rule in rules:
                for prop in rule.style:
                    props[prop.name] = prop.value

            # Add properties to new rule
            for name, value in props.items():
                new_rule.style[name] = value

            # Replace old rules with new one
            for rule in rules:
                sheet.deleteRule(rule)
            sheet.add(new_rule)
        except Exception as e:
            self._handle_optimization_error("rule group merging", e)

    def _reorder_rules(self, sheet: cssutils.css.CSSStyleSheet):
        """Reorder CSS rules by specificity and importance"""
        try:
            # Get all rules
            rules = []
            for rule in sheet:
                if isinstance(rule, cssutils.css.CSSStyleRule):
                    rules.append(rule)

            # Sort rules by priority
            rules.sort(key=self._rule_priority)

            # Reorder rules in sheet
            for rule in rules:
                sheet.deleteRule(rule)
                sheet.add(rule)
        except Exception as e:
            self._handle_optimization_error("rule reordering", e)

    def _rule_priority(self, rule: cssutils.css.CSSStyleRule) -> Tuple[int, int, int]:
        """Calculate priority for rule ordering"""
        try:
            # Count important declarations
            important_count = sum(1 for prop in rule.style if prop.priority == 'important')
            
            # Count selectors
            selector_count = len(rule.selectorList)
            
            # Calculate specificity
            specificity = 0
            for selector in rule.selectorList:
                specificity += len(selector.selectorText.split('#'))  # IDs
                specificity += len(selector.selectorText.split('.'))  # Classes
                specificity += len(selector.selectorText.split(':'))  # Pseudo-classes
            
            return (-important_count, -specificity, -selector_count)
        except Exception as e:
            logging.error(f"Error calculating rule priority: {e}")
            return (0, 0, 0)

class ProgressReporter:
    """Handles progress reporting and user feedback"""
    def __init__(self, total_steps=5):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = None
        self.step_times = {}
        self._progress_bar = None
        colorama.init()

    def start(self):
        """Start progress reporting"""
        self.start_time = datetime.now()
        self._progress_bar = tqdm(
            total=self.total_steps,
            desc="Processing",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
            colour=PROGRESS_BAR_COLOR
        )

    def update(self, step_name: str, message: str = None):
        """Update progress"""
        self.current_step += 1
        step_time = datetime.now() - self.start_time
        self.step_times[step_name] = step_time
        
        if self._progress_bar:
            self._progress_bar.update(1)
            if message:
                self._progress_bar.set_description(f"{step_name}: {message}")
            else:
                self._progress_bar.set_description(step_name)

    def finish(self):
        """Finish progress reporting"""
        if self._progress_bar:
            self._progress_bar.close()
        
        # Print summary
        print(f"\n{Fore.GREEN}Processing completed successfully!{Style.RESET_ALL}")
        print("\nStep timing summary:")
        for step, time in self.step_times.items():
            print(f"  {step}: {time.total_seconds():.2f}s")
        
        total_time = datetime.now() - self.start_time
        print(f"\nTotal processing time: {total_time.total_seconds():.2f}s")

    def error(self, message: str):
        """Report an error"""
        if self._progress_bar:
            self._progress_bar.close()
        print(f"\n{Fore.RED}Error: {message}{Style.RESET_ALL}")

class UserInterface:
    """Handles user interface and interaction"""
    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.output_format = 'text'
        colorama.init()

    def set_verbosity(self, verbose: bool, quiet: bool):
        """Set verbosity level"""
        self.verbose = verbose
        self.quiet = quiet

    def set_output_format(self, format: str):
        """Set output format"""
        self.output_format = format

    def print_info(self, message: str):
        """Print information message"""
        if not self.quiet:
            print(f"{Fore.BLUE}Info: {message}{Style.RESET_ALL}")

    def print_warning(self, message: str):
        """Print warning message"""
        if not self.quiet:
            print(f"{Fore.YELLOW}Warning: {message}{Style.RESET_ALL}")

    def print_error(self, message: str):
        """Print error message"""
        if not self.quiet:
            print(f"{Fore.RED}Error: {message}{Style.RESET_ALL}")

    def print_success(self, message: str):
        """Print success message"""
        if not self.quiet:
            print(f"{Fore.GREEN}Success: {message}{Style.RESET_ALL}")

    def print_debug(self, message: str):
        """Print debug message"""
        if self.verbose and not self.quiet:
            print(f"{Fore.CYAN}Debug: {message}{Style.RESET_ALL}")

    def print_progress(self, current: int, total: int, message: str = None):
        """Print progress"""
        if not self.quiet:
            progress = (current / total) * 100
            if message:
                print(f"\rProgress: {progress:.1f}% - {message}", end='')
            else:
                print(f"\rProgress: {progress:.1f}%", end='')
            if current == total:
                print()

    def format_output(self, data: dict) -> str:
        """Format output data"""
        if self.output_format == 'json':
            return json.dumps(data, indent=2)
        elif self.output_format == 'text':
            return self._format_text_output(data)
        else:
            return str(data)

    def _format_text_output(self, data: dict) -> str:
        """Format output as text"""
        output = []
        for key, value in data.items():
            if isinstance(value, dict):
                output.append(f"{key}:")
                for k, v in value.items():
                    output.append(f"  {k}: {v}")
            else:
                output.append(f"{key}: {value}")
        return "\n".join(output)

class ImportManager:
    """Manages CSS imports and prevents circular dependencies"""
    def __init__(self):
        self._processed_imports = set()
        self._import_depth = 0
        self._lock = threading.Lock()
        self._max_imports = 1000  # Maximum number of imports to track
        self._import_times = {}  # Track import times for cleanup
        self._import_cache = {}  # Cache for imported CSS content
        self._cache_lock = threading.Lock()

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.clear()

    def clear(self):
        """Clear processed imports and cache"""
        with self._lock:
            self._processed_imports.clear()
            self._import_depth = 0
            self._import_times.clear()
        with self._cache_lock:
            self._import_cache.clear()

    def _cleanup_old_imports(self):
        """Remove old imports to prevent unbounded growth"""
        with self._lock:
            if len(self._processed_imports) > self._max_imports:
                # Remove oldest imports
                current_time = time.time()
                old_imports = [imp for imp, t in self._import_times.items() 
                             if current_time - t > 3600]  # Remove imports older than 1 hour
                for imp in old_imports:
                    self._processed_imports.remove(imp)
                    del self._import_times[imp]
                with self._cache_lock:
                    for imp in old_imports:
                        self._import_cache.pop(imp, None)

    def _get_cached_import(self, import_url: str) -> Optional[str]:
        """Get cached import content if valid"""
        with self._cache_lock:
            if import_url in self._import_cache:
                content, timestamp = self._import_cache[import_url]
                if time.time() - timestamp < CACHE_EXPIRY:
                    return content
                del self._import_cache[import_url]
        return None

    def _cache_import(self, import_url: str, content: str):
        """Cache imported content"""
        with self._cache_lock:
            self._import_cache[import_url] = (content, time.time())

    def process_imports(self, css_content: str, base_url: str, verify_ssl: bool = True) -> str:
        """Process @import rules with circular dependency detection and media query support"""
        with self._lock:
            if self._import_depth >= MAX_IMPORT_DEPTH:
                logging.warning(f"Maximum import depth ({MAX_IMPORT_DEPTH}) reached")
                return css_content
            
            self._import_depth += 1
            
            try:
                # Cleanup old imports
                self._cleanup_old_imports()
                
                # Find all @import rules with media queries
                import_pattern = r'@import\s+(?:url\()?[\'"]([^\'"]+)[\'"]\)?(?:\s+([^;]+))?;'
                imports = re.findall(import_pattern, css_content)
                
                # Remove @import rules from the content
                css_content = re.sub(import_pattern, '', css_content)
                
                # Process each import
                for import_url, media_query in imports:
                    if import_url in self._processed_imports:
                        logging.warning(f"Circular import detected for {import_url}")
                        continue
                        
                    self._processed_imports.add(import_url)
                    self._import_times[import_url] = time.time()
                    
                    # Check cache first
                    imported_css = self._get_cached_import(import_url)
                    if imported_css is None:
                        # Normalize the import URL
                        import_url = normalize_url(import_url, base_url)
                        
                        try:
                            if is_valid_url(import_url):
                                logging.info(f"Processing import: {import_url}")
                                imported_css = get_css_from_url(import_url, verify_ssl=verify_ssl)
                            else:
                                full_path = resolve_relative_path(base_url, import_url)
                                if full_path:
                                    logging.info(f"Processing import: {full_path}")
                                    try:
                                        encoding = detect_encoding(full_path)
                                        with open(full_path, 'r', encoding=encoding) as f:
                                            imported_css = f.read()
                                    except Exception as e:
                                        logging.error(f"Error reading imported file {full_path}: {e}")
                                        imported_css = None
                                else:
                                    imported_css = None
                                    
                            if imported_css:
                                # Cache the imported content
                                self._cache_import(import_url, imported_css)
                                
                                # Process nested imports
                                imported_css = self.process_imports(imported_css, base_url, verify_ssl=verify_ssl)
                                
                                # Wrap imported CSS in media query if specified
                                if media_query:
                                    imported_css = f"@media {media_query} {{\n{imported_css}\n}}"
                                
                                css_content += '\n' + imported_css
                        except Exception as e:
                            logging.error(f"Error processing import {import_url}: {e}")
                            continue
                
                return css_content
            finally:
                self._import_depth -= 1

def check_python_version():
    """Check if Python version is compatible"""
    required_version = '3.6'
    current_version = platform.python_version()
    if version.parse(current_version) < version.parse(required_version):
        print(f"Error: Python {required_version} or higher is required. Current version: {current_version}")
        sys.exit(1)

def check_pip_version():
    """Check if pip version is compatible"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        pip_version = result.stdout.split()[1]
        if version.parse(pip_version) < version.parse('19.0'):
            print(f"Warning: pip version {pip_version} is older than recommended. Some features may not work correctly.")
    except Exception as e:
        print(f"Warning: Could not check pip version: {e}")

def is_venv():
    """Check if running in a virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def get_python_executable():
    """Get the correct Python executable path"""
    if platform.system() == 'Windows':
        return os.path.join(sys.prefix, 'python.exe')
    return sys.executable

def create_venv():
    """Create a virtual environment if not in one"""
    if not is_venv():
        print("Creating virtual environment...")
        # Use a temporary directory for initial creation
        temp_dir = tempfile.mkdtemp()
        venv_path = os.path.join(temp_dir, 'venv')
        
        try:
            # Create venv in temporary directory
            venv.create(venv_path, with_pip=True)
            
            # Determine the correct python executable path
            if platform.system() == 'Windows':
                python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
            else:
                python_path = os.path.join(venv_path, 'bin', 'python')
            
            # Verify the Python executable exists
            if not os.path.exists(python_path):
                raise FileNotFoundError(f"Python executable not found at {python_path}")
            
            # Move the venv to the final location
            final_venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv')
            if os.path.exists(final_venv_path):
                shutil.rmtree(final_venv_path)
            shutil.move(venv_path, final_venv_path)
            
            # Update python_path to point to the final location
            python_path = os.path.join(final_venv_path, 'Scripts' if platform.system() == 'Windows' else 'bin', 
                                     'python.exe' if platform.system() == 'Windows' else 'python')
            
            print(f"Virtual environment created at {final_venv_path}")
            
            # Restart the script in the virtual environment
            print("Restarting in virtual environment...")
            # Use subprocess instead of os.execv for better Windows compatibility
            subprocess.run([python_path, __file__] + sys.argv[1:], check=True)
            sys.exit(0)
            
        except Exception as e:
            print(f"Error creating virtual environment: {e}")
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            print("Continuing without virtual environment...")
        finally:
            # Clean up temporary directory if it still exists
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

def get_package_name(package):
    """Get the correct package name for pip"""
    package_map = {
        'beautifulsoup4': 'bs4',
        'cssutils': 'cssutils',
        'cssmin': 'cssmin',
        'chardet': 'chardet',
        'validators': 'validators',
        'requests': 'requests'
    }
    return package_map.get(package.lower(), package)

def check_pip_available():
    """Check if pip is available and working"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      timeout=10)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def install_package(package_spec, timeout=300):
    """Install a single package with timeout"""
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--user", package_spec
        ], check=True, timeout=timeout)
        return True
    except subprocess.CalledProcessError:
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                package_spec
            ], check=True, timeout=timeout)
            return True
        except subprocess.CalledProcessError:
            return False
    except subprocess.TimeoutExpired:
        print(f"Timeout while installing {package_spec}")
        return False

def check_requirements():
    """Check and install required packages"""
    if not check_pip_available():
        print("Error: pip is not available. Please install pip first.")
        sys.exit(1)

    required = {
        'requests': '2.31.0',
        'beautifulsoup4': '4.12.2',
        'validators': '0.22.0',
        'chardet': '5.2.0',
        'cssmin': '0.2.0',
        'cssutils': '2.9.0',
        'packaging': '23.2'  # Added for version comparison
    }
    
    missing = []
    outdated = []
    
    # Check installed packages
    installed = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    for package, version in required.items():
        pip_name = get_package_name(package)
        if pip_name.lower() not in installed:
            missing.append(f"{package}=={version}")
        elif installed[pip_name.lower()] != version:
            outdated.append(f"{package}=={version}")
    
    if missing or outdated:
        print("Checking and installing required packages...")
        packages_to_install = missing + outdated
        
        if packages_to_install:
            print("Installing required packages...")
            failed_packages = []
            
            # Install packages one by one
            for package in packages_to_install:
                print(f"Installing {package}...")
                if not install_package(package):
                    failed_packages.append(package)
            
            if failed_packages:
                print("\nFailed to install some packages:")
                for package in failed_packages:
                    print(f"- {package}")
                print("\nPlease try one of the following:")
                print("1. Run as administrator/with sudo")
                print(f"2. Install packages manually: pip install {' '.join(failed_packages)}")
                print("3. Create a virtual environment and try again")
                sys.exit(1)
            
            print("All required packages have been installed successfully!")
            
            # Reload the script to use newly installed packages
            print("Reloading script to use newly installed packages...")
            subprocess.run([sys.executable, __file__] + sys.argv[1:], check=True)
            sys.exit(0)
    else:
        print("All required packages are installed and up to date!")

def check_file_permissions(path):
    """Check if we have read/write permissions for a path"""
    try:
        if os.path.exists(path):
            # Check read permission
            if not os.access(path, os.R_OK):
                return False, "No read permission"
            # Check write permission
            if not os.access(path, os.W_OK):
                return False, "No write permission"
        else:
            # Check if we can create the file
            try:
                with open(path, 'a'):
                    pass
                os.remove(path)
            except:
                return False, "Cannot create file"
        return True, "OK"
    except Exception as e:
        return False, str(e)

def get_html_content(source, headers=None, verify_ssl=True):
    """Get HTML content from either a URL or local file"""
    if is_valid_url(source):
        try:
            # Set a reasonable timeout
            response = requests.get(source, headers=headers, timeout=30, verify=verify_ssl)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching URL {source}: {e}")
            return None
    elif is_valid_file_path(source):
        try:
            # Check file permissions
            can_access, error_msg = check_file_permissions(source)
            if not can_access:
                print(f"Error accessing file {source}: {error_msg}")
                return None

            # Check file size (limit to 10MB)
            file_size = os.path.getsize(source)
            if file_size > 10 * 1024 * 1024:  # 10MB
                print(f"Warning: File size ({file_size/1024/1024:.1f}MB) exceeds 10MB limit")
                return None
                
            encoding = detect_encoding(source)
            with open(source, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {source}: {e}")
            return None
    else:
        print(f"Error: {source} is neither a valid URL nor a valid file path")
        return None

def normalize_path(path):
    """Normalize path to handle both forward and backward slashes"""
    try:
        return str(Path(path).resolve())
    except Exception as e:
        print(f"Error normalizing path {path}: {e}")
        return path

def is_valid_url(url):
    return validators.url(url)

def is_valid_file_path(path):
    try:
        return os.path.isfile(normalize_path(path))
    except Exception:
        return False

def detect_encoding(file_path):
    """Detect file encoding"""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result['encoding'] or 'utf-8'

def is_data_url(url):
    """Check if URL is a data URL"""
    return url.startswith('data:')

def is_protocol_relative(url):
    """Check if URL is protocol-relative"""
    return url.startswith('//')

def normalize_url(url, base_url=''):
    """Normalize URL to handle different formats"""
    if is_data_url(url):
        return url
    if is_protocol_relative(url):
        return f"https:{url}"
    if base_url and not url.startswith(('http://', 'https://', 'data:', '/')):
        return urljoin(base_url, url)
    return url

def process_css_rules(css_content, base_url=''):
    """Process special CSS rules and variables with improved URL handling"""
    try:
        # Check CSS size
        if len(css_content.encode('utf-8')) > MAX_CSS_SIZE:
            print(f"Warning: CSS content size exceeds limit ({MAX_CSS_SIZE/1024/1024:.1f}MB)")
            return css_content
        
        # Parse CSS
        sheet = cssutils.parseString(css_content)
        
        # Process CSS variables and rules
        for rule in sheet:
            try:
                if rule.type == rule.STYLE_RULE:
                    for property in rule.style:
                        if property.name.startswith('--'):
                            # Keep CSS variable definitions
                            continue
                        elif 'var(' in property.value:
                            # Keep CSS variable usage
                            continue
                        elif 'url(' in property.value:
                            # Handle URL resources
                            url_match = re.search(r'url\([\'"]?([^\'"]+)[\'"]?\)', property.value)
                            if url_match:
                                url = url_match.group(1)
                                if not is_data_url(url) and not url.startswith(('http://', 'https://', '/')):
                                    # Convert relative URL to absolute
                                    absolute_url = normalize_url(url, base_url)
                                    property.value = property.value.replace(url, absolute_url)
                
                # Keep @keyframes rules
                elif rule.type == rule.KEYFRAMES_RULE:
                    continue
                    
                # Keep @font-face rules
                elif rule.type == rule.FONT_FACE_RULE:
                    continue
                    
                # Keep @supports rules
                elif rule.type == rule.SUPPORTS_RULE:
                    continue
                    
                # Keep @media rules
                elif rule.type == rule.MEDIA_RULE:
                    continue
                    
                # Keep @charset rules
                elif rule.type == rule.CHARSET_RULE:
                    continue
                    
                # Keep @namespace rules
                elif rule.type == rule.NAMESPACE_RULE:
                    continue
                    
            except Exception as e:
                print(f"Warning: Error processing CSS rule: {e}")
                continue
        
        return sheet.cssText
    except Exception as e:
        print(f"Error processing CSS rules: {e}")
        return css_content

def clean_css(css, minify=False):
    """Clean and optionally minify CSS while preserving special rules"""
    try:
        # Process special CSS rules first
        css = process_css_rules(css)
        
        if minify:
            # Preserve important rules before minification
            important_rules = []
            
            # Extract @charset rules
            charset_rules = re.findall(r'@charset\s+[^;]+;', css)
            important_rules.extend(charset_rules)
            css = re.sub(r'@charset\s+[^;]+;', '', css)
            
            # Extract @namespace rules
            namespace_rules = re.findall(r'@namespace\s+[^;]+;', css)
            important_rules.extend(namespace_rules)
            css = re.sub(r'@namespace\s+[^;]+;', '', css)
            
            # Extract @import rules
            import_rules = re.findall(r'@import\s+[^;]+;', css)
            important_rules.extend(import_rules)
            css = re.sub(r'@import\s+[^;]+;', '', css)
            
            # Extract @keyframes rules
            keyframes_rules = re.findall(r'@keyframes\s+[^{]+{[^}]+}', css, re.DOTALL)
            important_rules.extend(keyframes_rules)
            css = re.sub(r'@keyframes\s+[^{]+{[^}]+}', '', css, flags=re.DOTALL)
            
            # Extract @font-face rules
            fontface_rules = re.findall(r'@font-face\s*{[^}]+}', css, re.DOTALL)
            important_rules.extend(fontface_rules)
            css = re.sub(r'@font-face\s*{[^}]+}', '', css, flags=re.DOTALL)
            
            # Extract @supports rules
            supports_rules = re.findall(r'@supports\s*{[^}]+}', css, re.DOTALL)
            important_rules.extend(supports_rules)
            css = re.sub(r'@supports\s*{[^}]+}', '', css, flags=re.DOTALL)
            
            # Extract @media rules
            media_rules = re.findall(r'@media\s*{[^}]+}', css, re.DOTALL)
            important_rules.extend(media_rules)
            css = re.sub(r'@media\s*{[^}]+}', '', css, flags=re.DOTALL)
            
            # Minify the remaining CSS
            minified_css = cssmin.cssmin(css)
            
            # Restore important rules
            css = '\n'.join(important_rules) + '\n' + minified_css
            
            # Remove source map comments
            css = re.sub(r'/\*#\s*sourceMappingURL=[^*]+\*/', '', css)
        else:
            # Preserve comments
            comments = re.findall(r'/\*.*?\*/', css, re.DOTALL)
            css = re.sub(r'/\*.*?\*/', 'COMMENT_PLACEHOLDER', css, flags=re.DOTALL)
            
            # Clean up whitespace while preserving special rules
            css = re.sub(r'\s+', ' ', css)
            css = re.sub(r'}\s*{', '}\n{', css)
            css = re.sub(r'}\s*', '}\n', css)
            css = re.sub(r'@media\s*{', '@media {\n', css)
            css = re.sub(r'@keyframes\s*{', '@keyframes {\n', css)
            css = re.sub(r'@font-face\s*{', '@font-face {\n', css)
            css = re.sub(r'@supports\s*{', '@supports {\n', css)
            css = re.sub(r'@charset\s*', '@charset ', css)
            css = re.sub(r'@namespace\s*', '@namespace ', css)
            
            # Restore comments
            for comment in comments:
                css = css.replace('COMMENT_PLACEHOLDER', comment, 1)
        
        # Validate CSS
        try:
            cssutils.parseString(css)
        except Exception as e:
            print(f"Warning: CSS validation error: {e}")
            # Try to fix common CSS issues
            css = re.sub(r'([^;])\s*}', r'\1;}', css)  # Add missing semicolons
            css = re.sub(r'}\s*{', '}\n{', css)  # Fix rule separation
            css = re.sub(r'([^}])\s*{', r'\1 {', css)  # Fix rule opening
            
            # Try validation again
            try:
                cssutils.parseString(css)
            except Exception as e:
                print(f"Warning: Could not fix CSS validation error: {e}")
        
        return css
    except Exception as e:
        print(f"Error cleaning CSS: {e}")
        return css

def validate_css_content(css_content: str) -> bool:
    """Validate CSS content before processing"""
    try:
        if not css_content or not isinstance(css_content, str):
            return False
            
        # Check for basic CSS syntax
        if not re.search(r'[{}]', css_content):
            return False
            
        # Check for balanced braces
        brace_count = 0
        for char in css_content:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count < 0:
                    return False
        if brace_count != 0:
            return False
            
        # Try parsing with cssutils
        try:
            cssutils.parseString(css_content)
            return True
        except:
            return False
            
    except Exception as e:
        logging.error(f"Error validating CSS content: {e}")
        return False

def validate_html_content(html_content: str) -> bool:
    """Validate HTML content before processing"""
    try:
        if not html_content or not isinstance(html_content, str):
            return False
            
        # Check for basic HTML structure
        if not re.search(r'<[^>]+>', html_content):
            return False
            
        # Try parsing with BeautifulSoup
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return bool(soup.find())
        except:
            return False
        finally:
            if 'soup' in locals():
                soup.decompose()
                
    except Exception as e:
        logging.error(f"Error validating HTML content: {e}")
        return False

def extract_css_from_html(html_content: str, base_url: str = '') -> str:
    """Extract CSS from HTML content with improved validation"""
    try:
        if not html_content:
            return ''
            
        # Validate HTML content
        if not validate_html_content(html_content):
            raise ValueError("Invalid HTML content")
            
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        try:
            # Initialize CSS content
            css_content = []
            
            # Extract inline styles
            for style in soup.find_all('style'):
                if style.string:
                    css_content.append(style.string)
            
            # Extract external stylesheets
            for link in soup.find_all('link', rel='stylesheet'):
                href = link.get('href')
                if href:
                    css_url = normalize_url(href, base_url)
                    if is_valid_url(css_url):
                        external_css = get_css_from_url(css_url, verify_ssl=True)
                        if external_css and validate_css_content(external_css):
                            css_content.append(external_css)
                    else:
                        # Handle local CSS files
                        css_path = resolve_relative_path(base_url, href)
                        if css_path and os.path.exists(css_path):
                            try:
                                with open(css_path, 'r', encoding=detect_encoding(css_path)) as f:
                                    css = f.read()
                                    if validate_css_content(css):
                                        css_content.append(css)
                            except Exception as e:
                                logging.error(f"Error reading CSS file {css_path}: {e}")
            
            # Combine all CSS
            combined_css = '\n'.join(css_content)
            
            # Validate combined CSS
            if not validate_css_content(combined_css):
                raise ValueError("Invalid CSS content after combination")
            
            # Process imports using ImportManager
            import_manager = ImportManager()
            try:
                combined_css = import_manager.process_imports(combined_css, base_url, verify_ssl=True)
                if not validate_css_content(combined_css):
                    raise ValueError("Invalid CSS content after processing imports")
            finally:
                import_manager.clear()
            
            # Process CSS rules
            combined_css = process_css_rules(combined_css, base_url)
            if not validate_css_content(combined_css):
                raise ValueError("Invalid CSS content after processing rules")
            
            return combined_css
            
        finally:
            # Clean up BeautifulSoup
            soup.decompose()
            
    except Exception as e:
        logging.error(f"Error extracting CSS from HTML: {e}")
        return ''

def get_css_from_url(url: str, verify_ssl: bool = True, headers: Optional[Dict] = None) -> str:
    """Get CSS content from URL with improved validation and error handling"""
    try:
        # Validate URL
        if not is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")
            
        # Check cache first
        cached_content = get_from_cache(url)
        if cached_content and validate_css_content(cached_content):
            logging.info(f"Using cached content for {url}")
            return cached_content

        # Set default headers if none provided
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

        # Set up session with retry strategy
        session = requests.Session()
        retry_strategy = urllib3.Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Make request with timeout
        response = session.get(
            url,
            headers=headers,
            timeout=(5, 30),  # (connect timeout, read timeout)
            verify=verify_ssl,
            stream=True
        )
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'text/css' not in content_type and 'text/plain' not in content_type:
            logging.warning(f"Unexpected content type {content_type} for {url}")
        
        # Check file size
        content_length = int(response.headers.get('content-length', 0))
        if content_length > MAX_CSS_SIZE:
            raise ValueError(f"CSS file size ({content_length/1024/1024:.1f}MB) exceeds limit ({MAX_CSS_SIZE/1024/1024:.1f}MB)")
        
        # Read content in chunks with progress bar
        content = []
        total_size = 0
        with tqdm(total=content_length, unit='iB', unit_scale=True, desc=f"Downloading {url}") as pbar:
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    content.append(chunk)
                    chunk_size = len(chunk.encode('utf-8'))
                    total_size += chunk_size
                    pbar.update(chunk_size)
                    if total_size > MAX_CSS_SIZE:
                        raise ValueError("CSS file size exceeds limit while downloading")
        
        css_content = ''.join(content)
        
        # Validate CSS content
        if not validate_css_content(css_content):
            raise ValueError(f"Invalid CSS content from {url}")
        
        # Save to cache
        save_to_cache(url, css_content)
        
        return css_content
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        if hasattr(e.response, 'status_code'):
            logging.error(f"Status code: {e.response.status_code}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error fetching {url}: {e}")
        raise
    finally:
        if 'session' in locals():
            session.close()

def get_cache_path(url):
    """Get cache file path for a URL"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.css")

def is_cache_valid(cache_path):
    """Check if cache file is valid and not expired"""
    if not os.path.exists(cache_path):
        return False
    cache_time = os.path.getmtime(cache_path)
    return (time.time() - cache_time) < CACHE_EXPIRY

def save_to_cache(url, content):
    """Save CSS content to cache"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = get_cache_path(url)
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logging.warning(f"Failed to save to cache: {e}")

def get_from_cache(url):
    """Get CSS content from cache if valid"""
    cache_path = get_cache_path(url)
    if is_cache_valid(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.warning(f"Failed to read from cache: {e}")
    return None

def check_memory_usage():
    """Check if memory usage is within acceptable limits"""
    process = psutil.Process()
    memory_percent = process.memory_percent()
    
    if memory_percent > 80:  # 80% memory usage threshold
        logging.warning(f"High memory usage detected: {memory_percent:.1f}%")
        return False
    return True

def create_backup(file_path):
    """Create a backup of the file before processing"""
    try:
        backup_path = f"{file_path}.bak"
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return None

def retry_with_backoff(func, *args, max_retries: int = 3, initial_delay: float = 1.0, 
                      max_delay: float = 10.0, backoff_factor: float = 2.0, **kwargs):
    """Retry a function with exponential backoff"""
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(min(delay, max_delay))
                delay *= backoff_factor
    
    raise last_exception

def resolve_relative_path(base_path, relative_path):
    """Resolve relative path properly"""
    try:
        # Handle both forward and backward slashes
        relative_path = relative_path.replace('\\', '/')
        base_path = str(Path(base_path).parent)
        
        # Handle different types of relative paths
        if relative_path.startswith('./'):
            relative_path = relative_path[2:]
        elif relative_path.startswith('../'):
            # Count number of parent directory references
            parent_count = len(re.findall(r'^\.\./', relative_path))
            base_parts = Path(base_path).parts
            if parent_count >= len(base_parts):
                print(f"Error: Too many parent directory references in {relative_path}")
                return None
            base_path = str(Path(*base_parts[:-parent_count]))
            relative_path = relative_path[3*parent_count:]
        
        # Combine paths
        full_path = os.path.join(base_path, relative_path)
        return normalize_path(full_path)
    except Exception as e:
        print(f"Error resolving path {relative_path}: {e}")
        return None

def scan_directory(directory_path: str) -> List[str]:
    """Scan directory for HTML files"""
    try:
        directory_path = Path(directory_path).resolve()
        if not directory_path.is_dir():
            return []
            
        # Check directory size
        total_size = sum(f.stat().st_size for f in directory_path.rglob('*') if f.is_file())
        if total_size > MAX_DIRECTORY_SIZE:
            print(f"Warning: Directory size ({total_size/1024/1024:.1f}MB) exceeds limit ({MAX_DIRECTORY_SIZE/1024/1024:.1f}MB)")
            return []
            
        # Find all HTML files
        html_files = []
        for ext in SUPPORTED_EXTENSIONS:
            html_files.extend(directory_path.rglob(f'*{ext}'))
            
        # Limit number of files to process
        if len(html_files) > MAX_FILES_TO_PROCESS:
            print(f"Warning: Found {len(html_files)} files, limiting to {MAX_FILES_TO_PROCESS}")
            html_files = html_files[:MAX_FILES_TO_PROCESS]
            
        return [str(f) for f in html_files]
    except Exception as e:
        print(f"Error scanning directory {directory_path}: {e}")
        return []

def is_directory(path: str) -> bool:
    """Check if path is a directory"""
    try:
        return Path(path).is_dir()
    except Exception:
        return False

def extract_css_from_directory(directory_path: str, output_dir: str = None, **kwargs) -> Dict[str, Any]:
    """Extract CSS from all HTML files in a directory"""
    try:
        # Initialize UI
        ui = UserInterface()
        ui.set_verbosity(kwargs.get('verbose', False), kwargs.get('quiet', False))
        ui.set_output_format(kwargs.get('output_format', 'text'))
        
        # Initialize progress reporter
        progress = ProgressReporter(total_steps=4)
        progress.start()
        
        # Initialize resource manager
        resource_manager = ResourceManager()
        resource_manager.start_monitoring()
        
        # Initialize CSS feature manager
        feature_manager = CSSFeatureManager()
        
        # Initialize CSS optimizer
        css_optimizer = CSSOptimizer()
        
        # Check directory size
        progress.update("Directory Check", "Checking directory size...")
        total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(directory_path)
                        for filename in filenames)
        
        if total_size > MAX_DIRECTORY_SIZE:
            raise ValueError(f"Directory size exceeds limit of {MAX_DIRECTORY_SIZE / (1024 * 1024)}MB")
        
        # Create output directory if specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Validate output directory path
            if not output_dir.is_absolute():
                output_dir = output_dir.resolve()
            
            # Check for path traversal
            if not str(output_dir).startswith(str(Path.cwd())):
                raise ValueError("Output directory must be within current working directory")
        
        # Scan directory for HTML files
        progress.update("File Scan", "Scanning for HTML files...")
        html_files = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(('.html', '.htm', '.xhtml', '.php', '.asp', '.aspx', '.jsp')):
                    html_files.append(os.path.join(root, file))
        
        if not html_files:
            raise ValueError("No HTML files found in directory")
        
        if len(html_files) > MAX_FILES_TO_PROCESS:
            raise ValueError(f"Too many files to process (max: {MAX_FILES_TO_PROCESS})")
        
        # Process files in parallel
        progress.update("CSS Extraction", "Extracting CSS from files...")
        results = {}
        with ThreadPoolExecutor(max_workers=min(os.cpu_count(), 4)) as executor:
            future_to_file = {
                executor.submit(process_single_file, file, output_dir, feature_manager, css_optimizer, **kwargs): file
                for file in html_files
            }
            
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    result = future.result()
                    results[file] = result
                except Exception as e:
                    results[file] = {'status': 'error', 'error': str(e)}
        
        # Finish progress reporting
        progress.finish()
        
        # Print summary
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        error_count = len(results) - success_count
        
        ui.print_info(f"Processed {len(results)} files:")
        ui.print_success(f"✓ {success_count} files processed successfully")
        if error_count > 0:
            ui.print_error(f"✗ {error_count} files failed")
        
        return {
            'status': 'success',
            'total_files': len(results),
            'successful_files': success_count,
            'failed_files': error_count,
            'results': results,
            'processing_time': (datetime.now() - progress.start_time).total_seconds()
        }
        
    except Exception as e:
        if 'progress' in locals():
            progress.error(str(e))
        if 'ui' in locals():
            ui.print_error(str(e))
        raise
    finally:
        if 'resource_manager' in locals():
            resource_manager.stop_monitoring()
        cleanup_resources()

def process_single_file(file_path: str, output_dir: Path, feature_manager: CSSFeatureManager, 
                       css_optimizer: CSSOptimizer, **kwargs) -> Dict[str, Any]:
    """Process a single HTML file"""
    try:
        # Read HTML content
        with open(file_path, 'r', encoding=detect_encoding(file_path)) as f:
            html_content = f.read()
        
        # Extract CSS
        combined_css = extract_css_from_html(html_content, os.path.dirname(file_path))
        
        # Process CSS features
        combined_css = feature_manager.process_features(combined_css)
        
        # Optimize CSS
        combined_css = css_optimizer.optimize(combined_css, html_content)
        
        # Clean up the CSS
        cleaned_css = clean_css(combined_css, kwargs.get('minify', False))
        
        # Determine output path
        if output_dir:
            rel_path = os.path.relpath(file_path, os.path.dirname(file_path))
            output_path = output_dir / f"{os.path.splitext(rel_path)[0]}.css"
        else:
            output_path = Path(file_path).with_suffix('.css')
        
        # Save CSS
        save_css_to_file(cleaned_css, str(output_path))
        
        return {
            'status': 'success',
            'output_file': str(output_path),
            'css_size': len(cleaned_css),
            'features_detected': feature_manager.detect_features(cleaned_css)
        }
        
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

def cleanup_resources():
    """Clean up temporary files and resources"""
    try:
        # Clean up cache directory
        if os.path.exists(CACHE_DIR):
            for root, dirs, files in os.walk(CACHE_DIR, topdown=False):
                for name in files:
                    try:
                        file_path = os.path.join(root, name)
                        # Check if file is still in use
                        if not is_file_in_use(file_path):
                            os.remove(file_path)
                        else:
                            logging.warning(f"File {file_path} is still in use, skipping deletion")
                    except Exception as e:
                        logging.error(f"Error removing file {name}: {e}")
                
                for name in dirs:
                    try:
                        dir_path = os.path.join(root, name)
                        # Only remove empty directories
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except Exception as e:
                        logging.error(f"Error removing directory {name}: {e}")
            
            # Remove cache directory if empty
            if not os.listdir(CACHE_DIR):
                os.rmdir(CACHE_DIR)
                logging.info("Cache directory removed")

        # Clean up temporary files
        temp_dir = tempfile.gettempdir()
        for filename in os.listdir(temp_dir):
            if filename.startswith('css_extractor_'):
                try:
                    file_path = os.path.join(temp_dir, filename)
                    # Check if file is still in use
                    if not is_file_in_use(file_path):
                        os.remove(file_path)
                    else:
                        logging.warning(f"Temporary file {file_path} is still in use, skipping deletion")
                except Exception as e:
                    logging.error(f"Error removing temporary file {filename}: {e}")

        # Force garbage collection
        gc.collect()
        
        # Clear any remaining file handles
        for handle in psutil.Process().open_files():
            try:
                if handle.path.startswith(CACHE_DIR) or 'css_extractor_' in handle.path:
                    os.close(handle.fd)
            except Exception as e:
                logging.error(f"Error closing file handle {handle.path}: {e}")

        logging.info("Resource cleanup completed")
    except Exception as e:
        logging.error(f"Error during resource cleanup: {e}")

def is_file_in_use(file_path: str) -> bool:
    """Check if a file is currently in use by any process"""
    try:
        # Try to open the file in exclusive mode
        with open(file_path, 'a+b') as f:
            # If we can open it, it's not in use
            return False
    except (IOError, PermissionError):
        # If we can't open it, it's probably in use
        return True
    except Exception as e:
        logging.error(f"Error checking if file {file_path} is in use: {e}")
        # Assume file is in use if we can't determine
        return True

def save_css_to_file(css_content: str, output_file: str) -> None:
    """Save CSS content to file with improved validation and error handling"""
    try:
        # Validate CSS content
        if not validate_css_content(css_content):
            raise ValueError("Invalid CSS content")
            
        # Validate output path
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = output_path.resolve()
        
        # Check for path traversal
        if not str(output_path).startswith(str(Path.cwd())):
            raise ValueError("Output file must be within current working directory")
        
        # Create directory if it doesn't exist
        output_dir = output_path.parent
        if output_dir:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Error creating output directory {output_dir}: {e}")
        
        # Check write permissions
        if output_path.exists():
            if not os.access(str(output_path), os.W_OK):
                raise ValueError(f"No write permission for {output_file}")
        else:
            try:
                # Test if we can create the file
                with open(str(output_path), 'a'):
                    pass
                os.remove(str(output_path))
            except Exception as e:
                raise ValueError(f"Cannot create file {output_file}: {e}")
        
        # Create backup if file exists
        backup_path = None
        if output_path.exists():
            backup_path = output_path.with_suffix('.css.bak')
            try:
                shutil.copy2(str(output_path), str(backup_path))
            except Exception as e:
                logging.warning(f"Could not create backup of {output_file}: {e}")
        
        # Write CSS content
        try:
            with open(str(output_path), 'w', encoding='utf-8') as f:
                f.write(css_content)
        except Exception as e:
            # Restore backup if write fails
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(str(backup_path), str(output_path))
                except Exception as restore_error:
                    logging.error(f"Error restoring backup: {restore_error}")
            raise ValueError(f"Error writing to file {output_file}: {e}")
            
    except Exception as e:
        raise ValueError(f"Error saving CSS to file {output_file}: {e}")
    finally:
        # Clean up backup if write was successful
        if backup_path and backup_path.exists():
            try:
                os.remove(str(backup_path))
            except Exception as e:
                logging.warning(f"Could not remove backup file {backup_path}: {e}")

def extract_css(source: str, output_file: str = 'style.css', verify_ssl: bool = True, 
               minify: bool = False, verbose: bool = False, quiet: bool = False, 
               output_format: str = 'text') -> Dict[str, Any]:
    """Main function to extract CSS from a source"""
    try:
        # Initialize UI
        ui = UserInterface()
        ui.set_verbosity(verbose, quiet)
        ui.set_output_format(output_format)
        
        # Initialize progress reporter
        progress = ProgressReporter(total_steps=6)
        progress.start()
        
        # Initialize resource manager
        resource_manager = ResourceManager()
        resource_manager.start_monitoring()
        
        # Initialize CSS feature manager
        feature_manager = CSSFeatureManager()
        
        # Initialize CSS optimizer
        css_optimizer = CSSOptimizer()
        
        # Check Python version
        progress.update("Version Check", "Checking Python version...")
        check_python_version()
        
        # Check requirements
        progress.update("Requirements Check", "Checking required packages...")
        check_requirements()
        
        # Get HTML content
        progress.update("Content Fetch", "Fetching content...")
        if is_directory(source):
            return extract_css_from_directory(source, output_file, verify_ssl=verify_ssl,
                                           minify=minify, verbose=verbose, quiet=quiet,
                                           output_format=output_format)
        else:
            html_content = retry_with_backoff(get_html_content, source, verify_ssl=verify_ssl)
        
        # Extract CSS
        progress.update("CSS Extraction", "Extracting CSS...")
        combined_css = extract_css_from_html(html_content, source if is_valid_url(source) else source)
        
        # Process CSS features
        progress.update("Feature Processing", "Processing CSS features...")
        combined_css = feature_manager.process_features(combined_css)
        
        # Optimize CSS
        progress.update("CSS Optimization", "Optimizing CSS...")
        combined_css = css_optimizer.optimize(combined_css, html_content)
        
        # Clean up the CSS
        progress.update("CSS Cleanup", "Cleaning up CSS...")
        cleaned_css = clean_css(combined_css, minify)
        
        # Save to file
        progress.update("File Save", "Saving to file...")
        save_css_to_file(cleaned_css, output_file)
        
        # Finish progress reporting
        progress.finish()
        
        # Print success message
        ui.print_success(f"CSS successfully extracted and saved to {output_file}")
        
        # Return results
        return {
            'status': 'success',
            'output_file': output_file,
            'css_size': len(cleaned_css),
            'features_detected': feature_manager.detect_features(cleaned_css),
            'processing_time': (datetime.now() - progress.start_time).total_seconds()
        }
        
    except Exception as e:
        if 'progress' in locals():
            progress.error(str(e))
        if 'ui' in locals():
            ui.print_error(str(e))
        raise
    finally:
        if 'resource_manager' in locals():
            resource_manager.stop_monitoring()
        cleanup_resources()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract CSS from HTML files or URLs')
    parser.add_argument('source', help='Source HTML file, URL, or directory')
    parser.add_argument('-o', '--output', default='style.css', help='Output CSS file')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL verification')
    parser.add_argument('--minify', action='store_true', help='Minify CSS output')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress all output')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    try:
        result = extract_css(
            args.source,
            output_file=args.output,
            verify_ssl=not args.no_ssl,
            minify=args.minify,
            verbose=args.verbose,
            quiet=args.quiet,
            output_format=args.format
        )
        
        if args.format == 'json':
            print(json.dumps(result, indent=2))
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1) 