import pytest
from itzli.core.plugin_loader import PluginManager
from tests.dummy_plugins.fake_samsung import FakeSamsungPlugin

def test_plugin_discovery():
    manager = PluginManager(plugin_package="tests.dummy_plugins")
    manager.discover_plugins()
    
    plugins = manager.get_all_plugins()
    assert len(plugins) >= 1
    # Check that at least one of the loaded plugins is our FakeSamsungPlugin
    assert any(isinstance(p, FakeSamsungPlugin) for p in plugins)

def test_get_plugin_by_vid_pid():
    manager = PluginManager(plugin_package="tests.dummy_plugins")
    manager.discover_plugins()
    
    plugin = manager.get_plugin_for_device("04e8", "685d")
    assert plugin is not None
    assert plugin.name == "Fake Samsung Plugin"

def test_get_plugin_by_vid_pid_not_found():
    manager = PluginManager(plugin_package="tests.dummy_plugins")
    manager.discover_plugins()
    
    plugin = manager.get_plugin_for_device("1234", "5678")
    assert plugin is None
