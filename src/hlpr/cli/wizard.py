"""Interactive command builder and wizards."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hlpr.cli.base import console, print_error, print_info


class CommandWizard:
    """Interactive wizard for building commands."""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}

    def _validate_positive_int(self, value: str) -> str:
        """Validate that a string represents a positive integer."""
        try:
            int_val = int(value)
            if int_val <= 0:
                raise ValueError("Must be a positive integer")
            return value
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("Must be a valid integer") from e
            raise

    def _validate_non_negative_int(self, value: str) -> str:
        """Validate that a string represents a non-negative integer."""
        try:
            int_val = int(value)
            if int_val < 0:
                raise ValueError("Must be a non-negative integer")
            return value
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("Must be a valid integer") from e
            raise

    def _validate_non_empty(self, value: str) -> str:
        """Validate that a string is not empty."""
        if not value.strip():
            raise ValueError("Value cannot be empty")
        return value

    def prompt_choice(self, message: str, choices: list[str], default: str | None = None) -> str:
        """Prompt user to choose from a list of options."""
        console.print(f"\n[bold blue]{message}[/bold blue]")

        for i, choice in enumerate(choices, 1):
            console.print(f"  {i}. {choice}")

        while True:
            if default:
                response = console.input(f"Enter choice (1-{len(choices)}) or press Enter for '{default}': ").strip()
                if not response:
                    return default
            else:
                response = console.input(f"Enter choice (1-{len(choices)}): ").strip()

            try:
                choice_num = int(response)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
            except ValueError:
                pass

            print_error(f"Please enter a number between 1 and {len(choices)}")

    def prompt_input(self, message: str, default: str | None = None, validator: Callable[[str], str] | None = None) -> str:
        """Prompt user for input with optional validation."""
        while True:
            if default:
                response = console.input(f"{message} (default: {default}): ").strip()
                if not response:
                    response = default
            else:
                response = console.input(f"{message}: ").strip()

            if validator:
                try:
                    validator(response)
                    return str(response)
                except ValueError as e:
                    print_error(str(e))
            else:
                return str(response)

    def prompt_yes_no(self, message: str, default: bool = False) -> bool:
        """Prompt user for yes/no input."""
        default_text = "Y/n" if default else "y/N"
        while True:
            response = console.input(f"{message} ({default_text}): ").strip().lower()
            if not response:
                return default
            if response in ["y", "yes", "true", "1"]:
                return True
            if response in ["n", "no", "false", "0"]:
                return False
            print_error("Please enter 'y' or 'n'")

    def build_training_command(self) -> str:
        """Build a training command interactively."""
        console.print("\n[bold green]🚀 DSPy Training Command Builder[/bold green]")
        console.print("Let's build your training command step by step...")

        # Choose preset or custom
        use_preset = self.prompt_choice(
            "How would you like to configure your training?",
            ["Use a preset configuration", "Build custom configuration"],
            "Use a preset configuration"
        )

        if "preset" in use_preset:
            preset = self.prompt_choice(
                "Choose a preset:",
                ["quick", "development", "production", "experimental", "fast"],
                "quick"
            )
            command = f"hlpr train --preset {preset}"
        else:
            # Build custom configuration
            model = self.prompt_choice(
                "Choose a model:",
                ["ollama/gemma3", "gpt-3.5-turbo", "gpt-4", "claude-3-haiku"],
                "ollama/gemma3"
            )

            optimizer = self.prompt_choice(
                "Choose an optimizer:",
                ["bootstrap", "mipro", "copro", "bootstrap_random"],
                "bootstrap"
            )

            iters = self.prompt_input(
                "Number of optimization iterations",
                "5",
                self._validate_positive_int
            )

            include_unverified = self.prompt_yes_no(
                "Include unverified/noisy examples?",
                False
            )

            max_bootstrapped = self.prompt_input(
                "Maximum bootstrapped demonstrations",
                "4",
                self._validate_non_negative_int
            )

            max_labeled = self.prompt_input(
                "Maximum labeled demonstrations",
                "16",
                self._validate_non_negative_int
            )

            command = f"hlpr optimize-meeting --model {model} --optimizer {optimizer} --iters {iters}"
            if include_unverified:
                command += " --include-unverified"
            command += f" --max-bootstrapped-demos {max_bootstrapped} --max-labeled-demos {max_labeled}"

        # Show advanced options
        show_advanced = self.prompt_yes_no(
            "Would you like to see advanced options?",
            False
        )

        if show_advanced:
            console.print("\n[bold blue]Advanced Options:[/bold blue]")
            console.print("  --dry-run          Show command without executing")
            console.print("  --verbose          Show detailed output")
            console.print("  --help             Show help information")

        return command

    def build_meeting_command(self) -> str:
        """Build a meeting summarization command interactively."""
        console.print("\n[bold green]📝 Meeting Summarization Command Builder[/bold green]")

        meeting_id = self.prompt_input(
            "Enter meeting ID",
            validator=self._validate_non_empty
        )

        preset = self.prompt_choice(
            "Choose output preset:",
            ["default", "detailed", "minimal"],
            "default"
        )

        use_custom_model = self.prompt_yes_no(
            "Use custom model? (default: ollama/gemma3)",
            False
        )

        if use_custom_model:
            model = self.prompt_choice(
                "Choose model:",
                ["ollama/gemma3", "gpt-3.5-turbo", "gpt-4", "claude-3-haiku"],
                "ollama/gemma3"
            )
            command = f"hlpr quick-meeting {meeting_id} --preset {preset} --model {model}"
        else:
            command = f"hlpr quick-meeting {meeting_id} --preset {preset}"

        return command

    def build_workflow_command(self) -> str:
        """Build a workflow command interactively."""
        console.print("\n[bold green]⚡ Workflow Command Builder[/bold green]")

        workflow_type = self.prompt_choice(
            "What type of workflow would you like to create?",
            ["Run predefined workflow", "Create command chain", "Run development tasks"],
            "Run predefined workflow"
        )

        if "predefined" in workflow_type:
            workflow = self.prompt_choice(
                "Choose workflow:",
                ["setup-dev", "quick-train", "full-train", "cleanup"],
                "setup-dev"
            )
            command = f"hlpr workflow {workflow}"

        elif "command chain" in workflow_type:
            console.print("\nEnter commands to chain (one per line, empty line to finish):")
            commands = []
            while True:
                cmd = console.input("Command: ").strip()
                if not cmd:
                    break
                commands.append(cmd)

            if commands:
                command = f"hlpr chain {' '.join(f'"{cmd}"' for cmd in commands)}"
            else:
                print_error("No commands entered")
                return ""

        else:  # development tasks
            task = self.prompt_choice(
                "Choose development task:",
                ["dev", "dev-stop", "test", "lint", "quality", "clean"],
                "dev"
            )
            command = f"hlpr task {task}"

        return command

    def run_wizard(self) -> None:
        """Run the main wizard interface."""
        console.print("\n[bold green]🎯 hlpr Command Builder Wizard[/bold green]")
        console.print("Welcome! Let's build your command interactively...")

        command_type = self.prompt_choice(
            "What would you like to do?",
            ["Train DSPy model", "Summarize meeting", "Run workflow", "Manage environment"],
            "Train DSPy model"
        )

        if "Train" in command_type:
            command = self.build_training_command()
        elif "Summarize" in command_type:
            command = self.build_meeting_command()
        elif "Run workflow" in command_type:
            command = self.build_workflow_command()
        else:  # Manage environment
            action = self.prompt_choice(
                "Choose environment action:",
                ["Show environment info", "List presets", "List profiles", "List tasks"],
                "Show environment info"
            )

            if "environment" in action:
                command = "hlpr env-info"
            elif "presets" in action:
                command = "hlpr presets"
            elif "profiles" in action:
                command = "hlpr profile"
            else:
                command = "hlpr task --list"

        if command:
            console.print(f"\n[bold green]Generated command:[/bold green] {command}")

            execute_now = self.prompt_yes_no(
                "Would you like to execute this command now?",
                False
            )

            if execute_now:
                print_info("Executing command...")
                from hlpr.cli.executor import smart_execute
                try:
                    smart_execute(command)
                except Exception as e:
                    print_error(f"Command execution failed: {e}")
            else:
                print_info("Command copied to clipboard (you can copy and run it manually)")
        else:
            print_error("No command generated")


# Global wizard instance
_wizard: CommandWizard | None = None


def get_wizard() -> CommandWizard:
    """Get the global wizard instance."""
    global _wizard
    if _wizard is None:
        _wizard = CommandWizard()
    return _wizard


def run_wizard() -> None:
    """Run the command builder wizard."""
    get_wizard().run_wizard()