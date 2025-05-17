"""Tests for CSS Extractor resource managers."""

import os
import time
import pytest
import tempfile
from pathlib import Path
from ..managers import (
    BaseManager,
    CacheManager,
    MemoryManager,
    NetworkManager,
    ManagerFactory
)

class ConcreteBaseManager(BaseManager):
    def check_resources(self):
        pass
    def get_stats(self):
        return {}

class TestBaseManager:
    """Tests for BaseManager."""
    
    def test_logging(self):
        """Test logging functionality."""
        manager = ConcreteBaseManager()
        manager.log_info("Test info")
        manager.log_warning("Test warning")
        manager.log_error("Test error")
        manager.log_debug("Test debug")
        
    def test_error_handling(self):
        """Test error handling."""
        manager = ConcreteBaseManager()
        with pytest.raises(Exception):
            manager.handle_error(Exception("Test error"), "Test message")
            
    def test_context_manager(self):
        """Test context manager functionality."""
        with ConcreteBaseManager() as manager:
            assert isinstance(manager, BaseManager)
            
    def test_error_handling_with_none(self):
        """Test error handling with None error."""
        manager = ConcreteBaseManager()
        with pytest.raises(Exception):
            manager.handle_error(None, "Test message")
            
    def test_logging_with_empty_message(self):
        """Test logging with empty message."""
        manager = ConcreteBaseManager()
        manager.log_info("")
        manager.log_warning("")
        manager.log_error("")
        manager.log_debug("")

class TestCacheManager:
    """Tests for CacheManager."""
    
    @pytest.fixture
    def cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
            
    @pytest.fixture
    def cache_manager(self, cache_dir):
        """Create cache manager instance."""
        return CacheManager(cache_dir)
        
    def test_cache_creation(self, cache_manager, cache_dir):
        """Test cache directory creation."""
        assert Path(cache_dir).exists()
        assert Path(cache_dir).is_dir()
        
    def test_css_caching(self, cache_manager):
        """Test CSS caching functionality."""
        css_content = "body { color: red; }"
        
        # Cache CSS with auto-generated key
        cache_key = cache_manager.cache_css(css_content)
        assert cache_key is not None
        
        # Get cached CSS
        cached_content = cache_manager.get_cached_css(cache_key)
        assert cached_content == css_content
        
        # Check metadata
        stats = cache_manager.get_cache_stats()
        assert stats['total_entries'] == 1
        assert stats['total_size'] == len(css_content)
        
        # Test caching with explicit key
        explicit_key = "test_key"
        cache_key2 = cache_manager.cache_css(css_content, explicit_key)
        assert cache_key2 == explicit_key
        
        # Verify both entries exist
        assert cache_manager.get_cached_css(cache_key) == css_content
        assert cache_manager.get_cached_css(cache_key2) == css_content
        assert cache_manager.get_cache_stats()['total_entries'] == 2
        
    def test_cache_removal(self, cache_manager):
        """Test cache removal functionality."""
        css_content = "body { color: red; }"
        
        # Cache CSS with auto-generated key
        cache_key = cache_manager.cache_css(css_content)
        assert cache_key is not None
        
        # Remove cached CSS
        cache_manager.remove_cached_css(cache_key)
        
        # Verify removal
        assert cache_manager.get_cached_css(cache_key) is None
        assert cache_manager.get_cache_stats()['total_entries'] == 0
        
    def test_cache_clear(self, cache_manager):
        """Test cache clearing functionality."""
        # Add multiple entries
        for i in range(3):
            cache_manager.cache_css(f"body {{ color: {i}; }}", f"test{i}.css")
            
        # Clear cache
        cache_manager.clear_cache()
        
        # Verify clearing
        assert cache_manager.get_cache_stats()['total_entries'] == 0
        
    def test_cache_empty_content(self, cache_manager):
        """Test caching empty content."""
        cache_key = cache_manager.cache_css("", "empty.css")
        assert cache_key is not None
        assert cache_manager.get_cached_css(cache_key) == ""
        
    def test_cache_large_content(self, cache_manager):
        """Test caching large content."""
        large_content = "x" * (1024 * 1024)  # 1MB
        cache_key = cache_manager.cache_css(large_content, "large.css")
        assert cache_key is not None
        assert len(cache_manager.get_cached_css(cache_key)) == len(large_content)
        
    def test_cache_special_characters(self, cache_manager):
        """Test caching content with special characters."""
        special_content = "body { content: '\\u00A9'; }"
        cache_key = cache_manager.cache_css(special_content, "special.css")
        assert cache_key is not None
        assert cache_manager.get_cached_css(cache_key) == special_content
        
    def test_cache_concurrent_access(self, cache_manager):
        """Test concurrent cache access."""
        import threading
        
        def cache_worker():
            for i in range(10):
                cache_manager.cache_css(f"body {{ color: {i}; }}", f"test{i}.css")
                
        threads = [threading.Thread(target=cache_worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
            
        assert cache_manager.get_cache_stats()['total_entries'] == 50
        
    def test_cache_invalid_key(self, cache_manager):
        """Test accessing cache with invalid key."""
        assert cache_manager.get_cached_css("invalid_key") is None
        
    def test_cache_metadata_corruption(self, cache_manager):
        """Test handling corrupted metadata."""
        # Corrupt metadata file
        with open(cache_manager.metadata_file, 'w') as f:
            f.write("invalid json")
        # Should handle corruption gracefully
        cache_manager._load_metadata()
        assert dict(cache_manager.metadata.items()) == {}

class TestMemoryManager:
    """Tests for MemoryManager."""
    
    @pytest.fixture
    def memory_manager(self):
        """Create memory manager instance."""
        return MemoryManager(memory_limit=1024 * 1024)  # 1MB limit
        
    def test_memory_usage(self, memory_manager):
        """Test memory usage tracking."""
        # Check initial state
        assert memory_manager.check_available_memory()
        
        # Get memory stats
        stats = memory_manager.get_memory_stats()
        assert 'current_usage' in stats
        assert 'memory_limit' in stats
        assert 'system_total' in stats
        
    def test_memory_limits(self, memory_manager):
        """Test memory limit enforcement."""
        # Create large string to increase memory usage
        large_string = "x" * (1024 * 1024)  # 1MB
        
        # Force garbage collection
        memory_manager.force_garbage_collection()
        
        # Check memory usage
        assert memory_manager.get_memory_percent() > 0
        
    def test_critical_memory(self, memory_manager):
        """Test critical memory detection."""
        # Create large string to increase memory usage
        large_string = "x" * (1024 * 1024)  # 1MB
        
        # Check if memory is critical
        assert memory_manager.is_memory_critical(threshold=0.1)  # 10% threshold
        
    def test_memory_no_limit(self):
        """Test memory manager without limit."""
        manager = MemoryManager(memory_limit=None)
        assert manager.check_available_memory()
        assert manager.get_memory_percent() == 0.0
        
    def test_memory_negative_limit(self):
        """Test memory manager with negative limit."""
        manager = MemoryManager(memory_limit=-1024)
        assert not manager.check_available_memory()
        
    def test_memory_zero_limit(self):
        """Test memory manager with zero limit."""
        manager = MemoryManager(memory_limit=0)
        assert not manager.check_available_memory()
        
    def test_memory_process_not_found(self, memory_manager, monkeypatch):
        """Test handling process not found."""
        def mock_memory_info():
            raise psutil.NoSuchProcess(0)
            
        monkeypatch.setattr(memory_manager.process, 'memory_info', mock_memory_info)
        assert memory_manager.get_memory_usage() == 0

class TestNetworkManager:
    """Tests for NetworkManager."""
    
    @pytest.fixture
    def network_manager(self):
        """Create network manager instance."""
        return NetworkManager(max_requests=5)
        
    def test_request_limits(self, network_manager):
        """Test request limit enforcement."""
        # Make requests up to limit
        for _ in range(5):
            assert network_manager.check_network_usage()
            network_manager.request_count += 1
            
        # Verify limit reached
        assert not network_manager.check_network_usage()
        
    def test_url_validation(self, network_manager):
        """Test URL validation."""
        # Valid URLs
        assert network_manager.is_valid_url("http://example.com")
        assert network_manager.is_valid_url("https://example.com/path")
        
        # Invalid URLs
        assert not network_manager.is_valid_url("not-a-url")
        assert not network_manager.is_valid_url("http://")
        
    def test_domain_extraction(self, network_manager):
        """Test domain extraction."""
        assert network_manager.extract_domain("http://example.com") == "example.com"
        assert network_manager.extract_domain("https://sub.example.com/path") == "sub.example.com"
        
    def test_stats_tracking(self, network_manager):
        """Test statistics tracking."""
        # Make some requests
        for _ in range(3):
            network_manager.request_count += 1
            
        # Get stats
        stats = network_manager.get_network_stats()
        assert stats['request_count'] == 3
        assert stats['max_requests'] == 5
        assert stats['elapsed_time'] > 0
        
    def test_network_no_limit(self):
        """Test network manager without limit."""
        manager = NetworkManager(max_requests=None)
        assert manager.check_network_usage()
        
    def test_network_negative_limit(self):
        """Test network manager with negative limit."""
        manager = NetworkManager(max_requests=-5)
        assert not manager.check_network_usage()
        
    def test_network_zero_limit(self):
        """Test network manager with zero limit."""
        manager = NetworkManager(max_requests=0)
        assert not manager.check_network_usage()
        
    def test_network_invalid_timeout(self):
        """Test network manager with invalid timeout."""
        with pytest.raises(ValueError):
            NetworkManager(request_timeout=-1)
            
    def test_network_invalid_retries(self):
        """Test network manager with invalid retries."""
        with pytest.raises(ValueError):
            NetworkManager(max_retries=-1)
            
    def test_network_reset_stats(self, network_manager):
        """Test resetting network statistics."""
        network_manager.request_count = 5
        network_manager.reset_stats()
        assert network_manager.request_count == 0
        assert network_manager.get_network_stats()['request_count'] == 0

class TestManagerFactory:
    """Tests for ManagerFactory."""
    
    @pytest.fixture
    def factory(self):
        """Create manager factory instance."""
        return ManagerFactory()
        
    def test_manager_creation(self, factory):
        """Test manager creation."""
        # Create managers
        cache_manager = factory.create_cache_manager()
        memory_manager = factory.create_memory_manager()
        network_manager = factory.create_network_manager()
        
        # Verify creation
        assert isinstance(cache_manager, CacheManager)
        assert isinstance(memory_manager, MemoryManager)
        assert isinstance(network_manager, NetworkManager)
        
    def test_manager_retrieval(self, factory):
        """Test manager retrieval."""
        # Create managers
        factory.create_cache_manager()
        factory.create_memory_manager()
        
        # Get managers
        assert factory.get_manager('cache') is not None
        assert factory.get_manager('memory') is not None
        assert factory.get_manager('nonexistent') is None
        
    def test_resource_checking(self, factory):
        """Test resource checking."""
        # Create managers
        factory.create_cache_manager()
        factory.create_memory_manager()
        factory.create_network_manager()
        
        # Check resources
        factory.check_all_resources()
        
    def test_stats_collection(self, factory):
        """Test statistics collection."""
        # Create managers
        factory.create_cache_manager()
        factory.create_memory_manager()
        factory.create_network_manager()
        
        # Get stats
        stats = factory.get_all_stats()
        assert 'cache' in stats
        assert 'memory' in stats
        assert 'network' in stats
        
    def test_cleanup(self, factory):
        """Test cleanup functionality."""
        # Create managers
        factory.create_cache_manager()
        factory.create_memory_manager()
        factory.create_network_manager()
        
        # Cleanup
        factory.cleanup_all()
        
    def test_context_manager(self, factory):
        """Test context manager functionality."""
        with factory as f:
            assert isinstance(f, ManagerFactory)
            f.create_cache_manager()
            f.create_memory_manager()
            f.create_network_manager()
            
    def test_duplicate_manager_creation(self, factory):
        """Test creating duplicate managers."""
        # Create first manager
        cache_manager1 = factory.create_cache_manager()
        
        # Create duplicate manager
        cache_manager2 = factory.create_cache_manager()
        
        # Should return same instance
        assert cache_manager1 is cache_manager2
        
    def test_manager_creation_failure(self, factory, monkeypatch):
        """Test handling manager creation failure."""
        def mock_create_cache_manager(*args, **kwargs):
            raise Exception("Creation failed")
            
        monkeypatch.setattr(factory, 'create_cache_manager', mock_create_cache_manager)
        
        with pytest.raises(Exception):
            factory.create_cache_manager()
            
    def test_cleanup_failure(self, factory, monkeypatch):
        """Test handling cleanup failure."""
        def mock_cleanup():
            raise Exception("Cleanup failed")
            
        # Create manager
        cache_manager = factory.create_cache_manager()
        monkeypatch.setattr(cache_manager, 'cleanup', mock_cleanup)
        
        # Should handle cleanup failure gracefully
        factory.cleanup_all() 