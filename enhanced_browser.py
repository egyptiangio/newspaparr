"""
Enhanced browser configuration to bypass DataDome detection
Uses advanced anti-detection techniques and proxy support
CRITICAL: User agent MUST be defined in docker-compose.yml
"""

import os
import random
import logging
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
import time

logger = logging.getLogger(__name__)


class EnhancedBrowser:
    """Enhanced browser with better anti-detection capabilities"""
    
    @classmethod
    def create_undetected_driver(cls, headless=False, use_proxy=False):
        """
        Create an undetected Chrome driver with enhanced anti-detection
        
        Args:
            headless: Whether to run in headless mode
            use_proxy: Whether to use the SOCKS5 proxy for browser traffic
        """
        logger.info("🚀 Creating enhanced undetected browser...")
        
        # MUST use environment variable - NO FALLBACKS
        user_agent = os.environ.get('CAPSOLVER_USER_AGENT')
        if not user_agent:
            raise ValueError("CAPSOLVER_USER_AGENT MUST be set in docker-compose.yml - NO EXCEPTIONS")
        
        logger.info(f"🎭 Using MANDATORY User-Agent from docker-compose: {user_agent[:60]}...")
        
        # Create undetected Chrome options
        options = uc.ChromeOptions()
        
        # Basic options
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Random window size to avoid fingerprinting
        window_sizes = [(1920, 1080), (1366, 768), (1440, 900), (1536, 864)]
        width, height = random.choice(window_sizes)
        options.add_argument(f"--window-size={width},{height}")
        
        # Additional anti-detection arguments
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=UserAgentClientHint")
        options.add_argument("--disable-web-security")
        
        # Mimic real browser behavior
        options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        options.add_argument("--force-color-profile=srgb")
        
        # Add random chrome extensions directory (empty but present)
        options.add_argument("--load-extension=/tmp/fake_extension")
        os.makedirs("/tmp/fake_extension", exist_ok=True)
        
        # Add proxy if requested
        if use_proxy:
            proxy_host = os.environ.get('PROXY_HOST', 'mzaki.mooo.com')
            proxy_port = os.environ.get('PROXY_PORT', '3333')
            logger.info(f"🔗 Configuring browser to use SOCKS5 proxy: {proxy_host}:{proxy_port}")
            options.add_argument(f"--proxy-server=socks5://{proxy_host}:{proxy_port}")
        
        # GUI mode is better for anti-detection
        if headless:
            # Use headless=new mode which is less detectable
            options.add_argument("--headless=new")
            logger.info("Running in new headless mode")
        else:
            logger.info("Running in GUI mode (better for avoiding detection)")
        
        # Create driver with undetected-chromedriver
        try:
            # Use same configuration as original working code
            driver = uc.Chrome(
                options=options,
                browser_executable_path="/usr/bin/chromium"
            )
            
            # Additional JavaScript modifications
            cls._apply_anti_detection_scripts(driver)
            
            # Random delay to appear more human
            time.sleep(random.uniform(0.5, 1.5))
            
            logger.info("✅ Enhanced undetected browser created successfully")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create undetected driver: {e}")
            raise
    
    @classmethod
    def create_standard_driver(cls, headless=False, use_proxy=False):
        """
        Create a standard Chrome driver with stealth applied
        Fallback option if undetected driver fails
        """
        logger.info("🚀 Creating enhanced standard browser...")
        
        # MUST use environment variable - NO FALLBACKS
        user_agent = os.environ.get('CAPSOLVER_USER_AGENT')
        if not user_agent:
            raise ValueError("CAPSOLVER_USER_AGENT MUST be set in docker-compose.yml - NO EXCEPTIONS")
        
        logger.info(f"🎭 Using MANDATORY User-Agent from docker-compose: {user_agent[:60]}...")
        
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Random window size
        window_sizes = [(1920, 1080), (1366, 768), (1440, 900), (1536, 864)]
        width, height = random.choice(window_sizes)
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # Anti-detection settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add proxy if requested
        if use_proxy:
            proxy_host = os.environ.get('PROXY_HOST', 'mzaki.mooo.com')
            proxy_port = os.environ.get('PROXY_PORT', '3333')
            logger.info(f"🔗 Configuring browser to use SOCKS5 proxy: {proxy_host}:{proxy_port}")
            chrome_options.add_argument(f"--proxy-server=socks5://{proxy_host}:{proxy_port}")
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Use Chromium
        chrome_options.binary_location = "/usr/bin/chromium"
        
        from selenium.webdriver.chrome.service import Service
        service = Service("/usr/bin/chromedriver")
        
        driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
        
        # Apply stealth
        stealth(driver,
            user_agent=user_agent,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32" if "Windows" in user_agent else "MacIntel",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            run_on_insecure_origins=True
        )
        
        # Additional anti-detection scripts
        cls._apply_anti_detection_scripts(driver)
        
        # Random delay
        time.sleep(random.uniform(0.5, 1.5))
        
        logger.info("✅ Enhanced standard browser created successfully")
        return driver
    
    @staticmethod
    def _apply_anti_detection_scripts(driver):
        """Apply additional anti-detection JavaScript modifications"""
        
        # Override webdriver property
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Override plugins to appear more realistic
        driver.execute_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });
        """)
        
        # Override permissions
        driver.execute_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Add random mouse movements simulation
        driver.execute_script("""
            let mouseX = Math.random() * window.innerWidth;
            let mouseY = Math.random() * window.innerHeight;
            
            document.addEventListener('mousemove', function(e) {
                mouseX = e.clientX;
                mouseY = e.clientY;
            });
            
            // Simulate random mouse movements
            setInterval(() => {
                mouseX += (Math.random() - 0.5) * 20;
                mouseY += (Math.random() - 0.5) * 20;
                mouseX = Math.max(0, Math.min(window.innerWidth, mouseX));
                mouseY = Math.max(0, Math.min(window.innerHeight, mouseY));
            }, 100);
        """)
        
        # Override chrome property
        driver.execute_script("""
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        """)
        
        # Make navigator.languages look more realistic
        driver.execute_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        # Override timezone to match user's likely location
        driver.execute_script("""
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() {
                    return {
                        ...Intl.DateTimeFormat.prototype.resolvedOptions.call(this),
                        timeZone: 'America/New_York'
                    };
                }
            });
        """)