"""
On-demand SOCKS5 proxy server for CAPTCHA solving
Only starts when needed and automatically shuts down after use
"""
import asyncio
import logging
import threading
import time
import os
import signal
from typing import Optional
from contextlib import contextmanager
from socks5_proxy import SOCKS5Server
from error_handling import StandardizedLogger

logger = StandardizedLogger(__name__)


class OnDemandProxyManager:
    """Manages on-demand SOCKS5 proxy lifecycle"""
    
    def __init__(self, host='0.0.0.0', port=3333):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.loop = None
        self.is_running = False
        self.shutdown_timer = None
        self.auto_shutdown_delay = 300  # 5 minutes of inactivity
        
    def start_proxy(self) -> bool:
        """Start the proxy server if not already running"""
        if self.is_running:
            logger.info("Proxy already running", port=self.port)
            self._reset_shutdown_timer()
            return True
        
        try:
            logger.info("Starting on-demand SOCKS5 proxy", host=self.host, port=self.port)
            
            # Start server in separate thread
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            # Wait for server to start
            start_timeout = 10
            for _ in range(start_timeout * 10):  # Check every 100ms
                if self.is_running:
                    logger.info("SOCKS5 proxy started successfully", port=self.port)
                    self._reset_shutdown_timer()
                    return True
                time.sleep(0.1)
            
            logger.error("Proxy failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error("Failed to start proxy", error=e)
            return False
    
    def stop_proxy(self):
        """Stop the proxy server"""
        if not self.is_running:
            return
        
        logger.info("Stopping SOCKS5 proxy", port=self.port)
        
        try:
            # Cancel shutdown timer
            if self.shutdown_timer:
                self.shutdown_timer.cancel()
                self.shutdown_timer = None
            
            # Stop the server
            if self.loop and self.server:
                self.loop.call_soon_threadsafe(self.server.close)
            
            self.is_running = False
            
            # Wait for thread to finish
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logger.info("SOCKS5 proxy stopped")
            
        except Exception as e:
            logger.error("Error stopping proxy", error=e)
    
    def _run_server(self):
        """Run the server in async event loop"""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start server
            proxy_server = SOCKS5Server(self.host, self.port)
            
            async def start_server():
                self.server = await asyncio.start_server(
                    proxy_server.handle_client,
                    self.host,
                    self.port
                )
                self.is_running = True
                logger.info("SOCKS5 server listening", host=self.host, port=self.port)
                
                async with self.server:
                    await self.server.serve_forever()
            
            # Run server
            self.loop.run_until_complete(start_server())
            
        except Exception as e:
            logger.error("Server thread error", error=e)
            self.is_running = False
        finally:
            if self.loop:
                self.loop.close()
            self.is_running = False
    
    def _reset_shutdown_timer(self):
        """Reset the auto-shutdown timer"""
        # Cancel existing timer
        if self.shutdown_timer:
            self.shutdown_timer.cancel()
        
        # Start new timer
        self.shutdown_timer = threading.Timer(
            self.auto_shutdown_delay, 
            self._auto_shutdown
        )
        self.shutdown_timer.start()
        logger.debug(f"Auto-shutdown timer set for {self.auto_shutdown_delay}s")
    
    def _auto_shutdown(self):
        """Automatically shutdown proxy after inactivity"""
        logger.info("Auto-shutting down proxy after inactivity", 
                   delay=self.auto_shutdown_delay)
        self.stop_proxy()
    
    def is_proxy_running(self) -> bool:
        """Check if proxy is currently running"""
        return self.is_running
    
    def extend_session(self):
        """Extend the proxy session (reset shutdown timer)"""
        if self.is_running:
            self._reset_shutdown_timer()
            logger.debug("Proxy session extended")


# Global proxy manager instance
_proxy_manager = None


def get_proxy_manager() -> OnDemandProxyManager:
    """Get the global proxy manager instance"""
    global _proxy_manager
    if _proxy_manager is None:
        # Always bind to 0.0.0.0 for internal proxy server
        # PROXY_HOST is used for external access by CAPTCHA services
        proxy_host = '0.0.0.0'
        proxy_port = int(os.environ.get('SOCKS5_PROXY_PORT', '3333'))
        _proxy_manager = OnDemandProxyManager(proxy_host, proxy_port)
    return _proxy_manager


@contextmanager
def proxy_session():
    """Context manager for proxy sessions"""
    manager = get_proxy_manager()
    
    try:
        # Start proxy
        if not manager.start_proxy():
            raise RuntimeError("Failed to start proxy server")
        
        yield manager
        
    finally:
        # Extend session instead of immediately stopping
        # This allows reuse if another CAPTCHA comes quickly
        manager.extend_session()


def start_proxy_if_needed() -> bool:
    """Start proxy if CAPTCHA solving is needed"""
    manager = get_proxy_manager()
    return manager.start_proxy()


def stop_proxy_now():
    """Immediately stop the proxy (emergency shutdown)"""
    manager = get_proxy_manager()
    manager.stop_proxy()


def is_proxy_available() -> bool:
    """Check if proxy is available"""
    manager = get_proxy_manager()
    return manager.is_proxy_running()


# Cleanup on process termination
def _cleanup_handler(signum, frame):
    """Handle cleanup on process termination"""
    logger.info("Received termination signal, cleaning up proxy")
    stop_proxy_now()


# Register cleanup handlers
signal.signal(signal.SIGTERM, _cleanup_handler)
signal.signal(signal.SIGINT, _cleanup_handler)