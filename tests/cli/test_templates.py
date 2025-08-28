"""Unit tests for the command templates system."""
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from hlpr.cli.templates import CommandTemplate, TemplateManager


class TestCommandTemplate:
    """Tests for CommandTemplate class."""

    def test_create_template(self):
        """Test creating a command template."""
        template = CommandTemplate(
            name="test-template",
            description="A test template",
            command="echo {message}",
            parameters={"message": {"type": "str", "default": "hello"}},
        )

        assert template.name == "test-template"
        assert template.description == "A test template"
        assert template.command == "echo {message}"
        assert template.parameters == {"message": {"type": "str", "default": "hello"}}

    def test_to_dict(self):
        """Test converting template to dictionary."""
        template = CommandTemplate(
            name="test-template",
            description="A test template",
            command="echo {message}",
            parameters={"message": {"type": "str", "default": "hello"}},
        )

        result = template.to_dict()
        expected = {
            "name": "test-template",
            "description": "A test template",
            "command": "echo {message}",
            "parameters": {"message": {"type": "str", "default": "hello"}},
            "created_at": None,
            "updated_at": None,
        }

        assert result == expected

    def test_from_dict(self):
        """Test creating template from dictionary."""
        data = {
            "name": "test-template",
            "description": "A test template",
            "command": "echo {message}",
            "parameters": {"message": {"type": "str", "default": "hello"}},
        }

        template = CommandTemplate.from_dict(data)

        assert template.name == "test-template"
        assert template.description == "A test template"
        assert template.command == "echo {message}"
        assert template.parameters == {"message": {"type": "str", "default": "hello"}}

    def test_substitute_parameters(self):
        """Test parameter substitution in command."""
        template = CommandTemplate(
            name="test-template",
            description="A test template",
            command="echo {message} to {target}",
            parameters={
                "message": {"type": "str", "default": "hello"},
                "target": {"type": "str", "default": "world"}
            },
        )

        # Test with custom values
        result = template.substitute_parameters({"message": "hi", "target": "there"})
        assert result == "echo hi to there"

        # Test with default values
        result = template.substitute_parameters({})
        assert result == "echo hello to world"

        # Test with partial values
        result = template.substitute_parameters({"message": "goodbye"})
        assert result == "echo goodbye to world"

    def test_substitute_parameters_edge_cases(self):
        """Test parameter substitution edge cases."""
        template = CommandTemplate(
            name="test-template",
            description="A test template",
            command="echo {message}",
            parameters={"message": {"type": "str", "default": "hello"}},
        )

        # Test with None values
        result = template.substitute_parameters({"message": None})
        assert result == "echo None"

        # Test with empty string
        result = template.substitute_parameters({"message": ""})
        assert result == "echo "

        # Test with missing parameter (should use default)
        result = template.substitute_parameters({})
        assert result == "echo hello"


class TestTemplateManager:
    """Tests for TemplateManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Create a unique subdirectory for each test to avoid state leakage
        self.test_subdir = Path(self.temp_dir) / f"test_{int(time.time() * 1000000)}"
        self.test_subdir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_create_manager(self):
        """Test creating template manager."""
        manager = TemplateManager(templates_dir=self.test_subdir)
        assert manager.templates_dir.name == "templates"

    def test_save_and_load_templates(self):
        """Test saving and loading templates."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        # Create test template
        template = CommandTemplate(
            name="test-template",
            description="A test template",
            command="echo {message}",
            parameters={"message": {"type": "str", "default": "hello"}}
        )

        templates = {"test-template": template}
        manager.save_templates(templates)

        # Load templates back
        loaded_templates = manager.load_templates()
        assert len(loaded_templates) == 1
        assert "test-template" in loaded_templates

        loaded_template = loaded_templates["test-template"]
        assert loaded_template.name == template.name
        assert loaded_template.description == template.description
        assert loaded_template.command == template.command
        assert loaded_template.parameters == template.parameters

    def test_create_template(self):
        """Test creating a new template."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        result = manager.create_template(
            name="new-template",
            description="A new template",
            command="ls {path}",
            parameters={"path": {"type": "str", "default": "."}}
        )

        assert result is not None
        assert isinstance(result, CommandTemplate)
        assert result.name == "new-template"
        templates = manager.load_templates()
        assert "new-template" in templates

        template = templates["new-template"]
        assert template.name == "new-template"
        assert template.description == "A new template"
        assert template.command == "ls {path}"
        assert template.parameters == {"path": {"type": "str", "default": "."}}

    def test_get_template(self):
        """Test getting a template by name."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        # Create and save a template
        template = CommandTemplate(
            name="existing-template",
            description="An existing template",
            command="echo {text}",
            parameters={"text": {"type": "str", "default": "hello"}}
        )
        templates = {"existing-template": template}
        manager.save_templates(templates)

        # Get existing template
        result = manager.get_template("existing-template")
        assert result is not None
        assert result.name == "existing-template"

        # Get non-existing template
        result = manager.get_template("non-existing")
        assert result is None

    def test_delete_template(self):
        """Test deleting a template."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        # Create and save templates
        template1 = CommandTemplate(
            name="template1",
            description="Template 1",
            command="echo 1",
            parameters={}
        )
        template2 = CommandTemplate(
            name="template2",
            description="Template 2",
            command="echo 2",
            parameters={}
        )
        templates = {"template1": template1, "template2": template2}
        manager.save_templates(templates)

        # Delete existing template
        result = manager.delete_template("template1")
        assert result is True

        # Verify template was deleted
        templates = manager.load_templates()
        assert "template1" not in templates
        assert "template2" in templates

        # Delete non-existing template
        result = manager.delete_template("non-existing")
        assert result is False

    def test_list_templates(self):
        """Test listing all templates."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        # Empty list initially
        templates = manager.list_templates()
        assert len(templates) == 0

        # Add templates
        template1 = CommandTemplate(
            name="template1",
            description="Template 1",
            command="echo 1",
            parameters={}
        )
        template2 = CommandTemplate(
            name="template2",
            description="Template 2",
            command="echo 2",
            parameters={}
        )
        manager.save_templates({"template1": template1, "template2": template2})

        # List templates
        templates = manager.list_templates()
        assert len(templates) == 2
        template_names = [t.name for t in templates]
        assert "template1" in template_names
        assert "template2" in template_names

    def test_load_templates_corrupted_file(self):
        """Test loading templates from corrupted JSON file."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        # Write corrupted JSON
        manager.templates_file.write_text("invalid json content")

        # Should return empty dict on error
        templates = manager.load_templates()
        assert templates == {}

    def test_load_templates_missing_file(self):
        """Test loading templates when file doesn't exist."""
        manager = TemplateManager(templates_dir=self.test_subdir)

        # Should return empty dict when file doesn't exist
        templates = manager.load_templates()
        assert templates == {}


class TestTemplateIntegration:
    """Integration tests for template functionality."""

    def test_template_workflow(self):
        """Test complete template workflow."""
        # This test doesn't need mocking as it tests the actual classes
        template = CommandTemplate(
            name="workflow-template",
            description="A workflow template",
            command="echo {env} environment",
            parameters={"env": {"type": "str", "default": "dev"}},
        )

        # Test to_dict and from_dict round trip
        template_dict = template.to_dict()
        restored_template = CommandTemplate.from_dict(template_dict)

        assert restored_template.name == template.name
        assert restored_template.description == template.description
        assert restored_template.command == template.command
        assert restored_template.parameters == template.parameters

        # Test parameter substitution
        result = restored_template.substitute_parameters({"env": "prod"})
        assert result == "echo prod environment"


# Integration test placeholders for CLI commands
# These would require more complex mocking of typer and console
"""
def test_create_template_cli():
    # Test: hlpr template create
    pass

def test_run_template_cli():
    # Test: hlpr template run
    pass

def test_list_templates_cli():
    # Test: hlpr template list
    pass

def test_delete_template_cli():
    # Test: hlpr template delete
    pass

def test_show_template_cli():
    # Test: hlpr template show
    pass
"""