"""Tests for the discover-kasa tool."""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path
import importlib.util
import inspect


class TestDiscoverKasa(unittest.TestCase):
    """Test Kasa discovery tool."""

    def setUp(self):
        """Load the discover-kasa module for each test."""
        tools_dir = Path(__file__).parent.parent / "tools"
        spec = importlib.util.spec_from_file_location(
            "discover_kasa_module",
            tools_dir / "discover-kasa.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_module_has_main_function(self):
        """Test that the module has a main function."""
        self.assertTrue(hasattr(self.module, 'main'))

    def test_main_is_async(self):
        """Test that main function is async (coroutine)."""
        self.assertTrue(inspect.iscoroutinefunction(self.module.main))

    def test_no_bulbs_found(self):
        """Test that tool handles no bulbs found gracefully."""
        # Mock empty device list
        async def mock_discover():
            return {}

        with patch.object(self.module.Discover, 'discover', mock_discover):
            # Run main (should not raise)
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.module.main())
            # Should return without error
            self.assertIsNone(result)

    def test_with_bulbs_found(self):
        """Test that tool processes found bulbs."""
        # Create mock bulb device
        mock_bulb = AsyncMock()
        mock_bulb.is_bulb = True
        mock_bulb.alias = "Test Bulb"
        mock_bulb.host = "192.168.1.100"
        mock_bulb.model = "KL110"
        mock_bulb.mac = "00:11:22:33:44:55"
        mock_bulb.update = AsyncMock()

        # Create async mock for discover
        async def mock_discover():
            return {"192.168.1.100": mock_bulb}

        with patch.object(self.module.Discover, 'discover', mock_discover):
            # Run main
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.module.main())

            # Verify update was called on bulb
            self.assertIsNone(result)
            mock_bulb.update.assert_called_once()

    def test_filters_non_bulbs(self):
        """Test that tool filters out non-bulb devices."""
        # Create mock non-bulb device
        mock_non_bulb = AsyncMock()
        mock_non_bulb.is_bulb = False

        # Create async mock for discover
        async def mock_discover():
            return {"192.168.1.101": mock_non_bulb}

        with patch.object(self.module.Discover, 'discover', mock_discover):
            # Run main
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.module.main())

            # Should handle gracefully (no bulbs to update)
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
