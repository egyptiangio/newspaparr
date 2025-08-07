"""
Configuration validation module for Newspaparr
Validates required environment variables and system configuration
"""
import os
import sys
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
try:
    import zoneinfo
    TIMEZONE_MODULE = 'zoneinfo'
except ImportError:
    try:
        import pytz
        TIMEZONE_MODULE = 'pytz'
    except ImportError:
        TIMEZONE_MODULE = None

from error_handling import StandardizedLogger


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    config: Dict[str, Any]


class ConfigValidator:
    """Validates and provides configuration for Newspaparr"""
    
    def __init__(self):
        self.logger = StandardizedLogger(__name__)
        
        # Define required and optional configuration
        self.required_config = {
            'DATABASE_URL': {
                'description': 'Database connection URL',
                'default': 'sqlite:////app/data/newspaparr.db',
                'validator': self._validate_database_url
            },
            'SECRET_KEY': {
                'description': 'Flask secret key for sessions',
                'default': 'legacy-newspaparr-default-key',  # Default for legacy compatibility
                'validator': self._validate_secret_key
            },
            'TZ': {
                'description': 'Timezone for scheduling',
                'default': 'America/New_York',
                'validator': self._validate_timezone
            }
        }
        
        self.optional_config = {
            # CAPTCHA Configuration
            'CAPSOLVER_API_KEY': {
                'description': 'CapSolver API key for CAPTCHA solving',
                'default': '',
                'validator': self._validate_capsolver_key
            },
            'PROXY_HOST': {
                'description': 'Proxy host for CAPTCHA services',
                'default': 'localhost',
                'validator': self._validate_host
            },
            'SOCKS5_PROXY_PORT': {
                'description': 'SOCKS5 proxy port',
                'default': '3333',
                'validator': self._validate_port
            },
            
            # Renewal Behavior
            'RENEWAL_DEBUG': {
                'description': 'Enable debug mode with screenshots',
                'default': 'false',
                'validator': self._validate_boolean
            },
            'RENEWAL_SPEED': {
                'description': 'Renewal speed setting',
                'default': 'normal',
                'validator': self._validate_speed
            },
            'RENEWAL_SCREENSHOT_RETENTION': {
                'description': 'Number of screenshots to retain',
                'default': '100',
                'validator': self._validate_positive_int
            },
            
            # System Configuration
            'PUID': {
                'description': 'Process User ID',
                'default': '1000',
                'validator': self._validate_positive_int
            },
            'PGID': {
                'description': 'Process Group ID',
                'default': '1000',
                'validator': self._validate_positive_int
            },
            'FLASK_DEBUG': {
                'description': 'Flask debug mode',
                'default': 'false',
                'validator': self._validate_boolean
            },
            'DISPLAY': {
                'description': 'X11 display for GUI mode',
                'default': None,
                'validator': self._validate_display
            }
        }
    
    def validate_config(self, check_production: bool = False) -> ConfigValidationResult:
        """Validate all configuration"""
        errors = []
        warnings = []
        config = {}
        
        # Validate required configuration
        for key, spec in self.required_config.items():
            value = os.environ.get(key, spec['default'])
            
            # Check if required for production
            if check_production and spec.get('required_for_production', False) and not value:
                errors.append(f"❌ {key} is required for production but not set")
                continue
            
            # Use default if not set
            if value is None:
                if spec.get('required_for_production', False):
                    errors.append(f"❌ {key} is required but not set")
                    continue
                value = spec.get('default', '')
            
            # Validate value
            if spec.get('validator'):
                try:
                    validated_value = spec['validator'](value, key)
                    config[key] = validated_value
                except ValueError as e:
                    errors.append(f"❌ {key}: {str(e)}")
            else:
                config[key] = value
        
        # Validate optional configuration
        for key, spec in self.optional_config.items():
            value = os.environ.get(key, spec['default'])
            
            if value is not None and spec.get('validator'):
                try:
                    validated_value = spec['validator'](value, key)
                    config[key] = validated_value
                except ValueError as e:
                    warnings.append(f"⚠️ {key}: {str(e)}")
                    config[key] = spec['default']  # Use default on validation failure
            else:
                config[key] = value
        
        # Additional system checks
        self._check_system_dependencies(warnings, errors)
        self._check_captcha_configuration(config, warnings)
        self._check_database_setup(config, warnings, errors)
        
        is_valid = len(errors) == 0
        
        return ConfigValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            config=config
        )
    
    def _validate_database_url(self, value: str, key: str) -> str:
        """Validate database URL"""
        if not value:
            raise ValueError("Database URL cannot be empty")
        
        # Check if SQLite path is accessible
        if value.startswith('sqlite:///'):
            db_path = value.replace('sqlite:///', '')
            db_dir = Path(db_path).parent
            
            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    raise ValueError(f"Cannot create database directory: {db_dir}")
        
        return value
    
    def _validate_secret_key(self, value: str, key: str) -> str:
        """Validate Flask secret key"""
        if not value:
            raise ValueError("Secret key cannot be empty")
        
        # For legacy compatibility, allow shorter keys without validation
        return value
    
    def _validate_timezone(self, value: str, key: str) -> str:
        """Validate timezone"""
        if not TIMEZONE_MODULE:
            # Skip validation if no timezone module available
            return value
            
        try:
            if TIMEZONE_MODULE == 'zoneinfo':
                zoneinfo.ZoneInfo(value)
            elif TIMEZONE_MODULE == 'pytz':
                import pytz
                pytz.timezone(value)
            return value
        except Exception:
            raise ValueError(f"Unknown timezone: {value}")
    
    def _validate_capsolver_key(self, value: str, key: str) -> str:
        """Validate CapSolver API key"""
        if value and not value.startswith('CAP-'):
            raise ValueError("CapSolver API key should start with 'CAP-'")
        return value
    
    def _validate_host(self, value: str, key: str) -> str:
        """Validate hostname"""
        if not value:
            raise ValueError("Host cannot be empty")
        return value
    
    def _validate_port(self, value: str, key: str) -> int:
        """Validate port number"""
        try:
            port = int(value)
            if not (1 <= port <= 65535):
                raise ValueError(f"Port must be between 1 and 65535")
            return port
        except ValueError:
            raise ValueError(f"Invalid port number: {value}")
    
    def _validate_boolean(self, value: str, key: str) -> bool:
        """Validate boolean value"""
        if isinstance(value, bool):
            return value
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif value.lower() in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ValueError(f"Invalid boolean value: {value}")
    
    def _validate_speed(self, value: str, key: str) -> str:
        """Validate renewal speed setting"""
        valid_speeds = ['fast', 'normal', 'slow']
        if value.lower() not in valid_speeds:
            raise ValueError(f"Speed must be one of: {', '.join(valid_speeds)}")
        return value.lower()
    
    def _validate_positive_int(self, value: str, key: str) -> int:
        """Validate positive integer"""
        try:
            num = int(value)
            if num <= 0:
                raise ValueError(f"Must be a positive integer")
            return num
        except ValueError:
            raise ValueError(f"Invalid integer: {value}")
    
    def _validate_display(self, value: Optional[str], key: str) -> Optional[str]:
        """Validate X11 display"""
        # DISPLAY can be None (will be set by virtual display)
        return value
    
    def _check_system_dependencies(self, warnings: List[str], errors: List[str]):
        """Check system dependencies"""
        # Check Chrome/Chromium
        chrome_paths = [
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome'
        ]
        
        chrome_available = any(Path(path).exists() for path in chrome_paths)
        if not chrome_available:
            errors.append("❌ Chrome/Chromium browser not found")
        
        # Check if running in Docker
        if Path('/.dockerenv').exists():
            self.logger.debug("Running in Docker container")
        
        # Always using GUI mode with virtual display for better anti-detection
        if not os.environ.get('DISPLAY'):
            warnings.append("⚠️ No DISPLAY set - virtual display will be used for GUI mode")
    
    def _check_captcha_configuration(self, config: Dict[str, Any], warnings: List[str]):
        """Check CAPTCHA configuration"""
        capsolver_key = config.get('CAPSOLVER_API_KEY', '')
        
        if not capsolver_key:
            warnings.append("⚠️ No CapSolver API key configured - CAPTCHA solving disabled")
        else:
            # Check if proxy configuration is complete
            proxy_host = config.get('PROXY_HOST', '')
            proxy_port = int(config.get('SOCKS5_PROXY_PORT', 0))
            
            if not proxy_host or proxy_host == 'localhost':
                warnings.append("⚠️ PROXY_HOST is localhost - CapSolver may not be able to connect")
            
            if not (1000 <= proxy_port <= 65535):
                warnings.append("⚠️ SOCKS5_PROXY_PORT should typically be between 1000-65535")
    
    def _check_database_setup(self, config: Dict[str, Any], warnings: List[str], errors: List[str]):
        """Check database setup"""
        db_url = config.get('DATABASE_URL', '')
        
        if db_url.startswith('sqlite:///'):
            db_path = Path(db_url.replace('sqlite:///', ''))
            
            if db_path.exists():
                # Check if writable
                try:
                    db_path.touch(exist_ok=True)
                except PermissionError:
                    errors.append(f"❌ Database file not writable: {db_path}")
            else:
                # Check if directory is writable
                try:
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    errors.append(f"❌ Cannot create database directory: {db_path.parent}")
    
    def print_validation_report(self, result: ConfigValidationResult):
        """Print configuration validation report"""
        logger = StandardizedLogger(__name__)
        
        if result.is_valid:
            logger.info("Configuration validation passed")
        else:
            logger.error("Configuration validation failed")
        
        # Log errors
        for error in result.errors:
            logger.error(f"Config error: {error}")
        
        # Log warnings
        for warning in result.warnings:
            logger.warning(f"Config warning: {warning}")
        
        # Log key configuration (for debugging)
        if os.environ.get('RENEWAL_DEBUG', 'false').lower() == 'true':
            key_configs = ['SECRET_KEY', 'DATABASE_URL', 'TZ', 'CAPSOLVER_API_KEY']
            for key in key_configs:
                if key in result.config:
                    value = result.config[key]
                    # Mask sensitive values
                    if key in ['SECRET_KEY', 'CAPSOLVER_API_KEY'] and value:
                        value = f"{value[:8]}..." if len(str(value)) > 8 else "***"
                    logger.debug(f"Config {key}: {value}")
                    
        # Still print summary for startup
        if result.errors:
            print(f"❌ Configuration errors: {len(result.errors)}")
        if result.warnings:
            print(f"⚠️ Configuration warnings: {len(result.warnings)}")
        if result.is_valid:
            print("✅ Configuration validated")


def validate_startup_config() -> bool:
    """Validate configuration at startup"""
    validator = ConfigValidator()
    result = validator.validate_config(check_production=False)
    
    validator.print_validation_report(result)
    
    if not result.is_valid:
        return False
    
    return True


def get_validated_config() -> Dict[str, Any]:
    """Get validated configuration dictionary"""
    validator = ConfigValidator()
    result = validator.validate_config()
    return result.config


if __name__ == "__main__":
    # Allow running as standalone script for validation
    success = validate_startup_config()
    sys.exit(0 if success else 1)