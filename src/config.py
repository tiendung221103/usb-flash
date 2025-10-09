"""Configuration module - Simple version."""

import yaml
import os

class Config:
    """Load and manage configuration."""
    
    def __init__(self, config_file='config.yaml'):
        """Load config from YAML file.
        
        Args:
            config_file: Path to config file
        """
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Apply environment variable overrides
        if vid := os.getenv('TARGET_VID'):
            self.config['target_device']['vid'] = vid
        
        if pid := os.getenv('TARGET_PID'):
            self.config['target_device']['pid'] = pid
        
        print(f"[Config] Loaded: VID={self['target_device']['vid']}, "
              f"PID={self['target_device']['pid']}")
    
    def get(self, key, default=None):
        """Get config value by dot notation.
        
        Args:
            key: Config key like 'target_device.vid'
            default: Default value if not found
            
        Returns:
            Config value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def __getitem__(self, key):
        """Dictionary-style access."""
        return self.config[key]
