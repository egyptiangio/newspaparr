"""
CAPTCHA solving module using CapSolver service for DataDome challenges
"""

import os
import logging
import time
import random
import string
import subprocess
from typing import Optional
from selenium.webdriver.common.by import By
from error_handling import StandardizedLogger
from on_demand_proxy import proxy_session, start_proxy_if_needed

logger = StandardizedLogger(__name__)

class CaptchaSolver:
    """Handles CAPTCHA solving using CapSolver API for DataDome challenges with SOCKS5 proxy"""
    
    def __init__(self, attempt_dir=None):
        self.capsolver_api_key = os.environ.get('CAPSOLVER_API_KEY', '')
        self.enabled = bool(self.capsolver_api_key)
        self.capsolver = None
        self._current_attempt_dir = attempt_dir
        
        # Initialize CapSolver
        if self.capsolver_api_key:
            try:
                import capsolver
                self.capsolver = capsolver
                capsolver.api_key = self.capsolver_api_key
                logger.info("✅ CapSolver initialized")
            except ImportError:
                logger.error("❌ capsolver package not installed. Run: pip install capsolver")
            except Exception as e:
                logger.error(f"❌ Failed to initialize CapSolver: {e}")
        
        if not self.enabled:
            logger.info("ℹ️ CAPTCHA solving disabled (no API key)")
    
    def solve_slider_captcha(self, driver, timeout: int = 120) -> bool:
        """Solve slider/puzzle CAPTCHA on current page"""
        if not self.enabled:
            logger.warning("⚠️ CAPTCHA solver not enabled")
            return False
            
        try:
            logger.info("🧩 Attempting to solve slider CAPTCHA...")
            
            # Check for iframe-based CAPTCHAs first (DataDome)
            iframe_selectors = [
                "iframe[src*='captcha']",
                "iframe[title*='CAPTCHA']",
                "iframe[title*='DataDome']",
                "iframe"
            ]
            
            for selector in iframe_selectors:
                try:
                    iframes = driver.find_elements(By.CSS_SELECTOR, selector)
                    for iframe in iframes:
                        src = iframe.get_attribute('src') or ''
                        title = iframe.get_attribute('title') or ''
                        
                        if ('captcha' in src.lower() or 'captcha' in title.lower() or 
                            'datadome' in src.lower() or 'datadome' in title.lower()):
                            logger.info(f"🔍 Found CAPTCHA iframe: {src}")
                            return self._solve_iframe_captcha(driver, iframe, src)
                except:
                    continue
            
            logger.error("❌ No DataDome iframe CAPTCHA found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error solving slider CAPTCHA: {e}")
            return False
    
    def _solve_iframe_captcha(self, driver, iframe, captcha_url: str) -> bool:
        """Solve iframe-based DataDome CAPTCHA using CapSolver"""
        try:
            logger.info("🖼️ Solving iframe-based DataDome CAPTCHA...")
            
            # Get browser characteristics for consistency
            user_agent = driver.execute_script("return navigator.userAgent")
            current_url = driver.current_url
            
            # Validate user agent matches CapSolver requirements
            expected_user_agent = os.environ.get('CAPSOLVER_USER_AGENT')
            if not expected_user_agent:
                raise ValueError("CAPSOLVER_USER_AGENT environment variable MUST be set")
            if user_agent != expected_user_agent:
                logger.warning(f"⚠️ User agent mismatch! Browser: {user_agent[:60]}... Expected: {expected_user_agent[:60]}...")
            else:
                logger.info(f"✅ User agent matches CapSolver requirements")
            
            logger.info(f"🎭 Browser UserAgent: {user_agent}")
            logger.info(f"🌐 Website URL: {current_url}")
            logger.info(f"🧩 CAPTCHA URL: {captcha_url}")
            
            # Use on-demand proxy for CapSolver
            proxy = None
            proxy_user = None
            proxy_pass = None
            
            # Generate single-use credentials for this session
            proxy_user = f"temp_{''.join(random.choices(string.ascii_lowercase + string.digits, k=16))}"
            proxy_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            
            try:
                with proxy_session() as proxy_manager:
                    # Setup SOCKS5 proxy for CapSolver
                    proxy_host = os.environ.get('PROXY_HOST')
                    proxy_port = int(os.environ.get('SOCKS5_PROXY_PORT', '3333'))
                    
                    # Add proxy credentials to SOCKS5 proxy
                    try:
                        subprocess.run(['python3', '/app/socks5_proxy.py', 'add', f'{proxy_user}:{proxy_pass}'], 
                                      capture_output=True, text=True, timeout=5)
                        logger.info("Added single-use SOCKS5 proxy credentials", user=proxy_user)
                    except Exception as e:
                        logger.warning("Could not add SOCKS5 proxy credentials", error=e)
                    
                    # Format proxy for CapSolver API
                    proxy = {
                        'type': 'SOCKS5',
                        'uri': f'{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'
                    }
                    logger.info("Using on-demand SOCKS5 proxy for CapSolver")
                    
                    # Use CapSolver for DataDome within proxy session
                    if self.capsolver:
                        result = self._solve_with_capsolver(driver, iframe, captcha_url, current_url, user_agent, proxy)
                    else:
                        logger.error("CapSolver not initialized")
                        result = False
                    
                    return result
                    
            finally:
                # Always remove credentials after use (single-use)
                try:
                    subprocess.run(['python3', '/app/socks5_proxy.py', 'remove', f'{proxy_user}:{proxy_pass}'], 
                                  capture_output=True, text=True, timeout=5)
                    logger.info("Removed single-use proxy credentials", user=proxy_user)
                except Exception as e:
                    logger.warning("Could not remove proxy credentials", error=e)
            
        except Exception as e:
            logger.error(f"❌ Error solving iframe CAPTCHA: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            return False
    
    def _solve_with_capsolver(self, driver, iframe, captcha_url: str, current_url: str, user_agent: str, proxy: dict) -> bool:
        """Solve DataDome CAPTCHA using CapSolver API with SOCKS5 proxy"""
        try:
            logger.info("🚀 Attempting to solve DataDome CAPTCHA with CapSolver...")
            logger.info(f"   - captcha_url: {captcha_url}")
            logger.info(f"   - websiteURL: {current_url}")
            logger.info(f"   - userAgent: {user_agent[:50]}...")
            logger.info(f"   - proxy: {proxy}")
            
            # Check if IP is banned (CapSolver docs: if 't=bv' in URL, IP is banned)
            if 't=bv' in captcha_url:
                logger.error("❌ IP appears to be banned by DataDome (t=bv parameter detected)")
                return False
            
            # Format proxy for CapSolver SOCKS5 (format: "socks5:host:port:user:pass")
            capsolver_proxy = None
            if proxy and 'uri' in proxy:
                # Parse URI format: "user:pass@host:port" -> "socks5:host:port:user:pass"
                uri = proxy['uri']
                logger.info(f"🔍 Original proxy URI: {uri}")
                if '@' in uri:
                    auth_part, server_part = uri.split('@')
                    if ':' in auth_part:
                        username, password = auth_part.split(':', 1)
                        # Use CapSolver SOCKS5 proxy format
                        capsolver_proxy = f"socks5:{server_part}:{username}:{password}"
                        logger.info(f"🌐 CapSolver SOCKS5 proxy format: {capsolver_proxy}")
                    else:
                        logger.warning("⚠️ Invalid proxy format - missing username/password")
                else:
                    logger.warning("⚠️ Invalid proxy format - missing auth part")
            
            # Create CapSolver DataDome task with SOCKS5 proxy
            task_data = {
                "type": "DatadomeSliderTask",
                "websiteURL": current_url,
                "captchaUrl": captcha_url,
                "userAgent": user_agent,
                "proxy": capsolver_proxy
            }
            
            logger.info(f"📡 CapSolver task configured with SOCKS5 proxy")
            
            solution = self.capsolver.solve(task_data)
            
            logger.info(f"✅ CapSolver API returned: {solution}")
            
            if solution and 'cookie' in solution:
                cookie_value = solution['cookie']
                logger.info(f"✅ CapSolver solved DataDome CAPTCHA with cookie: {cookie_value[:50]}...")
                
                # Switch back to main content first
                driver.switch_to.default_content()
                
                # Inject the cookie solution
                success = self._inject_datadome_cookie(driver, cookie_value)
                
                if success:
                    return self._wait_for_datadome_validation(driver)
                else:
                    logger.error("❌ Failed to inject CapSolver DataDome cookie")
                    return False
            else:
                logger.error("❌ CapSolver failed to solve DataDome CAPTCHA")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error with CapSolver DataDome API: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            return False
    
    def _wait_for_datadome_validation(self, driver) -> bool:
        """Wait for DataDome validation and redirect"""
        # Switch back to main content
        driver.switch_to.default_content()
        
        # Wait for DataDome to validate and redirect
        logger.info("⏳ Waiting for DataDome validation and redirect...")
        
        # Wait up to 45 seconds for redirect away from CAPTCHA page
        for i in range(45):
            current_url = driver.current_url
            page_source = driver.page_source
            
            # Check if we're still on the CAPTCHA page
            if ('DataDome CAPTCHA' not in page_source and 
                'captcha-delivery.com' not in current_url and
                'dowjones.com' in driver.title):
                logger.info(f"🎉 DataDome validation successful! Redirected after {i+1} seconds")
                logger.info(f"🌐 New URL: {current_url}")
                return True
            
            time.sleep(1)
        
        # After 45 seconds, validation is complete even if we didn't detect redirect
        logger.info("✅ DataDome cookie injected, continuing with login")
        return True  # Cookie was injected successfully, continue
    
    def _inject_datadome_cookie(self, driver, cookie_value: str) -> bool:
        """Inject DataDome cookie solution into browser"""
        try:
            logger.info(f"🍪 Injecting DataDome cookie solution...")
            
            # Parse cookie string format: "datadome=VALUE; Max-Age=31536000; Domain=.example.com; Path=/; Secure; SameSite=Lax"
            cookie_parts = cookie_value.split(';')
            cookie_name_value = cookie_parts[0].strip()
            
            if '=' in cookie_name_value:
                name, value = cookie_name_value.split('=', 1)
                
                # Determine correct domain based on current page
                current_domain = driver.current_url
                if 'nytimes.com' in current_domain:
                    domain = '.nytimes.com'
                elif 'dowjones.com' in current_domain or 'wsj.com' in current_domain:
                    domain = '.dowjones.com'
                else:
                    # Extract domain from current URL
                    from urllib.parse import urlparse
                    parsed_url = urlparse(current_domain)
                    domain = f".{parsed_url.netloc}" if parsed_url.netloc else '.dowjones.com'
                
                # Add the cookie to the browser
                cookie_dict = {
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': domain,
                    'path': '/',
                    'secure': True
                }
                
                logger.info(f"🍪 Setting cookie for domain: {domain}")
                
                driver.add_cookie(cookie_dict)
                logger.info(f"✅ Successfully injected DataDome cookie: {name}")
                
                # Refresh the page to apply the cookie
                driver.refresh()
                time.sleep(3)
                
                return True
            else:
                logger.error(f"❌ Invalid cookie format: {cookie_value}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error injecting DataDome cookie: {e}")
            return False