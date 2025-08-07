"""
Library adapter system for NYT auto-renewal
Provides library-agnostic interface for different authentication systems
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import logging
import time
from selenium_stealth import stealth
import os
from pyvirtualdisplay import Display

logger = logging.getLogger(__name__)

class LibraryAdapter(ABC):
    """Abstract base class for library adapters"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.driver = None
        self.wait = None
    
    @abstractmethod
    def get_library_info(self) -> Dict:
        """Get library information and configuration"""
        pass
    
    @abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the library system"""
        pass
    
    @abstractmethod
    def access_nyt(self) -> bool:
        """Access NYT through library portal"""
        pass
    
    @abstractmethod
    def get_nyt_activation_url(self) -> Optional[str]:
        """Get the NYT activation URL if needed"""
        pass
    
    def access_newspaper(self, newspaper_type: str) -> bool:
        """Access newspaper through library portal"""
        if newspaper_type == 'wsj':
            return self.access_wsj()
        else:
            return self.access_nyt()
    
    def access_wsj(self) -> bool:
        """Access WSJ through library portal"""
        try:
            current_url = self.driver.current_url
            logger.info(f"WSJ access check - Current URL: {current_url}")
            
            # If already on WSJ site, we're done
            if "wsj.com" in current_url and "partner.wsj.com" not in current_url:
                logger.info("Already on WSJ main site")
                return True
            
            # If on the library's WSJ page (e.g., loggedin/wsj.html), click "Visit the Wall Street Journal" link
            if "wsj.html" in current_url and "idm.oclc.org" in current_url:
                logger.info("On library WSJ page, looking for 'Visit the Wall Street Journal' link")
                
                visit_wsj_selectors = [
                    "//a[contains(text(), 'Visit the Wall Street Journal')]",
                    "//a[contains(text(), 'Visit The Wall Street Journal')]",
                    "//a[contains(text(), 'Wall Street Journal')]",
                    "//a[contains(@href, 'wsj.com')]",
                    "a[href*='wsj.com']"
                ]
                
                for selector in visit_wsj_selectors:
                    try:
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if elements and elements[0].is_displayed():
                            logger.info(f"Found WSJ link with selector: {selector}")
                            link_href = elements[0].get_attribute('href')
                            logger.info(f"WSJ link href: {link_href}")
                            
                            try:
                                # Try clicking with timeout protection
                                elements[0].click()
                                logger.info(f"Clicked WSJ link, waiting for navigation...")
                                
                                # Wait for navigation with explicit timeout
                                wait = WebDriverWait(self.driver, 10)
                                wait.until(lambda driver: driver.current_url != current_url)
                                
                                new_url = self.driver.current_url
                                logger.info(f"After clicking WSJ link, URL: {new_url}")
                                
                                # Check if we reached WSJ or partner page
                                if "wsj.com" in new_url or "partner.wsj.com" in new_url:
                                    return True
                                    
                            except TimeoutException:
                                logger.error(f"Timeout waiting for navigation after WSJ link click")
                                # Try direct navigation as fallback
                                if link_href:
                                    logger.info(f"Attempting direct navigation to: {link_href}")
                                    self.driver.get(link_href)
                                    time.sleep(2)
                                    if "wsj.com" in self.driver.current_url:
                                        return True
                            except Exception as e:
                                logger.error(f"Error clicking WSJ link: {str(e)}")
                                
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {str(e)}")
                        continue
                
                logger.warning("Could not find 'Visit the Wall Street Journal' link")
            
            # Check if we ended up on WSJ or partner site
            final_url = self.driver.current_url
            return "wsj.com" in final_url or "partner.wsj.com" in final_url
            
        except Exception as e:
            logger.error(f"Error accessing WSJ: {str(e)}")
            return False
    
    def get_newspaper_activation_url(self, newspaper_type: str) -> Optional[str]:
        """Get the newspaper activation URL if needed"""
        if newspaper_type == 'wsj':
            return self.get_wsj_activation_url()
        else:
            return self.get_nyt_activation_url()
    
    def get_wsj_activation_url(self) -> Optional[str]:
        """Get WSJ activation URL"""
        current_url = self.driver.current_url
        if "wsj.html" in current_url or "wsj.com" in current_url:
            return current_url
        return None
    
    def get_newspaper_url(self, newspaper_type: str) -> str:
        """Get newspaper-specific URL from library configuration"""
        # URLs are now stored directly in the database
        if newspaper_type == 'nyt':
            url = self.config.get('nyt_url', '')
        elif newspaper_type == 'wsj':
            url = self.config.get('wsj_url', '')
        else:
            url = ''
        
        if url:
            logger.info(f"Using stored URL for {newspaper_type}: {url}")
        else:
            logger.error(f"No URL configured for {newspaper_type}")
            
        return url
    
    def setup_driver(self, headless: bool = True, newspaper_type: str = 'nyt') -> webdriver.Chrome:
        """Setup WebDriver with undetected-chromedriver for all newspapers"""
        
        # Use undetected-chromedriver for all newspapers (better bot evasion)
        logger.info(f"Setting up undetected-chromedriver for {newspaper_type.upper()}")
        
        # Check if we're running on a server (no display)
        display = None
        if os.environ.get('DISPLAY') is None and not headless:
            logger.info("No display detected, starting virtual display for GUI mode")
            display = Display(visible=0, size=(1920, 1080))
            display.start()
            self.virtual_display = display  # Store reference for cleanup
            logger.info(f"Virtual display started: {os.environ.get('DISPLAY')}")
        
        options = uc.ChromeOptions()
        
        # Prefer GUI mode (non-headless) for better anti-detection
        # Only use headless if explicitly requested AND we're not using virtual display
        if headless and display is None:
            options.add_argument("--headless")
            logger.info("Running in headless mode (not recommended for avoiding detection)")
        else:
            logger.info("Running in GUI mode (better for avoiding detection)")
        
        # Use environment variable User-Agent for system-wide consistency
        user_agent = os.environ.get('CAPSOLVER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
        options.add_argument(f"user-agent={user_agent}")
        logger.info(f"📱 Using CapSolver-compatible static User-Agent: {user_agent[:60]}...")
        
        # Basic options for Docker/server environment
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Browser runs locally (home IP) - no proxy needed
        # Only CapSolver will use the proxy to match the same IP
        logger.info("🏠 Browser using direct connection (home IP)")
        
        # Incognito-like behavior: clear state for each renewal
        options.add_argument("--incognito")
        options.add_argument("--disable-cache")
        options.add_argument("--disable-application-cache")
        options.add_argument("--disable-offline-load-stale-cache")
        options.add_argument("--disk-cache-size=0")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--safebrowsing-disable-auto-update")
        options.add_argument("--disable-ipc-flooding-protection")
        logger.info("🕵️  Configured Chrome for maximum privacy/incognito behavior")
        
        # Let undetected-chromedriver handle driver and browser detection automatically
        try:
            # Use Chromium with undetected-chromedriver (supports ARM64)
            self.driver = uc.Chrome(options=options, browser_executable_path="/usr/bin/chromium")
            logger.info("✅ Using undetected Chromium with auto-managed ChromeDriver (version matched)")
            logger.info(f"Successfully created undetected Chromium driver for {newspaper_type.upper()}")
            
            # Apply selenium-stealth for additional anti-detection
            logger.info("Applying selenium-stealth anti-detection measures...")
            
            # Get the user agent that was set (it's stored in options)
            user_agent_for_stealth = user_agent if 'user_agent' in locals() else os.environ.get('CAPSOLVER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
            
            # Extract platform from user agent for consistency
            platform = "Win32"
                
            stealth(self.driver,
                user_agent=user_agent_for_stealth,  # Use the same user agent
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform=platform,
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            logger.info("✅ Selenium-stealth anti-detection applied")
            
        except Exception as e:
            logger.warning(f"Failed to create undetected driver: {str(e)}, falling back to regular driver")
            # Fallback to regular driver if undetected fails
            return self._setup_regular_driver(headless)
        
        self.wait = WebDriverWait(self.driver, 30)
        
        logger.info("✅ Browser ready for WSJ login (direct connection)")
        
        return self.driver
    
    def _setup_regular_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Setup regular ChromeDriver (for WSJ or fallback)"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Use same environment variable User-Agent for consistency
        user_agent = os.environ.get('CAPSOLVER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
        
        chrome_options.add_argument(f"--user-agent={user_agent}")
        logger.info(f"🎭 Fallback driver using User-Agent: {user_agent[:60]}...")
        
        # Anti-bot detection settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # Use Chromium
        chrome_options.binary_location = "/usr/bin/chromium"
        
        from selenium.webdriver.chrome.service import Service
        
        # Use system chromium-driver (Debian/Ubuntu path)
        service = Service("/usr/bin/chromedriver")
        self.driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
        
        # Hide automation indicators
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        
        # Apply selenium-stealth for additional anti-detection
        logger.info("Applying selenium-stealth to regular driver...")
        
        # Extract platform from user agent
        platform = "Win32"
            
        stealth(self.driver,
            user_agent=user_agent,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform=platform,
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        logger.info("✅ Selenium-stealth applied to regular driver")
        
        return self.driver
    
    def cleanup_driver(self):
        """Clean up WebDriver resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
        
        # Clean up virtual display if we started one
        if hasattr(self, 'virtual_display') and self.virtual_display:
            logger.info("Stopping virtual display")
            self.virtual_display.stop()
            self.virtual_display = None

class GenericOCLCAdapter(LibraryAdapter):
    """Generic adapter for OCLC WorldCat libraries"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.library_domain = config.get('library_domain')
        self.library_name = config.get('library_name', 'OCLC Library')
    
    def get_library_info(self) -> Dict:
        return {
            "name": self.library_name,
            "type": "OCLC WorldCat",
            "base_url": f"https://{self.library_domain}",
            "renewal_hours": self.config.get('renewal_hours', 72),
            "supports_multiple_accounts": True
        }
    
    def authenticate(self, username: str, password: str) -> bool:
        """Generic OCLC authentication"""
        try:
            # Get newspaper type from config
            newspaper_type = self.config.get('newspaper_type', 'nyt')
            
            # Use dynamic URL generation
            login_url = self.get_newspaper_url(newspaper_type)
            
            if not login_url:
                logger.error("No login URL could be generated for library")
                return False
            
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            logger.info(f"Navigating to {self.library_name} login for {newspaper_name}")
            self.driver.get(login_url)
            
            possible_username_fields = ["user", "username", "barcode", "cardnumber"]
            possible_password_fields = ["pass", "password", "pin"]
            
            username_field = None
            for field_name in possible_username_fields:
                try:
                    username_field = self.driver.find_element(By.NAME, field_name)
                    break
                except:
                    continue
            
            if not username_field:
                logger.error("Could not find username field")
                return False
            
            username_field.send_keys(username)
            
            password_field = None
            for field_name in possible_password_fields:
                try:
                    password_field = self.driver.find_element(By.NAME, field_name)
                    break
                except:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                return False
                
            password_field.send_keys(password)
            
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                ".submit-button",
                "#submit"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    submit_button.click()
                    break
                except:
                    continue
            
            time.sleep(5)
            
            current_url = self.driver.current_url
            
            # Check for newspaper-specific success indicators
            newspaper_type = getattr(self, 'newspaper_type', self.config.get('newspaper_type', 'nyt'))
            success_domains = {
                'nyt': ['nytimes.com'],
                'wsj': ['wsj.com', 'wsj.html']
            }
            
            domains = success_domains.get(newspaper_type, ['nytimes.com'])
            success = any(domain in current_url for domain in domains)
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            
            if success:
                logger.info(f"{self.library_name} authentication successful for {newspaper_name}")
                return True
            else:
                logger.error(f"{self.library_name} authentication failed for {newspaper_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error during {self.library_name} authentication: {str(e)}")
            return False
    
    def access_nyt(self) -> bool:
        """Access NYT through generic OCLC portal"""
        current_url = self.driver.current_url
        return ("nytimes.com" in current_url or 
                "nyt.html" in current_url or
                ("idm.oclc.org" in current_url and "nyt" in current_url))
    
    def get_nyt_activation_url(self) -> Optional[str]:
        """Get NYT activation URL"""
        current_url = self.driver.current_url
        if "corpgrouppass" in current_url or "activate" in current_url:
            return current_url
        return None

class CustomLibraryAdapter(LibraryAdapter):
    """Custom adapter for user-configured libraries"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.library_domain = config.get('library_domain')
        self.library_name = config.get('library_name', 'Custom Library')
        self.login_url = config.get('login_url')
    
    def get_library_info(self) -> Dict:
        return {
            "name": self.library_name,
            "type": "Custom",
            "base_url": self.login_url or f"https://{self.library_domain}" if self.library_domain else None,
            "renewal_hours": self.config.get('renewal_hours', 72),
            "supports_multiple_accounts": True
        }
    
    def authenticate(self, username: str, password: str) -> bool:
        """Custom library authentication with dynamic URL generation"""
        try:
            # Get newspaper type from config
            newspaper_type = self.config.get('newspaper_type', 'nyt')
            
            # Use dynamic URL generation
            login_url = self.get_newspaper_url(newspaper_type)
            
            if not login_url:
                logger.error("No login URL could be generated for custom library")
                return False
            
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            logger.info(f"Navigating to {self.library_name} login for {newspaper_name}")
            self.driver.get(login_url)
            
            # Try common username field names
            possible_username_fields = ["user", "username", "barcode", "cardnumber", "email"]
            possible_password_fields = ["pass", "password", "pin"]
            
            username_field = None
            for field_name in possible_username_fields:
                try:
                    username_field = self.driver.find_element(By.NAME, field_name)
                    break
                except:
                    continue
            
            if not username_field:
                logger.error("Could not find username field")
                return False
            
            username_field.send_keys(username)
            
            password_field = None
            for field_name in possible_password_fields:
                try:
                    password_field = self.driver.find_element(By.NAME, field_name)
                    break
                except:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                return False
                
            password_field.send_keys(password)
            
            # Try to find and click submit button
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                ".submit-button",
                "#submit",
                "button:contains('Login')",
                "button:contains('Sign in')"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    submit_button.click()
                    break
                except:
                    continue
            
            time.sleep(5)
            
            current_url = self.driver.current_url
            
            # Check for newspaper-specific success indicators
            newspaper_type = getattr(self, 'newspaper_type', self.config.get('newspaper_type', 'nyt'))
            success_domains = {
                'nyt': ['nytimes.com'],
                'wsj': ['wsj.com', 'wsj.html']
            }
            
            domains = success_domains.get(newspaper_type, ['nytimes.com'])
            success = any(domain in current_url for domain in domains)
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            
            if success:
                logger.info(f"{self.library_name} authentication successful for {newspaper_name}")
                return True
            else:
                logger.error(f"{self.library_name} authentication failed for {newspaper_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error during {self.library_name} authentication: {str(e)}")
            return False
    
    def access_nyt(self) -> bool:
        """Access NYT through custom library portal"""
        current_url = self.driver.current_url
        return ("nytimes.com" in current_url or 
                "nyt.html" in current_url or
                ("idm.oclc.org" in current_url and "nyt" in current_url))
    
    def get_nyt_activation_url(self) -> Optional[str]:
        """Get NYT activation URL"""
        current_url = self.driver.current_url
        if "corpgrouppass" in current_url or "activate" in current_url:
            return current_url
        return None

class LibraryAdapterFactory:
    """Factory for creating library adapters"""
    
    @staticmethod
    def create_adapter(library_type: str, config: Dict) -> LibraryAdapter:
        """Create appropriate library adapter"""
        adapters = {
            "generic_oclc": GenericOCLCAdapter,
            "custom": CustomLibraryAdapter,
        }
        
        if library_type not in adapters:
            raise ValueError(f"Unknown library type: {library_type}")
        
        return adapters[library_type](config)
