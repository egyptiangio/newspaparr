"""
Centralized browser configuration to ensure user agent consistency
across all components for CapSolver DataDome compatibility
"""
import os
import logging

logger = logging.getLogger(__name__)

def get_capsolver_user_agent():
    """
    Get the CapSolver user agent from environment variable.
    Raises ValueError if not set when actually needed.
    This allows the module to be imported during build time without the env var.
    """
    user_agent = os.environ.get('CAPSOLVER_USER_AGENT')
    if not user_agent:
        raise ValueError(
            "CAPSOLVER_USER_AGENT environment variable MUST be set in docker-compose.yml\n"
            "Use one of the CapSolver-supported versions:\n"
            "  - Chrome/137.0.0.0 (recommended)\n"
            "  - Chrome/136.0.0.0\n"
            "  - Chrome/135.0.0.0\n"
            "  - Chrome/134.0.0.0\n"
            "  - Chrome/133.0.0.0\n"
            "  - Chrome/132.0.0.0\n"
            "See: https://docs.capsolver.com/en/guide/captcha/datadome/"
        )
    return user_agent

# Lazy property that only checks when accessed
class _UserAgentProperty:
    def __repr__(self):
        return get_capsolver_user_agent()
    
    def __str__(self):
        return get_capsolver_user_agent()
    
    def __bool__(self):
        try:
            return bool(get_capsolver_user_agent())
        except ValueError:
            return False

# This will only raise an error when actually accessed, not on import
CAPSOLVER_USER_AGENT = _UserAgentProperty()

# Platform information extracted from user agent
PLATFORM = "Win32"
PLATFORM_VERSION = "10.0.0"

# Helper function for logging (only logs if user agent is available)
def log_user_agent():
    try:
        user_agent = get_capsolver_user_agent()
        logger.info(f"🎭 Using centralized User-Agent: {user_agent}")
    except ValueError:
        logger.debug("CAPSOLVER_USER_AGENT not set yet (expected during build)")