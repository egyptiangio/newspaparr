"""
Centralized browser configuration to ensure user agent consistency
across all components for CapSolver DataDome compatibility
"""
import os

# CapSolver-supported user agent for DataDome CAPTCHA solving
# Must be identical across browser initialization and CAPTCHA API calls
# Source: Environment variable set in docker-compose.yml
CAPSOLVER_USER_AGENT = os.environ.get(
    'CAPSOLVER_USER_AGENT', 
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
)

# Platform information extracted from user agent
PLATFORM = "Win32"
PLATFORM_VERSION = "10.0.0"

# Log the user agent being used for consistency verification
import logging
logger = logging.getLogger(__name__)
logger.info(f"🎭 Using centralized User-Agent: {CAPSOLVER_USER_AGENT}")