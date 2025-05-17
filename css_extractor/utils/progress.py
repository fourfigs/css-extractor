"""Progress reporting functionality."""

import sys
import time
from datetime import datetime
from typing import Optional
import logging

class ProgressReporter:
    """Handles progress reporting for long-running operations."""
    
    def __init__(self, total_steps: int, width: int = 50):
        """Initialize the progress reporter.
        
        Args:
            total_steps: Total number of steps in the process
            width: Width of the progress bar in characters
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.width = width
        self.start_time = datetime.now()
        self.last_update = time.time()
        self._lock = threading.Lock()
        
    def start(self):
        """Start the progress reporting."""
        self.start_time = datetime.now()
        self.current_step = 0
        self._print_progress()
        
    def update(self, step_name: str, message: str = ""):
        """Update the progress.
        
        Args:
            step_name: Name of the current step
            message: Optional message to display
        """
        with self._lock:
            self.current_step += 1
            self._print_progress(step_name, message)
            
    def finish(self):
        """Finish the progress reporting."""
        with self._lock:
            self.current_step = self.total_steps
            self._print_progress("Complete", "Finished")
            print()  # Add newline after progress bar
            
    def error(self, error_message: str):
        """Report an error.
        
        Args:
            error_message: The error message to display
        """
        with self._lock:
            print(f"\nError: {error_message}")
            logging.error(error_message)
            
    def _print_progress(self, step_name: Optional[str] = None, message: str = ""):
        """Print the progress bar.
        
        Args:
            step_name: Optional name of the current step
            message: Optional message to display
        """
        try:
            # Calculate progress
            progress = self.current_step / self.total_steps
            filled = int(self.width * progress)
            bar = '█' * filled + '░' * (self.width - filled)
            
            # Calculate elapsed time
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
            
            # Calculate estimated time remaining
            if self.current_step > 0:
                time_per_step = elapsed.total_seconds() / self.current_step
                remaining_steps = self.total_steps - self.current_step
                remaining_time = time_per_step * remaining_steps
                remaining_str = str(datetime.timedelta(seconds=int(remaining_time)))
            else:
                remaining_str = "calculating..."
            
            # Print progress bar
            sys.stdout.write('\r')
            if step_name:
                sys.stdout.write(f"{step_name}: ")
            sys.stdout.write(f"[{bar}] {progress:.1%}")
            sys.stdout.write(f" ({self.current_step}/{self.total_steps})")
            sys.stdout.write(f" {elapsed_str} elapsed, {remaining_str} remaining")
            if message:
                sys.stdout.write(f" - {message}")
            sys.stdout.flush()
            
        except Exception as e:
            logging.error(f"Error printing progress: {e}")
            
    def _get_progress_color(self, progress: float) -> str:
        """Get color based on progress.
        
        Args:
            progress: Progress value between 0 and 1
            
        Returns:
            ANSI color code
        """
        if progress < 0.3:
            return '\033[91m'  # Red
        elif progress < 0.7:
            return '\033[93m'  # Yellow
        else:
            return '\033[92m'  # Green 