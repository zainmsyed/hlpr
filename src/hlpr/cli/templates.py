"""Command templates system for reusable command configurations."""
from __future__ import annotations

import json
from typing import Any

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table

from hlpr.cli.base import app, console, print_error, print_success, raise_smart_error
from hlpr.core.config import get_config_dir

# Create templates subcommand
templates_app = typer.Typer(help="Manage command templates")
app.add_typer(templates_app, name="template")

# Template storage
TEMPLATES_DIR = get_config_dir() / "templates"
TEMPLATES_FILE = TEMPLATES_DIR / "templates.json"


class CommandTemplate:
    """Represents a command template with parameters and metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        command: str,
        parameters: dict[str, Any],
        created_at: str | None = None,
        updated_at: str | None = None,
    ):
        self.name = name
        self.description = description
        self.command = command
        self.parameters = parameters
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> dict[str, Any]:
        """Convert template to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "command": self.command,
            "parameters": self.parameters,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandTemplate:
        """Create template from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            command=data["command"],
            parameters=data["parameters"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def substitute_parameters(self, param_values: dict[str, Any] | None = None) -> str:
        """Substitute parameters in the command template."""
        command = self.command
        if param_values is None:
            param_values = {}

        # Use provided values or defaults from parameter definitions
        final_values = {}
        for param_name, param_config in self.parameters.items():
            if param_name in param_values:
                final_values[param_name] = param_values[param_name]
            elif isinstance(param_config, dict) and "default" in param_config:
                final_values[param_name] = param_config["default"]
            else:
                # Use parameter name as fallback if no default
                final_values[param_name] = param_name

        # Substitute parameters in command
        for param_name, param_value in final_values.items():
            placeholder = f"{{{param_name}}}"
            command = command.replace(placeholder, str(param_value))

        return command


class TemplateManager:
    """Manages command templates storage and retrieval."""

    def __init__(self, templates_dir: Any = None) -> None:
        if templates_dir is not None:
            self.templates_dir = templates_dir / "templates"
        else:
            self.templates_dir = TEMPLATES_DIR
        self.templates_file = self.templates_dir / "templates.json"
        self._ensure_templates_dir()

    def _ensure_templates_dir(self) -> None:
        """Ensure templates directory exists."""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        if not self.templates_file.exists():
            self.templates_file.write_text("{}")

    def load_templates(self) -> dict[str, CommandTemplate]:
        """Load all templates from storage."""
        try:
            data = json.loads(self.templates_file.read_text())
            return {
                name: CommandTemplate.from_dict(template_data)
                for name, template_data in data.items()
            }
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_templates(self, templates: dict[str, CommandTemplate]) -> None:
        """Save templates to storage."""
        data = {name: template.to_dict() for name, template in templates.items()}
        self.templates_file.write_text(json.dumps(data, indent=2))

    def create_template(
        self,
        name: str,
        description: str,
        command: str,
        parameters: dict[str, Any],
    ) -> CommandTemplate:
        """Create a new template."""
        from datetime import datetime

        now = datetime.now().isoformat()
        template = CommandTemplate(
            name=name,
            description=description,
            command=command,
            parameters=parameters,
            created_at=now,
            updated_at=now,
        )

        templates = self.load_templates()
        templates[name] = template
        self.save_templates(templates)

        return template

    def get_template(self, name: str) -> CommandTemplate | None:
        """Get a template by name."""
        templates = self.load_templates()
        return templates.get(name)

    def delete_template(self, name: str) -> bool:
        """Delete a template by name."""
        templates = self.load_templates()
        if name in templates:
            del templates[name]
            self.save_templates(templates)
            return True
        return False

    def list_templates(self) -> list[CommandTemplate]:
        """List all templates."""
        templates = self.load_templates()
        return list(templates.values())


# Global template manager instance
template_manager = TemplateManager()


@templates_app.command("create")
def create_template(
    name: str = typer.Argument(..., help="Name of the template"),
    interactive: bool = typer.Option(
        True, "--interactive/--non-interactive", help="Use interactive mode"
    ),
) -> None:
    """Create a new command template."""
    if interactive:
        return _create_template_interactive(name)
    else:
        return _create_template_non_interactive(name)


def _create_template_interactive(name: str) -> None:
    """Create template with interactive prompts."""
    if not name.strip():
        raise_smart_error("Template name cannot be empty")
        
    console.print(f"[bold]Creating template:[/bold] {name}")

    # Check if template already exists
    if template_manager.get_template(name):
        if not Confirm.ask(f"Template '{name}' already exists. Overwrite?"):
            return

    # Get template details
    description = Prompt.ask("Description", default="")
    command = Prompt.ask("Command template (use {param} for parameters)")

    # Get parameters
    parameters = {}
    console.print("\n[bold]Parameters:[/bold]")
    console.print("Enter parameter names (press Enter when done):")

    while True:
        param_name = Prompt.ask("Parameter name", default="")
        if not param_name:
            break

        param_type = Prompt.ask(
            f"Type for '{param_name}'",
            choices=["str", "int", "float", "bool"],
            default="str"
        )
        param_default = Prompt.ask(f"Default value for '{param_name}'", default="")

        parameters[param_name] = {
            "type": param_type,
            "default": param_default if param_default else None,
        }

    # Create template
    try:
        _template = template_manager.create_template(
            name=name,
            description=description,
            command=command,
            parameters=parameters,
        )
        print_success(f"Template '{name}' created successfully!")
        console.print(f"Use: [bold]hlpr template run {name} [args][/bold]")

    except Exception as e:
        print_error(f"Failed to create template: {e}")


def _create_template_non_interactive(name: str) -> None:
    """Create template with command line arguments."""
    # This would require additional arguments for non-interactive mode
    print_error("Non-interactive mode not implemented yet. Use --interactive flag.")


@templates_app.command("run")
def run_template(
    name: str = typer.Argument(..., help="Name of the template to run"),
    args: list[str] | None = None,
) -> None:
    """Run a command template with given arguments."""
    if not name.strip():
        raise_smart_error("Template name cannot be empty")
        
    template = template_manager.get_template(name)
    if not template:
        raise_smart_error(
            f"Template '{name}' not found",
            suggestions=[
                f"Create it with: hlpr template create {name}",
                "List available templates: hlpr template list"
            ]
        )

    # Type narrowing: template is definitely not None here
    assert template is not None
    
    try:
        # Convert positional args to parameter values
        param_values = {}
        if args:
            param_names = list(template.parameters.keys())
            for i, arg in enumerate(args):
                if i < len(param_names):
                    param_values[param_names[i]] = arg
        
        # Substitute parameters
        command = template.substitute_parameters(param_values)

        # Execute the command
        console.print(f"[bold]Running template:[/bold] {name}")
        console.print(f"[dim]Command:[/dim] {command}")

        # Import and use the executor
        # Parse command into parts
        import shlex

        from hlpr.cli.executor import smart_execute
        command_parts = shlex.split(command)

        if not command_parts:
            raise_smart_error(
                "Empty command generated from template",
                suggestions=[
                    "Check your template command syntax",
                    f"Review template: hlpr template show {name}"
                ]
            )

        smart_execute(command_parts[0], command_parts[1:])

    except Exception as e:
        print_error(f"Failed to run template '{name}': {e}")


@templates_app.command("list")
def list_templates() -> None:
    """List all available templates."""
    templates = template_manager.list_templates()

    if not templates:
        console.print("[dim]No templates found.[/dim]")
        console.print("Create one with: [bold]hlpr template create <name>[/bold]")
        return

    # Create table
    table = Table(title="Command Templates")
    table.add_column("Name", style="bold cyan")
    table.add_column("Description", style="dim")
    table.add_column("Command", style="green")
    table.add_column("Parameters", style="yellow")

    for template in templates:
        param_count = len(template.parameters)
        params_str = f"{param_count} parameter{'s' if param_count != 1 else ''}"

        table.add_row(
            template.name,
            template.description or "[dim]No description[/dim]",
            template.command,
            params_str,
        )

    console.print(table)


@templates_app.command("delete")
def delete_template(
    name: str = typer.Argument(..., help="Name of the template to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
) -> None:
    """Delete a command template."""
    if not name.strip():
        raise_smart_error("Template name cannot be empty")
        
    template = template_manager.get_template(name)
    if not template:
        print_error(f"Template '{name}' not found")
        return

    if not force:
        if not Confirm.ask(f"Delete template '{name}'?"):
            return

    if template_manager.delete_template(name):
        print_success(f"Template '{name}' deleted successfully!")
    else:
        print_error(f"Failed to delete template '{name}'")


@templates_app.command("show")
def show_template(
    name: str = typer.Argument(..., help="Name of the template to show"),
) -> None:
    """Show details of a specific template."""
    if not name.strip():
        raise_smart_error("Template name cannot be empty")
        
    template = template_manager.get_template(name)
    if not template:
        print_error(f"Template '{name}' not found")
        return

    console.print(f"[bold]Template:[/bold] {name}")
    console.print(f"[bold]Description:[/bold] {template.description or '[dim]No description[/dim]'}")
    console.print(f"[bold]Command:[/bold] {template.command}")

    if template.parameters:
        console.print("\n[bold]Parameters:[/bold]")
        for param_name, param_info in template.parameters.items():
            param_type = param_info.get("type", "str")
            param_default = param_info.get("default", "")
            default_str = f" (default: {param_default})" if param_default else ""
            console.print(f"  • {param_name}: {param_type}{default_str}")
    else:
        console.print("\n[dim]No parameters defined[/dim]")

    if template.created_at:
        console.print(f"\n[dim]Created:[/dim] {template.created_at}")
    if template.updated_at:
        console.print(f"[dim]Updated:[/dim] {template.updated_at}")