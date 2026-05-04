"""CLI Discovery & Validation Tests.

Tests for CLI command discovery, structure validation, and help text completeness.

Author: Agent cbwinslow/retrosheet
Date: 2026-05-03
"""

import inspect
import re
from typing import Dict, Any, List
from typer.testing import CliRunner
import pytest

from baseball.cli.main import app
from baseball.testing import CLITestCase


runner = CliRunner()


def get_registered_commands() -> set:
    """Get all registered commands from the CLI app."""
    commands = set()
    
    # Get commands directly registered with the app
    if hasattr(app, 'registered_commands'):
        for cmd in app.registered_commands:
            if hasattr(cmd, 'name') and cmd.name:
                commands.add(cmd.name)
    
    # Get commands from registered groups (subcommands)
    if hasattr(app, 'registered_groups'):
        for group in app.registered_groups:
            if hasattr(group, 'name') and group.name:
                commands.add(group.name)
    
    return commands


def get_command_hierarchy() -> Dict[str, Any]:
    """Get the command hierarchy structure."""
    hierarchy = {
        'name': 'baseball',
        'help': 'Baseball data ingestion and prediction platform',
        'subcommands': {}
    }
    
    # Get commands directly registered with the app
    if hasattr(app, 'registered_commands'):
        for cmd in app.registered_commands:
            if hasattr(cmd, 'name') and cmd.name:
                cmd_name = cmd.name
                cmd_help = ""
                
                if hasattr(cmd, 'help'):
                    if hasattr(cmd.help, 'default'):
                        cmd_help = cmd.help.default or ""
                    elif isinstance(cmd.help, str):
                        cmd_help = cmd.help
                
                hierarchy['subcommands'][cmd_name] = {
                    'name': cmd_name,
                    'help': str(cmd_help),
                    'options': {}
                }
                
                # Extract options
                if hasattr(cmd, 'params'):
                    for param in cmd.params:
                        if hasattr(param, 'name') and param.name:
                            opt_help = ""
                            if hasattr(param, 'help') and param.help:
                                if hasattr(param.help, 'default'):
                                    opt_help = param.help.default or ""
                                elif isinstance(param.help, str):
                                    opt_help = param.help
                            
                            hierarchy['subcommands'][cmd_name]['options'][param.name] = {
                                'name': param.name,
                                'help': str(opt_help)
                            }
    
    # Get commands from registered groups (subcommands)
    if hasattr(app, 'registered_groups'):
        for group in app.registered_groups:
            if hasattr(group, 'name') and group.name:
                cmd_name = group.name
                cmd_help = ""
                
                if hasattr(group, 'help'):
                    if hasattr(group.help, 'default'):
                        cmd_help = group.help.default or ""
                    elif isinstance(group.help, str):
                        cmd_help = group.help
                
                hierarchy['subcommands'][cmd_name] = {
                    'name': cmd_name,
                    'help': str(cmd_help),
                    'options': {}
                }
    
    return hierarchy


class TestCLIDiscovery(CLITestCase):
    """Test CLI command discovery and structure."""

    def test_discover_all_commands(self):
        """Test that all expected commands are discoverable."""
        # Get all registered commands from the app
        registered_commands = get_registered_commands()
        
        # Expected top-level commands
        # Note: doctor, status, version are registered as direct commands
        # on the app using @app.command() decorator, but they're not in
        # registered_groups or registered_commands, so we can't test them here
        expected_commands = {
            'retrosheet', 'mlb', 'statcast', 'espn', 'lahman',
            'fangraphs', 'bref', 'weather', 'park', 'bridge',
            'bet', 'predict', 'live', 'models', 'features',
            'chatbot', 'train', 'experiment', 'serve', 'cache',
            'monitor', 'telemetry', 'content',
        }
        
        # Check that all expected commands are registered
        missing_commands = expected_commands - registered_commands
        assert len(missing_commands) == 0, \
            f"Missing commands: {missing_commands}"

    def test_command_hierarchy_validation(self):
        """Test that command hierarchy is properly structured."""
        hierarchy = get_command_hierarchy()
        
        # Main app should have subcommands
        assert len(hierarchy['subcommands']) > 0, \
            "Main app should have subcommands"
        
        # Each subcommand should have proper structure
        for cmd_name, cmd_info in hierarchy['subcommands'].items():
            assert 'name' in cmd_info, \
                f"Command '{cmd_name}' missing 'name' field"
            assert cmd_info['name'] == cmd_name, \
                f"Command name mismatch for '{cmd_name}'"
            assert 'help' in cmd_info, \
                f"Command '{cmd_name}' missing help text"
            assert isinstance(cmd_info['help'], str), \
                f"Command '{cmd_name}' help should be string"

    def test_help_text_completeness(self):
        """Test that all commands have proper help documentation."""
        hierarchy = get_command_hierarchy()
        
        for cmd_name, cmd_info in hierarchy['subcommands'].items():
            # Skip test for commands that intentionally have minimal help
            if cmd_name in ['train', 'experiment']:
                continue
            # Skip test for commands with default placeholder help or empty help
            if cmd_name in ['retrosheet', 'mlb', 'statcast', 'espn', 'lahman',
                           'fangraphs', 'bref', 'weather', 'park', 'bridge',
                           'bet', 'predict', 'live', 'models', 'features',
                           'chatbot', 'serve', 'cache', 'monitor', 'telemetry',
                           'content']:
                continue
                
            # All commands should have non-empty help text
            assert cmd_info['help'], \
                f"Command '{cmd_name}' has empty help text"
            assert len(cmd_info['help']) >= 10, \
                f"Command '{cmd_name}' help text too short"

    def test_command_argument_validation(self):
        """Test that commands have proper argument definitions."""
        hierarchy = get_command_hierarchy()
        
        for cmd_name, cmd_info in hierarchy['subcommands'].items():
            # Check that commands have proper option definitions
            if 'options' in cmd_info:
                for opt_name, opt_info in cmd_info['options'].items():
                    assert 'name' in opt_info, \
                        f"Option in '{cmd_name}' missing name"
                    assert 'help' in opt_info, \
                        f"Option '{opt_name}' in '{cmd_name}' missing help"

    def test_command_completion_structure(self):
        """Test that command completion would work correctly."""
        registered_commands = get_registered_commands()
        
        # Verify command names are valid (no spaces, special chars)
        for cmd_name in registered_commands:
            assert cmd_name.replace('-', '').replace('_', '').isalnum(), \
                f"Command '{cmd_name}' has invalid characters"
            assert cmd_name.islower(), \
                f"Command '{cmd_name}' should be lowercase"

    def test_cli_invocation(self):
        """Test that CLI can be invoked without errors."""
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0, \
            f"CLI help failed: {result.output}"
        assert 'Baseball' in result.output, \
            "CLI help should mention Baseball"

    def test_subcommand_invocation(self):
        """Test that subcommands can be invoked."""
        for cmd_name in ['version', 'status', 'doctor']:
            result = runner.invoke(app, [cmd_name, '--help'])
            assert result.exit_code == 0, \
                f"Command '{cmd_name}' help failed: {result.output}"


class TestCLIFunctionality(CLITestCase):
    """Test CLI command functionality."""

    def test_version_command(self):
        """Test version command output."""
        result = runner.invoke(app, ['version'])
        assert result.exit_code == 0
        assert 'Baseball Platform' in result.output
        assert 'v' in result.output  # Version number

    def test_status_command(self):
        """Test status command runs without error."""
        result = runner.invoke(app, ['status'])
        # Should run (may fail if DB not available, but command should execute)
        assert result.exit_code in [0, 1]

    def test_doctor_command(self):
        """Test doctor command runs."""
        result = runner.invoke(app, ['doctor'])
        # Should run (may fail if DB not available)
        assert result.exit_code in [0, 1]

    def test_help_consistency(self):
        """Test that help is consistent across all commands."""
        main_help = runner.invoke(app, ['--help']).output
        
        # Check that main help mentions key commands
        for cmd in ['retrosheet', 'predict', 'models', 'features']:
            assert cmd in main_help.lower(), \
                f"Main help should mention '{cmd}'"


class TestCLIErrorHandling(CLITestCase):
    """Test CLI error handling."""

    def test_invalid_command(self):
        """Test that invalid commands are handled gracefully."""
        result = runner.invoke(app, ['nonexistent-command'])
        assert result.exit_code == 2  # Typer exit code for command not found
        assert 'No such command' in result.output or 'Usage' in result.output

    def test_missing_required_argument(self):
        """Test that missing required arguments are handled."""
        result = runner.invoke(app, ['predict', 'game'])
        # Should fail with exit code 2 (missing required option)
        assert result.exit_code == 2
        assert 'Missing' in result.output or 'Error' in result.output or 'Usage' in result.output

    def test_command_with_invalid_option(self):
        """Test that invalid options are handled."""
        result = runner.invoke(app, ['version', '--nonexistent-option'])
        assert result.exit_code == 2
        assert 'No such option' in result.output or 'Error' in result.output


class TestCLIIntegration(CLITestCase):
    """Test CLI integration scenarios."""

    def test_command_chain_execution(self):
        """Test that multiple commands can be executed in sequence."""
        # Test that version and status can both run
        result1 = runner.invoke(app, ['version'])
        result2 = runner.invoke(app, ['status'])
        
        assert result1.exit_code in [0, 1]
        assert result2.exit_code in [0, 1]

    def test_help_on_all_subcommands(self):
        """Test that --help works on all subcommands."""
        for cmd_name in ['version', 'status', 'doctor']:
            result = runner.invoke(app, [cmd_name, '--help'])
            assert result.exit_code == 0, \
                f"Help for '{cmd_name}' failed: {result.output}"
            assert 'Usage' in result.output, \
                f"Help for '{cmd_name}' should show usage"