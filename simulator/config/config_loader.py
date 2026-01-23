"""
Configuration loader for simulated robot responses.

This module loads JSON configuration files and creates command handlers
that can be used by the simulator.

Supports:
- Base configuration that all models share
- Model-specific configurations that extend/override the base
- Command overrides by name (change handler, response, or disable)
- Case-insensitive command matching
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field

from .handlers import get_handler, HANDLER_REGISTRY


@dataclass
class CommandConfig:
    """Configuration for a single command."""
    name: str
    pattern: str
    compiled_pattern: re.Pattern
    handler_name: Optional[str]
    handler: Optional[Callable]
    default_response: Optional[str]
    description: str
    enabled: bool = True


class ResponseConfigLoader:
    """
    Loads and manages response configuration from JSON files.
    
    Supports hierarchical configuration:
    - Base config contains common commands for all models
    - Model-specific configs extend the base and can override handlers
    - Commands can be disabled by setting "enabled": false
    
    Usage:
        loader = ResponseConfigLoader()
        loader.load_config("path/to/config.json")
        
        # Or load from the default config directory (with inheritance)
        loader.load_default_config("mirobot")
        
        # Process a command
        response = loader.process_command("?", state, context)
    """
    
    def __init__(self):
        self.commands: List[CommandConfig] = []
        self.settings: Dict[str, Any] = {
            "unknown_command_response": "error",
            "command_delay_ms": 0,
            "case_sensitive": False,
        }
        self._config_data: Dict = {}
        self._command_dict: Dict[str, Dict] = {}  # name -> config dict
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the path to the config directory."""
        return Path(__file__).parent
    
    @classmethod
    def get_default_config_path(cls, model: str) -> Path:
        """Get the path to a model's default config file."""
        return cls.get_config_dir() / f"{model}_responses.json"
    
    def _load_json_file(self, config_path: str) -> Dict:
        """Load a JSON file and return the parsed data."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """
        Merge override config into base config.
        
        Commands with the same name in override will update the base command.
        New commands in override will be added.
        Commands with "enabled": false will be marked as disabled.
        """
        result = {
            "commands": [],
            "custom_commands": [],
            "settings": {},
        }
        
        # Merge settings
        result["settings"].update(base.get("settings", {}))
        result["settings"].update(override.get("settings", {}))
        
        # Build command dict from base
        base_commands = {}
        for cmd in base.get("commands", []):
            name = cmd.get("name")
            if name:
                base_commands[name] = cmd.copy()
        
        for cmd in base.get("custom_commands", []):
            name = cmd.get("name")
            if name and cmd.get("pattern"):
                base_commands[name] = cmd.copy()
        
        # Apply overrides
        for cmd in override.get("commands", []):
            name = cmd.get("name")
            if name:
                if name in base_commands:
                    # Override existing command
                    base_commands[name].update({k: v for k, v in cmd.items() if k != "_comment"})
                else:
                    # New command
                    base_commands[name] = cmd.copy()
        
        for cmd in override.get("custom_commands", []):
            name = cmd.get("name")
            if name and cmd.get("pattern"):
                if name in base_commands:
                    base_commands[name].update({k: v for k, v in cmd.items() if k != "_comment"})
                else:
                    base_commands[name] = cmd.copy()
        
        # Convert back to list
        result["commands"] = list(base_commands.values())
        
        return result
    
    def load_config(self, config_path: str) -> None:
        """
        Load configuration from a JSON file (with inheritance support).
        
        Args:
            config_path: Path to the JSON configuration file
        """
        config_data = self._load_json_file(config_path)
        
        # Check for inheritance
        extends = config_data.get("_extends")
        if extends:
            base_path = self.get_default_config_path(extends)
            if base_path.exists():
                base_data = self._load_json_file(str(base_path))
                config_data = self._merge_configs(base_data, config_data)
        
        self._config_data = config_data
        self._parse_config()
    
    def load_default_config(self, model: str) -> None:
        """
        Load the default configuration for a robot model.
        
        This will automatically load the base config first if the model
        config specifies "_extends": "base".
        
        Args:
            model: Robot model name (e.g., "mirobot", "e4", "mt4", "ms4220")
        """
        config_path = self.get_default_config_path(model)
        if config_path.exists():
            self.load_config(str(config_path))
        else:
            # Try base config
            base_path = self.get_default_config_path("base")
            if base_path.exists():
                self.load_config(str(base_path))
            else:
                # No config file exists - use empty config
                self._config_data = {"commands": [], "custom_commands": [], "settings": {}}
                self._parse_config()
    
    def load_from_dict(self, config: Dict, base_config: Optional[Dict] = None) -> None:
        """
        Load configuration from a dictionary.
        
        Args:
            config: Configuration dictionary
            base_config: Optional base config to extend
        """
        if base_config:
            config = self._merge_configs(base_config, config)
        
        self._config_data = config
        self._parse_config()
    
    def _parse_config(self) -> None:
        """Parse the loaded configuration data."""
        self.commands = []
        self._command_dict = {}
        
        # Load settings
        if "settings" in self._config_data:
            self.settings.update(self._config_data["settings"])
        
        # Load all commands (from merged config)
        for cmd in self._config_data.get("commands", []):
            self._add_command(cmd)
        
        # Load custom commands (if not already merged)
        for cmd in self._config_data.get("custom_commands", []):
            if cmd.get("pattern"):
                self._add_command(cmd)
    
    def _add_command(self, cmd_config: Dict) -> None:
        """Add a command from configuration."""
        # Check if command is enabled
        if cmd_config.get("enabled") is False:
            return
        
        pattern = cmd_config.get("pattern", "")
        if not pattern:
            return
        
        handler_name = cmd_config.get("handler")
        handler = get_handler(handler_name) if handler_name else None
        
        # Always use case-insensitive matching (as per requirement)
        flags = 0 if self.settings.get("case_sensitive", False) else re.IGNORECASE
        
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            print(f"Warning: Invalid regex pattern '{pattern}': {e}")
            return
        
        cmd = CommandConfig(
            name=cmd_config.get("name", "unnamed"),
            pattern=pattern,
            compiled_pattern=compiled,
            handler_name=handler_name,
            handler=handler,
            default_response=cmd_config.get("response"),
            description=cmd_config.get("description", ""),
            enabled=cmd_config.get("enabled", True),
        )
        
        self.commands.append(cmd)
        self._command_dict[cmd.name] = cmd_config
    
    def add_command(
        self,
        name: str,
        pattern: str,
        handler_name: Optional[str] = None,
        response: Optional[str] = None,
        description: str = ""
    ) -> None:
        """
        Add a command programmatically.
        
        Args:
            name: Command name
            pattern: Regex pattern to match
            handler_name: Name of handler function (from handlers.py)
            response: Default response if handler returns None
            description: Description of the command
        """
        handler = get_handler(handler_name) if handler_name else None
        flags = 0 if self.settings.get("case_sensitive", False) else re.IGNORECASE
        
        self.commands.append(CommandConfig(
            name=name,
            pattern=pattern,
            compiled_pattern=re.compile(pattern, flags),
            handler_name=handler_name,
            handler=handler,
            default_response=response,
            description=description,
        ))
    
    def process_command(
        self,
        command: str,
        state: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Process a command and return the response.
        
        Args:
            command: The command string to process
            state: The robot state object
            context: Additional context (send_response callback, versions, etc.)
            
        Returns:
            Tuple of (matched, response):
            - matched: True if a matching command was found
            - response: The response string, or None
        """
        for cmd in self.commands:
            match = cmd.compiled_pattern.match(command)
            if match:
                response = None
                
                # Call handler if available
                if cmd.handler:
                    try:
                        response = cmd.handler(command, match, state, context)
                    except Exception as e:
                        print(f"Handler error for '{cmd.name}': {e}")
                        response = None
                
                # Use default response if handler didn't return one
                if response is None:
                    response = cmd.default_response
                
                return True, response
        
        # No matching command found
        return False, self.settings.get("unknown_command_response", "error")
    
    def get_command_list(self) -> List[Dict]:
        """Get a list of all configured commands."""
        return [
            {
                "name": cmd.name,
                "pattern": cmd.pattern,
                "handler": cmd.handler_name,
                "response": cmd.default_response,
                "description": cmd.description,
            }
            for cmd in self.commands
        ]
    
    def save_config(self, config_path: str) -> None:
        """
        Save the current configuration to a JSON file.
        
        Args:
            config_path: Path to save the configuration
        """
        config = {
            "commands": [],
            "custom_commands": [],
            "settings": self.settings,
        }
        
        for cmd in self.commands:
            cmd_dict = {
                "name": cmd.name,
                "pattern": cmd.pattern,
                "handler": cmd.handler_name,
                "response": cmd.default_response,
                "description": cmd.description,
            }
            config["commands"].append(cmd_dict)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)


def load_config(model: str = "mirobot") -> ResponseConfigLoader:
    """
    Convenience function to load a configuration.
    
    Args:
        model: Robot model name
        
    Returns:
        Configured ResponseConfigLoader instance
    """
    loader = ResponseConfigLoader()
    loader.load_default_config(model)
    return loader
