"""Core CSS extraction functionality."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..managers.resource import ResourceManager
from ..managers.feature import CSSFeatureManager
from ..managers.optimizer import CSSOptimizer
from ..managers.imports import ImportManager
from ..utils.progress import ProgressReporter
from ..utils.ui import UserInterface
from ..utils.retry import retry_with_backoff
from ..utils.html import get_html_content
from ..utils.validation import validate_html_content
from ..utils.path import is_directory, is_valid_url
from .processor import process_css_rules, clean_css

def extract_css(source: str, output_file: str = 'style.css', verify_ssl: bool = True,
               minify: bool = False, verbose: bool = False, quiet: bool = False,
               output_format: str = 'text') -> Dict[str, Any]:
    """Main function to extract CSS from a source."""
    try:
        # Initialize UI
        ui = UserInterface()
        ui.set_verbosity(verbose, quiet)
        ui.set_output_format(output_format)
        
        # Initialize progress reporter
        progress = ProgressReporter(total_steps=6)
        progress.start()
        
        # Initialize managers
        resource_manager = ResourceManager()
        resource_manager.start_monitoring()
        feature_manager = CSSFeatureManager()
        css_optimizer = CSSOptimizer()
        
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

def extract_css_from_html(html_content: str, base_url: str = '') -> str:
    """Extract CSS from HTML content."""
    try:
        if not html_content:
            return ''
            
        # Validate HTML content
        if not validate_html_content(html_content):
            raise ValueError("Invalid HTML content")
            
        # Parse HTML and extract CSS
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
            
            # Process imports
            import_manager = ImportManager()
            try:
                combined_css = import_manager.process_imports(combined_css, base_url, verify_ssl=True)
            finally:
                import_manager.clear()
            
            # Process CSS rules
            combined_css = process_css_rules(combined_css, base_url)
            
            return combined_css
            
        finally:
            soup.decompose()
            
    except Exception as e:
        logging.error(f"Error extracting CSS from HTML: {e}")
        return ''

def extract_css_from_directory(directory_path: str, output_dir: str = None, **kwargs) -> Dict[str, Any]:
    """Extract CSS from all HTML files in a directory."""
    try:
        # Initialize UI and managers
        ui = UserInterface()
        ui.set_verbosity(kwargs.get('verbose', False), kwargs.get('quiet', False))
        ui.set_output_format(kwargs.get('output_format', 'text'))
        
        progress = ProgressReporter(total_steps=4)
        progress.start()
        
        resource_manager = ResourceManager()
        resource_manager.start_monitoring()
        
        feature_manager = CSSFeatureManager()
        css_optimizer = CSSOptimizer()
        
        # Process files
        html_files = scan_directory(directory_path)
        if not html_files:
            raise ValueError("No HTML files found in directory")
        
        # Process files in parallel
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