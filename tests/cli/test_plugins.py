"""Unit tests for the plugin system."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from hlpr.cli.plugins import PluginManager, get_plugin_manager, hlpr_command


class TestPluginManager:
    """Tests for PluginManager class."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.temp_dir) / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_create_manager(self, mock_config_dir):
        """Test creating plugin manager."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        assert manager.plugins_dir == Path(self.temp_dir) / "plugins"
        assert manager.plugins_dir.exists()
        assert len(manager.loaded_plugins) == 0
        assert len(manager.plugin_commands) == 0

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_discover_plugins(self, mock_config_dir):
        """Test discovering plugin files."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # No plugins initially
        plugins = manager.discover_plugins()
        assert len(plugins) == 0
        
        # Create plugin files
        (self.plugins_dir / "plugin1.py").write_text("# Plugin 1")
        (self.plugins_dir / "plugin2.py").write_text("# Plugin 2")
        (self.plugins_dir / "not_a_plugin.txt").write_text("# Not a plugin")
        
        plugins = manager.discover_plugins()
        assert len(plugins) == 2
        plugin_names = [p.name for p in plugins]
        assert "plugin1.py" in plugin_names
        assert "plugin2.py" in plugin_names
        assert "not_a_plugin.txt" not in plugin_names

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_load_plugin_success(self, mock_config_dir):
        """Test successfully loading a plugin."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # Create a valid plugin file
        plugin_content = '''
def test_function():
    """A test function."""
    return "test"

test_variable = "test_value"
'''
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text(plugin_content)
        
        # Load the plugin
        module = manager.load_plugin(plugin_file)
        
        assert module is not None
        assert hasattr(module, 'test_function')
        assert hasattr(module, 'test_variable')
        assert module.test_function() == "test"
        assert module.test_variable == "test_value"

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_load_plugin_syntax_error(self, mock_config_dir):
        """Test loading a plugin with syntax errors."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # Create an invalid plugin file
        plugin_content = '''
def test_function(
    # Missing closing parenthesis
    return "test"
'''
        plugin_file = self.plugins_dir / "invalid_plugin.py"
        plugin_file.write_text(plugin_content)
        
        # Should return None on syntax error
        module = manager.load_plugin(plugin_file)
        assert module is None

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_load_plugin_security_checks(self, mock_config_dir):
        """Test security checks when loading plugins."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # Test file size limit
        large_content = "# " + "x" * (1024 * 1024 + 1)  # Larger than MAX_PLUGIN_SIZE
        large_plugin = self.plugins_dir / "large_plugin.py"
        large_plugin.write_text(large_content)
        
        module = manager.load_plugin(large_plugin)
        assert module is None
        
        # Test non-Python file
        non_python_file = self.plugins_dir / "not_python.txt"
        non_python_file.write_text("# This is not a Python file")
        
        module = manager.load_plugin(non_python_file)
        assert module is None

    @patch('hlpr.cli.plugins.get_config_dir')
    @patch('hlpr.cli.plugins.app')
    def test_register_plugin_commands(self, mock_app, mock_config_dir):
        """Test registering commands from plugins."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # Create a mock plugin module with commands
        mock_module = Mock()
        
        def test_command():
            return "test"
        
        # Add hlpr command attributes
        test_command._hlpr_command_name = "test-cmd"
        test_command._hlpr_command_help = "A test command"
        
        # Mock inspect.getmembers to return our test function
        with patch('hlpr.cli.plugins.inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [("test_command", test_command)]
            
            manager._register_plugin_commands(mock_module, "test_plugin")
            
            # Verify command was registered
            assert "test-cmd" in manager.plugin_commands
            assert manager.plugin_commands["test-cmd"] == test_command
            
            # Verify typer app.command was called
            mock_app.command.assert_called_once_with(
                name="test-cmd", 
                help="A test command"
            )

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_register_plugin_commands_conflict(self, mock_config_dir):
        """Test handling command name conflicts."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # Add an existing command
        existing_command = Mock()
        existing_command._hlpr_command_name = "existing-cmd"
        manager.plugin_commands["existing-cmd"] = existing_command
        
        # Create a conflicting command
        def conflicting_command():
            return "conflict"
        
        conflicting_command._hlpr_command_name = "existing-cmd"
        conflicting_command._hlpr_command_help = "A conflicting command"
        
        mock_module = Mock()
        
        with patch('hlpr.cli.plugins.inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [("conflicting_command", conflicting_command)]
            
            # Should not register the conflicting command
            manager._register_plugin_commands(mock_module, "test_plugin")
            
            # Original command should remain
            assert manager.plugin_commands["existing-cmd"] == existing_command

    @patch('hlpr.cli.plugins.get_config_dir')
    def test_get_plugin_info(self, mock_config_dir):
        """Test getting plugin information."""
        mock_config_dir.return_value = Path(self.temp_dir)
        
        manager = PluginManager()
        
        # Add mock loaded plugin
        mock_module = Mock()
        mock_module.__name__ = "hlpr_plugin_test"
        manager.loaded_plugins["test"] = mock_module
        
        # Add mock command
        mock_command = Mock()
        mock_command.__module__ = "hlpr_plugin_test"
        mock_command.__name__ = "test_function"
        mock_command._hlpr_command_help = "Test help"
        manager.plugin_commands["test-cmd"] = mock_command
        
        info = manager.get_plugin_info()
        
        assert info["plugins_dir"] == str(manager.plugins_dir)
        assert "test" in info["loaded_plugins"]
        assert len(info["loaded_plugins"]["test"]["commands"]) == 1
        assert info["loaded_plugins"]["test"]["commands"][0]["name"] == "test-cmd"
        assert "test-cmd" in info["plugin_commands"]


class TestHlprCommand:
    """Tests for hlpr_command decorator."""

    def test_hlpr_command_decorator(self):
        """Test the hlpr_command decorator."""
        @hlpr_command("test-command", help="Test command help")
        def test_function():
            """Test function docstring."""
            return "test"
        
        assert hasattr(test_function, '_hlpr_command_name')
        assert hasattr(test_function, '_hlpr_command_help')
        assert test_function._hlpr_command_name == "test-command"
        assert test_function._hlpr_command_help == "Test command help"

    def test_hlpr_command_decorator_no_help(self):
        """Test hlpr_command decorator without help text."""
        @hlpr_command("test-command")
        def test_function():
            """Test function docstring."""
            return "test"
        
        assert test_function._hlpr_command_name == "test-command"
        assert test_function._hlpr_command_help == "Test function docstring."

    def test_hlpr_command_decorator_no_docstring(self):
        """Test hlpr_command decorator without docstring."""
        @hlpr_command("test-command")
        def test_function():
            return "test"
        
        assert test_function._hlpr_command_name == "test-command"
        assert test_function._hlpr_command_help == ""


class TestPluginManagerSingleton:
    """Tests for plugin manager singleton."""

    def test_get_plugin_manager_singleton(self):
        """Test that get_plugin_manager returns a singleton."""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        
        assert manager1 is manager2

    @patch('hlpr.cli.plugins._plugin_manager', None)
    def test_get_plugin_manager_creates_new(self):
        """Test that get_plugin_manager creates new instance when None."""
        # Reset the global variable
        import hlpr.cli.plugins
        hlpr.cli.plugins._plugin_manager = None
        
        manager = get_plugin_manager()
        assert manager is not None
        assert isinstance(manager, PluginManager)


class TestPluginIntegration:
    """Integration tests for plugin system."""
    
    def test_plugin_example_content(self):
        """Test that the example plugin content is valid Python."""
        from hlpr.cli.plugins import PLUGIN_EXAMPLE
        
        # Should be able to compile the example
        try:
            compile(PLUGIN_EXAMPLE, "example_plugin.py", "exec")
        except SyntaxError:
            pytest.fail("Plugin example contains syntax errors")

    def test_plugin_loading_workflow(self):
        """Test complete plugin loading workflow."""
        # This would test the CLI commands end-to-end
        # For now, we'll mark it as a placeholder
        pass


# Fixtures and test data
@pytest.fixture
def sample_plugin_content():
    """Sample plugin content for testing."""
    return '''
import typer
from hlpr.cli.plugins import hlpr_command
from hlpr.cli.base import console, print_success

@hlpr_command("sample-cmd", help="A sample command")
def sample_command(
    name: str = typer.Option("World", "--name", "-n", help="Name to greet")
):
    """Sample command implementation."""
    console.print(f"Hello, {name}!")
    print_success("Sample command executed successfully")

@hlpr_command("another-cmd", help="Another sample command")  
def another_command():
    """Another sample command."""
    console.print("Another command executed")
'''

@pytest.fixture
def invalid_plugin_content():
    """Invalid plugin content for testing."""
    return '''
# This plugin has syntax errors
def broken_function(
    # Missing closing parenthesis
    return "broken"

@hlpr_command("broken-cmd")
def another_broken_function():
    undefined_variable.do_something()  # This will fail at runtime
'''