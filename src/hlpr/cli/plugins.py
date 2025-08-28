"""Plugin system for hlpr CLI extensions."""
from __future__ import annotations

import importlib
import importlib.util
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import typer

from hlpr.cli.base import app, console, print_error, print_success
from hlpr.core.config import get_config_dir

# Maximum plugin file size (1MB)
MAX_PLUGIN_SIZE = 1024 * 1024


class PluginFunction(Protocol):
    """Protocol for plugin functions with command metadata."""
    _hlpr_command_name: str
    _hlpr_command_help: str


class PluginManager:
    """Manages loading and execution of hlpr plugins."""

    def __init__(self) -> None:
        self.plugins_dir = get_config_dir() / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_plugins: dict[str, Any] = {}
        self.plugin_commands: dict[str, Callable[..., Any]] = {}

    def discover_plugins(self) -> list[Path]:
        """Discover all plugin files in the plugins directory."""
        plugin_files = []
        if self.plugins_dir.exists():
            for file_path in self.plugins_dir.glob("*.py"):
                if file_path.is_file():
                    plugin_files.append(file_path)
        return plugin_files

    def load_plugin(self, plugin_path: Path) -> Any | None:
        """Load a plugin module from file path."""
        try:
            # Security checks
            if plugin_path.stat().st_size > MAX_PLUGIN_SIZE:
                console.print(f"[red]Plugin {plugin_path.name} is too large (max {MAX_PLUGIN_SIZE} bytes)[/red]")
                return None
                
            if not plugin_path.suffix == '.py':
                console.print(f"[red]Plugin {plugin_path.name} is not a Python file[/red]")
                return None
            
            spec = importlib.util.spec_from_file_location(
                f"hlpr_plugin_{plugin_path.stem}", plugin_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            console.print(f"[red]Failed to load plugin {plugin_path.name}: {e}[/red]")
        return None

    def load_all_plugins(self) -> None:
        """Load all available plugins."""
        plugin_files = self.discover_plugins()

        if not plugin_files:
            return

        console.print(f"[blue]Loading {len(plugin_files)} plugin(s)...[/blue]")

        for plugin_path in plugin_files:
            plugin_module = self.load_plugin(plugin_path)
            if plugin_module:
                self.loaded_plugins[plugin_path.stem] = plugin_module
                console.print(f"  ✅ Loaded plugin: {plugin_path.name}")

                # Register commands from this plugin
                self._register_plugin_commands(plugin_module, plugin_path.stem)

    def _register_plugin_commands(self, plugin_module: Any, plugin_name: str) -> None:
        """Register commands defined in a plugin module."""
        for _name, obj in inspect.getmembers(plugin_module):
            if (inspect.isfunction(obj) and
                hasattr(obj, '_hlpr_command_name') and
                hasattr(obj, '_hlpr_command_help')):

                # Cast to our protocol type
                plugin_func = obj
                command_name: str = plugin_func._hlpr_command_name
                command_help: str = plugin_func._hlpr_command_help
                
                # Check for command name conflicts
                if command_name in self.plugin_commands:
                    console.print(f"[yellow]Warning: Command '{command_name}' already exists, skipping[/yellow]")
                    continue

                # Register with typer
                app.command(name=command_name, help=command_help)(obj)

                # Store reference
                self.plugin_commands[command_name] = obj

                console.print(f"    📌 Registered command: {command_name}")

    def get_plugin_info(self) -> dict[str, Any]:
        """Get information about loaded plugins and their commands."""
        info = {
            "plugins_dir": str(self.plugins_dir),
            "loaded_plugins": {},
            "plugin_commands": []
        }

        for plugin_name, _plugin_module in self.loaded_plugins.items():
            plugin_info: dict[str, Any] = {
                "name": plugin_name,
                "commands": []
            }

            # Find commands in this plugin
            for command_name, command_func in self.plugin_commands.items():
                if (hasattr(command_func, '__module__') and
                    command_func.__module__ == f"hlpr_plugin_{plugin_name}"):
                    command_list = plugin_info["commands"]
                    command_list.append({
                        "name": command_name,
                        "help": getattr(command_func, '_hlpr_command_help', ''),
                        "function": command_func.__name__
                    })

            loaded_plugins: dict[str, Any] = info["loaded_plugins"]  # type: ignore[assignment]
            loaded_plugins[plugin_name] = plugin_info

        command_names: list[str] = list(self.plugin_commands.keys())
        info_commands: list[str] = info["plugin_commands"]  # type: ignore[assignment]
        info_commands.extend(command_names)

        return info


# Global plugin manager instance
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def hlpr_command(name: str, help: str = "") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to register a function as an hlpr command.

    Usage:
        @hlpr_command("my-command", help="My custom command")
        def my_command_function(param: str):
            \"\"\"Command implementation\"\"\"
            print(f"Running my command with {param}")
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store metadata on the function
        func._hlpr_command_name = name  # type: ignore[attr-defined]
        func._hlpr_command_help = help or func.__doc__ or ""  # type: ignore[attr-defined]

        return func

    return decorator


# Initialize plugins when module is imported
def init_plugins() -> None:
    """Initialize the plugin system."""
    try:
        manager = get_plugin_manager()
        manager.load_all_plugins()
    except Exception as e:
        console.print(f"[red]Plugin initialization failed: {e}[/red]")


# Auto-initialize plugins
init_plugins()


# CLI Commands for plugin management
@app.command("plugins")  # type: ignore[misc]
def manage_plugins(
    action: str = typer.Argument("list", help="Action: list, reload, info"),
) -> None:
    """Manage hlpr plugins."""
    manager = get_plugin_manager()

    if action == "list":
        plugins = manager.discover_plugins()
        loaded = manager.loaded_plugins

        if not plugins:
            console.print("[dim]No plugins found.[/dim]")
            console.print("Create plugins in: [bold]~/.hlpr/plugins/[/bold]")
            console.print("Example: [green]~/.hlpr/plugins/my_commands.py[/green]")
            return

        from rich.table import Table
        table = Table(title="hlpr Plugins")
        table.add_column("Plugin", style="bold cyan")
        table.add_column("Status", style="green")
        table.add_column("Commands", style="yellow")

        for plugin_path in plugins:
            plugin_name = plugin_path.stem
            status = "✅ Loaded" if plugin_name in loaded else "❌ Failed"
            commands = []

            if plugin_name in loaded:
                plugin_info = manager.get_plugin_info()["loaded_plugins"].get(plugin_name, {})
                commands = [cmd["name"] for cmd in plugin_info.get("commands", [])]

            table.add_row(
                plugin_path.name,
                status,
                ", ".join(commands) if commands else "[dim]None[/dim]"
            )

        console.print(table)

    elif action == "reload":
        console.print("[blue]Reloading plugins...[/blue]")
        manager.loaded_plugins.clear()
        manager.plugin_commands.clear()
        manager.load_all_plugins()
        print_success("Plugins reloaded successfully!")

    elif action == "info":
        info = manager.get_plugin_info()

        console.print("[bold]Plugin System Information[/bold]")
        console.print(f"Plugins directory: {info['plugins_dir']}")
        console.print(f"Loaded plugins: {len(info['loaded_plugins'])}")
        console.print(f"Plugin commands: {len(info['plugin_commands'])}")

        if info['loaded_plugins']:
            console.print("\n[bold]Loaded Plugins:[/bold]")
            for plugin_name, plugin_data in info['loaded_plugins'].items():
                console.print(f"  • {plugin_name}")
                for cmd in plugin_data.get('commands', []):
                    console.print(f"    - {cmd['name']}: {cmd['help']}")

    else:
        print_error(f"Unknown action: {action}")
        console.print("Available actions: [bold]list[/bold], [bold]reload[/bold], [bold]info[/bold]")


# Example plugin content for documentation
PLUGIN_EXAMPLE = '''
# Example plugin: ~/.hlpr/plugins/demo_commands.py

from hlpr.cli.plugins import hlpr_command
from hlpr.cli.base import console, print_success

@hlpr_command("quick-demo", help="Run a quick demo workflow")
def quick_demo_workflow(
    meeting_id: int = typer.Option(..., "--meeting-id", "-m", help="Meeting ID to process"),
    model: str = typer.Option("ollama/gemma3", "--model", help="Model to use")
):
    """Demo workflow: create, train, and summarize a meeting."""
    console.print(f"🚀 Starting demo workflow for meeting {meeting_id}")

    try:
        # Your custom logic here
        print_success(f"Demo completed for meeting {meeting_id} using {model}")

    except Exception as e:
        console.print(f"[red]Demo failed: {e}[/red]")

@hlpr_command("hello", help="Say hello with custom greeting")
def hello_command(
    name: str = typer.Option("World", "--name", "-n", help="Name to greet"),
    style: str = typer.Option("normal", "--style", help="Greeting style")
):
    """A simple hello command with different styles."""
    if style == "excited":
        greeting = f"HELLO {name.upper()}!!! 🎉"
    elif style == "formal":
        greeting = f"Good day, {name}. How do you do?"
    else:
        greeting = f"Hello, {name}!"

    console.print(f"[green]{greeting}[/green]")
'''


@app.command("create-plugin")  # type: ignore[misc]
def create_plugin_example(
    name: str = typer.Argument(..., help="Name for the example plugin file"),
) -> None:
    """Create an example plugin file to get started."""
    if not name.strip():
        from hlpr.cli.base import raise_smart_error
        raise_smart_error("Plugin name cannot be empty")
        
    output = get_plugin_manager().plugins_dir
    output.mkdir(parents=True, exist_ok=True)
    plugin_file = output / f"{name}.py"

    if plugin_file.exists():
        from hlpr.cli.base import raise_smart_error
        raise_smart_error(
            f"Plugin file already exists: {plugin_file}",
            suggestions=["Choose a different name", "Use a different output directory"]
        )

    # Write example plugin
    plugin_file.write_text(PLUGIN_EXAMPLE)

    print_success(f"Example plugin created: {plugin_file}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Edit the plugin file with your custom commands")
    console.print("  2. Reload plugins: [green]hlpr plugins reload[/green]")
    console.print("  3. List commands: [green]hlpr plugins list[/green]")
    console.print("  4. Try your command: [green]hlpr hello --name YourName[/green]")