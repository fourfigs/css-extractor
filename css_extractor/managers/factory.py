"""Manager factory for CSS Extractor."""

import logging
from typing import Dict, Any, Optional
from .base import BaseManager
from .cache import CacheManager
from .memory import MemoryManager
from .network import NetworkManager

class ManagerFactory:
    """Factory for creating and managing resource managers."""
    
    def __init__(self):
        """Initialize manager factory."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._managers = {}
        
    def create_cache_manager(self) -> CacheManager:
        """Create cache manager.
        
        Returns:
            CacheManager: Cache manager instance
        """
        if 'cache' not in self._managers:
            self._managers['cache'] = CacheManager(cache_dir=".css_cache")
        return self._managers['cache']
            
    def create_memory_manager(self) -> MemoryManager:
        """Create memory manager.
        
        Returns:
            MemoryManager: Memory manager instance
        """
        if 'memory' not in self._managers:
            self._managers['memory'] = MemoryManager()
        return self._managers['memory']
            
    def create_network_manager(self) -> NetworkManager:
        """Create network manager.
        
        Returns:
            NetworkManager: Network manager instance
        """
        if 'network' not in self._managers:
            self._managers['network'] = NetworkManager()
        return self._managers['network']
            
    def get_manager(self, name: str) -> Optional[Any]:
        """Get manager by name.
        
        Args:
            name: Manager name
            
        Returns:
            Optional[Any]: Manager instance if found
        """
        return self._managers.get(name)
        
    def get_all_managers(self) -> Dict[str, BaseManager]:
        """Get all managers.
        
        Returns:
            Dict[str, BaseManager]: Dictionary of all managers
        """
        return self._managers.copy()
        
    def check_all_resources(self) -> None:
        """Check resources for all managers."""
        for name, manager in self._managers.items():
            try:
                manager.check_resources()
            except Exception as e:
                self.logger.error(f"Failed to check resources for {name} manager: {e}")
                
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all managers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of statistics for each manager
        """
        return {name: manager.get_stats() for name, manager in self._managers.items()}
        
    def cleanup_all(self) -> None:
        """Clean up all managers."""
        for name, manager in self._managers.items():
            try:
                manager.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to cleanup {name} manager: {e}")
                
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup_all()

# Exported class
__all__ = ['ManagerFactory'] 
__all__ = ['ManagerFactory'] 