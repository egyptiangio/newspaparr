"""
WSGI entry point for production deployment
"""
import os
import logging
import logging.handlers

# Configure logging BEFORE importing app
logs_dir = os.path.join(os.path.dirname(__file__), 'data', 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Console handler
        logging.StreamHandler(),
        # File handler with rotation
        logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, 'newspaparr.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ],
    force=True  # Force reconfiguration even if logging is already configured
)

# Log that we've initialized
logger = logging.getLogger(__name__)
logger.info("📝 Logging initialized from wsgi.py")

from app import create_app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    app.run()