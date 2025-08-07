"""
Clean Renewal Engine for Newspaparr
Handles NYT and WSJ renewals with priority-based login and CAPTCHA solving
"""

import os
import time
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from library_adapters import LibraryAdapterFactory
from captcha_solver import CaptchaSolver
from error_handling import StandardizedLogger
from browser_config import CAPSOLVER_USER_AGENT
from state_detector import StateDetector, check_current_state

logger = StandardizedLogger(__name__)

class RenewalEngine:
    """Clean renewal engine with priority-based login and CAPTCHA solving"""
    
    def __init__(self, headless: bool = True, timeout: int = 60):
        self.headless = headless
        self.timeout = timeout
        self.renewal_speed = os.environ.get('RENEWAL_SPEED', 'normal')
        
        # Debug mode for full screenshot capture
        self.debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
        
        # Screenshot retention limit (number of attempts to keep)
        self.screenshot_retention = int(os.environ.get('SCREENSHOT_RETENTION', '10'))
        
        # Screenshot directory with attempt-specific folders
        self.screenshot_base_dir = "/app/data/debug/screenshots"
        os.makedirs(self.screenshot_base_dir, exist_ok=True)
        
        # Current attempt directory (will be set per renewal)
        self.current_attempt_dir = None
        
        # Validate CapSolver user agent consistency
        logger.info(f"🎭 Using CapSolver-compatible User-Agent: {CAPSOLVER_USER_AGENT[:60]}...")
        
        logger.info(f"🚀 Clean RenewalEngine initialized (headless={headless}, timeout={timeout}s)")
    
    def renew_account(self, account) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """Main entry point for account renewal"""
        start_time = time.time()
        adapter = None
        success = False
        result_url = None
        expiration_datetime = None
        final_state = "UNKNOWN"
        state_message = None
        
        # Create attempt-specific directory for this renewal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        account_name = getattr(account, 'name', 'unknown').replace(' ', '_')
        self.current_attempt_dir = os.path.join(self.screenshot_base_dir, f"{account_name}_{timestamp}")
        os.makedirs(self.current_attempt_dir, exist_ok=True)
        
        # Clean up old attempts if retention limit exceeded
        self._cleanup_old_attempts(account_name)
        
        try:
            # Get library name for display
            from app import LibraryConfig
            library_config = LibraryConfig.query.filter_by(type=account.library_type).first()
            library_name = library_config.name if library_config else account.library_type
            
            # Create the formatted block
            start_block = f"""
============================================================
STARTING RENEWAL for {account.name} ({account.newspaper_type.upper()})
============================================================
Library: {library_name}
Newspaper: {account.newspaper_type.upper()}
Headless: {self.headless}
Timeout: {self.timeout}s
============================================================
"""
            # Print to terminal and log
            print(start_block)
            for line in start_block.strip().split('\n'):
                logger.info(line)
            
            logger.info(f"🔄 Starting renewal for account: {account.name} ({account.newspaper_type.upper()})")
            
            # Reset state detection counters for new renewal
            StateDetector.reset_all_counters()
            
            # Store newspaper type for state detection
            self.newspaper_type = getattr(account, 'newspaper_type', 'nyt')
            
            # Step 1: Create library adapter
            adapter = self._create_adapter(account)
            if not adapter:
                raise Exception("Failed to create library adapter")
            
            # Check if this is a gift code URL (bypasses library auth)
            newspaper_type = getattr(account, 'newspaper_type', 'nyt')
            newspaper_url = adapter.config.get(f'{newspaper_type}_url', '')
            is_gift_code_url = self._is_gift_code_url(newspaper_url)
            
            if is_gift_code_url:
                logger.info(f"🎁 Detected gift code URL for {account.name} ({account.newspaper_type.upper()}), skipping library authentication")
                # Navigate directly to gift code URL
                if not self._handle_gift_code_redemption(adapter, account, newspaper_url):
                    raise Exception("Gift code redemption failed")
            else:
                # Standard flow - authenticate with library first
                # Step 2: Authenticate with library (prescriptive, predictable)
                if not self._authenticate_with_library(adapter, account):
                    raise Exception("Library authentication failed")
                
                # Skip prescriptive portal access - let priority-based system handle it
                # This allows adaptation to different library implementations
                # Using priority system for login
            
            # Step 4: Handle newspaper login (priority-based system)
            newspaper_type = getattr(account, 'newspaper_type', 'nyt')
            if not self._handle_newspaper_login(adapter, account, newspaper_type):
                raise Exception("Newspaper login failed")
            
            # Step 5: Verify renewal success and extract expiration
            success, result_url, expiration_datetime, final_state, state_message = self._verify_renewal(adapter, account)
            
            # Build appropriate message based on state
            if final_state == "SUCCESS":
                message = state_message or f"✅ Renewal complete - Access verified"
            elif final_state == "SUCCESS_WITH_WARNING":
                message = f"⚠️ {state_message}"
            elif final_state == "FAILURE":
                message = f"❌ {state_message}"
            else:
                message = f"⚠️ Renewal may need attention - Process completed but status unclear"
            
        except Exception as e:
            logger.error(f"💥 Renewal failed for {account.name} ({account.newspaper_type.upper()}): {str(e)}")
            final_state = "FAILURE"
            state_message = str(e)
            message = f"❌ {str(e)}"
            success = False
            
        finally:
            # Always save final screenshot and clean up
            if adapter and adapter.driver:
                self._save_final_screenshot(account, adapter.driver)
                adapter.cleanup_driver()
            
            # Log the attempt
            duration = int(time.time() - start_time)
            # Set is_warning flag for SUCCESS_WITH_WARNING state
            is_warning = (final_state == "SUCCESS_WITH_WARNING")
            self._log_renewal_attempt(account, success, message, duration, 
                                    is_warning=is_warning)
            
            # Print final summary AFTER all actions are complete
            result_lines = [
                "",
                "="*60,
                f"RENEWAL RESULT for {account.name} ({account.newspaper_type.upper()})",
                "="*60,
                f"State: {final_state}"
            ]
            if state_message:
                result_lines.append(f"Details: {state_message}")
            if expiration_datetime:
                result_lines.append(f"Expires: {expiration_datetime}")
            result_lines.append("="*60)
            result_lines.append("")
            
            # Log the final summary
            for line in result_lines:
                if line:  # Skip empty lines in logs
                    logger.info(line)
        
        return success, result_url, expiration_datetime
    
    def _create_adapter(self, account):
        """Create library adapter for the account"""
        try:
            from app import LibraryConfig
            
            # Get library configuration from database
            library_config = LibraryConfig.query.filter_by(type=account.library_type).first()
            if not library_config:
                logger.error(f"No library configuration found for type: {account.library_type}")
                return None
            
            # Parse custom config if available
            custom_config = {}
            if library_config.custom_config:
                try:
                    custom_config = json.loads(library_config.custom_config)
                except:
                    logger.warning(f"Failed to parse custom config for {library_config.name}")
            
            # Get newspaper type for URL generation
            newspaper_type = getattr(account, 'newspaper_type', 'nyt')
            
            # Create adapter configuration
            adapter_config = {
                'library_type': account.library_type,
                'library_domain': custom_config.get('base_url', '').replace('https://', '').replace('http://', ''),
                'library_name': library_config.name,
                'base_url': custom_config.get('base_url', ''),
                'custom_config': custom_config,
                'newspaper_type': newspaper_type,
                'renewal_hours': library_config.default_renewal_hours,
                'nyt_url': library_config.nyt_url,
                'wsj_url': library_config.wsj_url
            }
            
            # Create adapter using factory
            adapter = LibraryAdapterFactory.create_adapter(account.library_type, adapter_config)
            
            # Setup driver
            adapter.setup_driver(headless=self.headless, newspaper_type=newspaper_type)
            
            logger.info(f"✅ Created adapter for {library_config.name} ({newspaper_type.upper()})")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create adapter: {str(e)}")
            return None
    
    def _authenticate_with_library(self, adapter, account) -> bool:
        """Authenticate with library (prescriptive, predictable step)"""
        try:
            logger.info(f"🔐 Authenticating with library for {account.name} ({account.newspaper_type.upper()})")
            
            # Save initial screenshot
            self._save_debug_screenshot(account, adapter.driver, "library_auth_start")
            
            # Use library adapter's authentication method
            success = adapter.authenticate(account.library_username, account.library_password)
            
            if success:
                logger.info(f"✅ Library authentication successful for {account.name} ({account.newspaper_type.upper()})")
                self._save_debug_screenshot(account, adapter.driver, "library_auth_success")
            else:
                logger.error(f"❌ Library authentication failed for {account.name} ({account.newspaper_type.upper()})")
                self._save_debug_screenshot(account, adapter.driver, "library_auth_failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Library authentication error for {account.name} ({account.newspaper_type.upper()}): {str(e)}")
            if adapter and adapter.driver:
                self._save_debug_screenshot(account, adapter.driver, "library_auth_error")
            return False
    
    def _access_newspaper_portal(self, adapter, account) -> bool:
        """Access newspaper portal through library"""
        try:
            newspaper_type = getattr(account, 'newspaper_type', 'nyt')
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            
            logger.info(f"🗞️ Accessing {newspaper_name} portal for {account.name} ({account.newspaper_type.upper()})")
            
            # Save screenshot before accessing portal
            self._save_debug_screenshot(account, adapter.driver, f"{newspaper_type}_portal_before")
            
            # Use library adapter to access newspaper
            success = adapter.access_newspaper(newspaper_type)
            
            if success:
                logger.info(f"✅ Successfully accessed {newspaper_name} portal for {account.name} ({account.newspaper_type.upper()})")
                self._save_debug_screenshot(account, adapter.driver, f"{newspaper_type}_portal_success")
            else:
                logger.error(f"❌ Failed to access {newspaper_name} portal for {account.name} ({account.newspaper_type.upper()})")
                self._save_debug_screenshot(account, adapter.driver, f"{newspaper_type}_portal_failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Portal access error for {account.name} ({account.newspaper_type.upper()}): {str(e)}")
            if adapter and adapter.driver:
                self._save_debug_screenshot(account, adapter.driver, f"{newspaper_type}_portal_error")
            return False
    
    def _handle_newspaper_login(self, adapter, account, newspaper_type: str) -> bool:
        """Handle newspaper login using priority-based system"""
        try:
            driver = adapter.driver
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            
            logger.info(f"🎯 Starting priority-based {newspaper_name} login for {account.name} ({account.newspaper_type.upper()})")
            
            # Get credentials
            # Get credentials from generic columns
            username = getattr(account, 'username', '') or getattr(account, 'newspaper_username', '')
            password = getattr(account, 'password', '') or getattr(account, 'newspaper_password', '')
            
            if not username or not password:
                logger.error(f"Missing credentials for {account.name} ({account.newspaper_type.upper()})")
                return False
            
            # Save initial state
            self._save_debug_screenshot(account, driver, f"{newspaper_type}_login_start")
            
            # Priority-based login system - continue until success or definitive failure
            max_attempts = 10  # Increased for multi-step login flows
            login_successful = False
            
            for attempt in range(max_attempts):
                logger.info(f"🔄 Login attempt {attempt + 1}/{max_attempts}")
                
                # Check if we're on a library portal page that needs navigation
                current_url = driver.current_url
                # Check if we're on library page but not yet on actual newspaper site
                on_library_page = "idm.oclc.org" in current_url
                on_newspaper_site = ("nytimes.com" in current_url if newspaper_type == 'nyt' else "wsj.com" in current_url)
                
                if on_library_page and not on_newspaper_site:
                    logger.info(f"🔗 On library portal page ({current_url}), looking for {newspaper_name} access link")
                    if self._click_newspaper_access_link(driver, newspaper_type):
                        logger.info(f"✅ Clicked {newspaper_name} access link")
                        self._human_delay('medium')
                        continue
                
                # Priority 0: Check for "Sign In" link on processing/loading pages
                if self._click_sign_in_link_if_present(driver):
                    logger.info("📝 Clicked Sign In link on processing page")
                    self._human_delay('medium')
                    self._save_debug_screenshot(account, driver, f"{newspaper_type}_after_signin_link_{attempt + 1}")
                
                # Check for CAPTCHA first
                if self._handle_captcha_if_present(driver, f"{newspaper_type}_login_attempt_{attempt + 1}"):
                    self._save_debug_screenshot(account, driver, f"{newspaper_type}_after_captcha_{attempt + 1}")
                    # After CAPTCHA solving, page may have changed - give it time to update
                    logger.info("🔄 CAPTCHA solved - waiting for page to update and checking for new login forms")
                    self._human_delay('long')
                    # Continue to form detection - don't skip to next iteration
                
                # Check if we're already logged in (success state)
                if self._check_login_success_state(driver, newspaper_type):
                    logger.info("✅ Login success state detected - stopping priority-based login")
                    login_successful = True
                    break
                
                # Check if we're in a failure state
                if self._check_login_failure_state(driver, newspaper_type):
                    logger.error("❌ Login failure state detected - stopping attempts")
                    break
                
                form_submitted = False
                
                # Priority 1: Try to fill both username and password if both fields available
                if self._try_combined_login(driver, username, password, newspaper_type):
                    logger.info("✅ Combined username+password form submitted")
                    form_submitted = True
                
                # Priority 2: Try username-only flow
                elif self._try_username_only_flow(driver, username, newspaper_type):
                    logger.info("✅ Username-only form submitted, checking for password field")
                    form_submitted = True
                    # After username, look for password field on same or next page
                    self._human_delay('medium')
                    if self._try_password_only_flow(driver, password, newspaper_type):
                        logger.info("✅ Password form submitted after username")
                
                # Priority 3: Try password-only flow
                elif self._try_password_only_flow(driver, password, newspaper_type):
                    logger.info("✅ Password-only form submitted")
                    form_submitted = True
                
                # If we submitted a form, wait and check the result
                if form_submitted:
                    self._human_delay('long')  # Wait for navigation/processing
                    
                    # Check for CAPTCHA after form submission
                    if self._handle_captcha_if_present(driver, f"{newspaper_type}_post_submit_captcha_{attempt + 1}"):
                        self._save_debug_screenshot(account, driver, f"{newspaper_type}_post_captcha_{attempt + 1}")
                        self._human_delay('medium')
                    
                    # Check if this submission succeeded
                    if self._check_login_success_state(driver, newspaper_type):
                        logger.info("✅ Login success state reached after form submission")
                        login_successful = True
                        break
                    
                    # If still on login page, continue the loop
                    current_url = driver.current_url.lower()
                    if any(indicator in current_url for indicator in ['login', 'signin', 'auth', 'sso']):
                        logger.info(f"🔄 Still on login page ({current_url[:50]}...), continuing priority-based login")
                    else:
                        # Unknown page - let verification logic handle it
                        logger.info(f"🤔 Reached unknown page ({current_url[:50]}...), letting verification handle it")
                        break
                else:
                    # No forms found to submit
                    logger.info("⚠️ No login forms found on current page")
                    self._human_delay('medium')
                
                # Save attempt screenshot
                self._save_debug_screenshot(account, driver, f"{newspaper_type}_login_attempt_{attempt + 1}_end")
            
            # Final state check
            self._human_delay('medium')
            self._save_debug_screenshot(account, driver, f"{newspaper_type}_login_final")
            
            logger.info(f"✅ Priority-based {newspaper_name} login completed for {account.name} ({account.newspaper_type.upper()})")
            return True
            
        except Exception as e:
            logger.error(f"Newspaper login error for {account.name} ({account.newspaper_type.upper()}): {str(e)}")
            if adapter and adapter.driver:
                self._save_debug_screenshot(account, adapter.driver, f"{newspaper_type}_login_error")
            return False
    
    def _try_combined_login(self, driver, username: str, password: str, newspaper_type: str) -> bool:
        """Try to fill both username and password if both fields are available"""
        try:
            # Look for username/email fields
            username_selectors = [
                "input[type='email']",
                "input[name='username']", 
                "input[name='email']",
                "input[id='email']",
                "input[id='username']",
                "input[name='emailOrUsername']",  # WSJ specific
                "input[id='emailOrUsername']",    # WSJ specific
                "#email-input",
                "#username-input",
                "[data-testid='email']",
                "[data-testid='username']"
            ]
            
            # Look for password fields  
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[id='password']",
                "#password-input",
                "[data-testid='password']"
            ]
            
            username_field = None
            password_field = None
            
            # Find username field
            for selector in username_selectors:
                try:
                    field = driver.find_element(By.CSS_SELECTOR, selector)
                    if field and field.is_displayed():
                        username_field = field
                        logger.info(f"Found username field: {selector}")
                        break
                except:
                    continue
            
            # Find password field
            for selector in password_selectors:
                try:
                    field = driver.find_element(By.CSS_SELECTOR, selector)
                    # Check if field is displayed AND not readonly (NYT has hidden readonly password field)
                    if field and field.is_displayed() and not field.get_attribute('readonly'):
                        password_field = field
                        logger.info(f"Found password field: {selector}")
                        break
                except:
                    continue
            
            # If both fields available, fill them
            if username_field and password_field:
                logger.info("✅ Both username and password fields available - filling both")
                
                # Clear and fill username
                username_field.clear()
                self._human_type(username_field, username)
                self._human_delay('small')
                
                # Clear and fill password
                password_field.clear()
                self._human_type(password_field, password)
                self._human_delay('small')
                
                # Look for submit button
                if self._click_submit_button(driver):
                    self._human_delay('medium')
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Combined login attempt failed: {str(e)}")
            return False
    
    def _try_username_only_flow(self, driver, username: str, newspaper_type: str) -> bool:
        """Try username-only flow with continue button"""
        try:
            # Look for username/email fields
            username_selectors = [
                "input[type='email']",
                "input[name='username']",
                "input[name='email']", 
                "input[id='email']",
                "input[id='username']",
                "input[name='emailOrUsername']",  # WSJ specific
                "input[id='emailOrUsername']"      # WSJ specific
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    field = driver.find_element(By.CSS_SELECTOR, selector)
                    if field and field.is_displayed():
                        username_field = field
                        logger.info(f"Found username field for username-only flow: {selector}")
                        break
                except:
                    continue
            
            if username_field:
                # Check if field already has our username value to avoid re-typing
                current_value = username_field.get_attribute('value') or ''
                if current_value.strip() == username.strip():
                    logger.debug("Username field already contains correct value, skipping re-type")
                else:
                    # Clear and fill username
                    username_field.clear()
                    self._human_delay('small')  # Small delay after clear
                    self._human_type(username_field, username)
                    self._human_delay('small')
                
                # Look for continue/next button (not submit)
                continue_selectors = [
                    "button:contains('Continue')",
                    "button:contains('Next')", 
                    "input[value*='Continue']",
                    "input[value*='Next']",
                    "[data-testid*='continue']",
                    "[data-testid*='next']"
                ]
                
                for selector in continue_selectors:
                    try:
                        if "contains" in selector:
                            # XPath for text content
                            text = selector.split("'")[1]
                            button = driver.find_element(By.XPATH, f"//button[contains(text(),'{text}')]")
                        else:
                            button = driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if button and button.is_displayed() and button.is_enabled():
                            logger.info(f"Clicking continue button: {selector}")
                            button.click()
                            self._human_delay('medium')
                            return True
                    except:
                        continue
                        
                # If no continue button, try submit
                if self._click_submit_button(driver):
                    self._human_delay('medium')
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Username-only flow failed: {str(e)}")
            return False
    
    def _try_password_only_flow(self, driver, password: str, newspaper_type: str) -> bool:
        """Try password-only flow"""
        try:
            # Look for password fields
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[id='password']",
                "#password-input",
                "[data-testid='password']"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    field = driver.find_element(By.CSS_SELECTOR, selector)
                    # Check if field is displayed AND not readonly (NYT has hidden readonly password field)
                    if field and field.is_displayed() and not field.get_attribute('readonly'):
                        password_field = field
                        logger.info(f"Found password field: {selector}")
                        break
                except:
                    continue
            
            if password_field:
                # Fill password
                password_field.clear()
                self._human_type(password_field, password)
                self._human_delay('small')
                
                # Submit the form
                if self._click_submit_button(driver):
                    self._human_delay('medium')
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Password-only flow failed: {str(e)}")
            return False
    
    def _click_sign_in_link_if_present(self, driver) -> bool:
        """Click Sign In link if present on loading/processing pages"""
        try:
            # Look for various sign-in link patterns
            sign_in_selectors = [
                "a:contains('Sign In')",
                "a:contains('sign in')",
                "a:contains('SIGN IN')",
                "a:contains('Log In')",
                "a:contains('Log in')",  # NYT specific
                "a:contains('Login')",
                "[href*='signin']",
                "[href*='login']",
                "[href*='authenticate']",
                ".sign-in-link",
                ".signin-link",
                ".login-link"
            ]
            
            for selector in sign_in_selectors:
                try:
                    if "contains" in selector:
                        # XPath for text content
                        text = selector.split("'")[1]
                        elements = driver.find_elements(By.XPATH, f"//a[contains(text(),'{text}')]")
                    else:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element and element.is_displayed() and element.is_enabled():
                            logger.info(f"Found sign-in link: {selector}")
                            element.click()
                            return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            logger.debug(f"Error looking for sign-in link: {str(e)}")
            return False
    
    def _check_login_success_state(self, driver, newspaper_type: str) -> bool:
        """Check if we've reached a login success state using text-based detection"""
        try:
            state, message = check_current_state(driver, newspaper_type, "login_check")
            
            if state in ["SUCCESS", "SUCCESS_WITH_WARNING"]:
                logger.info(f"✅ {message}")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking login success state: {str(e)}")
            return False
    
    def _check_login_failure_state(self, driver, newspaper_type: str) -> bool:
        """Check if we've reached a definitive login failure state"""
        try:
            state, message = check_current_state(driver, newspaper_type, "login_check")
            
            if state == "FAILURE":
                logger.error(f"❌ {message}")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking login failure state: {str(e)}")
            return False
    
    def _click_submit_button(self, driver) -> bool:
        """Find and click submit button"""
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:contains('Sign in')",
            "button:contains('Log in')",
            "button:contains('Login')", 
            "[data-testid*='submit']",
            "[data-testid*='signin']",
            "form button",
            ".submit-button"
        ]
        
        for selector in submit_selectors:
            try:
                if "contains" in selector:
                    # XPath for text content
                    text = selector.split("'")[1]
                    button = driver.find_element(By.XPATH, f"//button[contains(text(),'{text}')]")
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button and button.is_displayed() and button.is_enabled():
                    logger.info(f"Clicking submit button: {selector}")
                    button.click()
                    return True
            except:
                continue
                
        return False
    
    def _handle_captcha_if_present(self, driver, context: str) -> bool:
        """Check for and solve CAPTCHA if present using state detector"""
        try:
            # Check for CAPTCHA using state detector
            state, message = check_current_state(driver, getattr(self, 'newspaper_type', 'nyt'), context)
            
            if state == "CAPTCHA_PRESENT":
                logger.info(f"🧩 {message}")
                
                # Validate user agent consistency before CAPTCHA solving
                self._validate_user_agent_consistency(driver)
                
                # Initialize CAPTCHA solver with current attempt directory
                captcha_solver = CaptchaSolver(attempt_dir=self.current_attempt_dir)
                
                # Solve the CAPTCHA
                success = captcha_solver.solve_slider_captcha(driver, timeout=120)
                
                if success:
                    logger.info("✅ CAPTCHA solved successfully")
                    # Reset CAPTCHA counter for this context on success
                    StateDetector.reset_captcha_counter(context)
                    self._human_delay('medium')
                    return True
                else:
                    logger.warning("⚠️ CAPTCHA solving attempt failed")
                    return False
            
            elif state == "FAILURE":
                # CAPTCHA blocked after too many attempts
                logger.error(f"❌ {message}")
                return False
                    
            return False  # No CAPTCHA present
            
        except Exception as e:
            logger.error(f"CAPTCHA handling error: {str(e)}")
            return False
    
    def _validate_user_agent_consistency(self, driver):
        """Validate that browser and CapSolver use the same user agent"""
        try:
            # Get actual browser user agent
            browser_user_agent = driver.execute_script("return navigator.userAgent")
            
            # Compare with CapSolver user agent
            if browser_user_agent == CAPSOLVER_USER_AGENT:
                logger.info("✅ User agent consistency validated - browser matches CapSolver")
            else:
                logger.warning(f"⚠️ User agent mismatch detected!")
                logger.warning(f"Browser UA: {browser_user_agent}")
                logger.warning(f"CapSolver UA: {CAPSOLVER_USER_AGENT}")
                logger.warning("This may cause CAPTCHA solving failures!")
                
        except Exception as e:
            logger.error(f"User agent validation error: {str(e)}")
    
    def _verify_renewal(self, adapter, account) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """Verify renewal success using text-based state detection"""
        try:
            driver = adapter.driver
            current_url = driver.current_url
            newspaper_type = getattr(account, 'newspaper_type', 'nyt')
            newspaper_name = 'NYT' if newspaper_type == 'nyt' else 'WSJ'
            
            logger.info(f"🔍 Verifying {newspaper_name} renewal for {account.name} ({account.newspaper_type.upper()})")
            logger.info(f"🌐 Final URL: {current_url}")
            
            # Use new text-based state detection
            state, message = check_current_state(driver, newspaper_type, "final_verification")
            
            # Determine success based on state
            success = state in ["SUCCESS", "SUCCESS_WITH_WARNING"]
            
            # Extract expiration date if available
            expiration_datetime = self._extract_expiration_date(driver, newspaper_type)
            
            # Log the result with appropriate emoji based on state
            if state == "SUCCESS":
                logger.info(f"✅ {message or 'Renewal successful'}")
            elif state == "SUCCESS_WITH_WARNING":
                logger.warning(f"⚠️ {message or 'Renewal successful with warning'}")
            elif state == "FAILURE":
                logger.error(f"❌ {message or 'Renewal failed'}")
            else:
                logger.info(f"❓ {message or 'Renewal status uncertain'}")
            
            if expiration_datetime:
                logger.info(f"📅 Expiration detected: {expiration_datetime}")
            
            # Return state and message along with other data
            return success, current_url, expiration_datetime, state, message
            
        except Exception as e:
            logger.error(f"Renewal verification error: {str(e)}")
            return False, None, None, "FAILURE", f"Verification error: {str(e)}"
    
    def _cleanup_old_attempts(self, account_name: str):
        """Clean up old screenshot directories, keeping only the most recent N attempts"""
        try:
            # Get all directories for this account
            pattern = f"{account_name}_*"
            all_dirs = []
            
            for dir_name in os.listdir(self.screenshot_base_dir):
                if dir_name.startswith(f"{account_name}_"):
                    dir_path = os.path.join(self.screenshot_base_dir, dir_name)
                    if os.path.isdir(dir_path):
                        # Get directory creation time
                        try:
                            mtime = os.path.getmtime(dir_path)
                            all_dirs.append((mtime, dir_path, dir_name))
                        except:
                            continue
            
            # Sort by modification time (newest first)
            all_dirs.sort(reverse=True)
            
            # Keep only the most recent N attempts
            if len(all_dirs) > self.screenshot_retention:
                dirs_to_remove = all_dirs[self.screenshot_retention:]
                for _, dir_path, dir_name in dirs_to_remove:
                    try:
                        import shutil
                        shutil.rmtree(dir_path)
                        logger.info(f"🗑️ Cleaned up old screenshot directory: {dir_name}")
                    except Exception as e:
                        logger.error(f"Failed to remove directory {dir_name}: {e}")
                        
        except Exception as e:
            logger.error(f"Error during screenshot cleanup: {e}")
    
    def _extract_expiration_date(self, driver, newspaper_type: str) -> Optional[datetime]:
        """Extract expiration date from page content"""
        try:
            page_source = driver.page_source.lower()
            
            # Look for common expiration patterns
            import re
            import pytz
            
            # Patterns like "expires on March 15, 2024" or "until 03/15/2024"
            date_patterns = [
                r'expires?\s+(?:on\s+)?([a-z]+ \d{1,2},? \d{4})',
                r'until\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'(?:valid|active)\s+(?:through|until)\s+([a-z]+ \d{1,2},? \d{4})',
                r'renewal\s+date:?\s*([a-z]+ \d{1,2},? \d{4})',
                r'next\s+billing:?\s*([a-z]+ \d{1,2},? \d{4})'
            ]
            
            # Get timezone from environment
            tz_name = os.environ.get('TZ', 'America/New_York')
            local_tz = pytz.timezone(tz_name)
            
            for pattern in date_patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    date_str = matches[0]
                    try:
                        # Try to parse the date
                        from dateutil import parser
                        # Parse as local time and make timezone-aware
                        expiration_date = parser.parse(date_str)
                        if expiration_date.tzinfo is None:
                            expiration_date = local_tz.localize(expiration_date)
                        
                        # Convert to UTC for storage
                        expiration_date_utc = expiration_date.astimezone(pytz.UTC)
                        
                        # If it's in the past, probably wrong - add a year
                        if expiration_date_utc < datetime.now(pytz.UTC):
                            expiration_date_utc = expiration_date_utc.replace(year=expiration_date_utc.year + 1)
                        
                        return expiration_date_utc
                    except:
                        continue
                        
            return None
            
        except Exception as e:
            logger.debug(f"Expiration extraction error: {str(e)}")
            return None
    
    def _save_debug_screenshot(self, account, driver, step_name: str):
        """Save debug screenshot during renewal process (only in debug mode)"""
        try:
            # Only save intermediate screenshots if debug mode is enabled
            if not self.debug_mode:
                return
                
            if not driver or not self.current_attempt_dir:
                return
                
            timestamp = datetime.now().strftime("%H%M%S") 
            filename = f"{step_name}_{timestamp}"
            
            # Save screenshot
            screenshot_path = os.path.join(self.current_attempt_dir, f"{filename}.png")
            driver.save_screenshot(screenshot_path)
            
            # Save HTML source (only in debug mode)
            html_path = os.path.join(self.current_attempt_dir, f"{filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            
            # Save URL info
            url_path = os.path.join(self.current_attempt_dir, f"{filename}_url.txt")
            with open(url_path, 'w') as f:
                f.write(f"URL: {driver.current_url}\nTitle: {driver.title}\nTimestamp: {datetime.now()}")
                
            logger.debug(f"📸 Debug files saved: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving debug screenshot: {str(e)}")
    
    def _save_final_screenshot(self, account, driver, save_html: bool = None):
        """Save final screenshot for renewal attempt (always saves at least screenshot)"""
        try:
            if not driver or not self.current_attempt_dir:
                return None
                
            filename = "final_result"
            
            # Always save final screenshot (this is our ONE screenshot per attempt)
            screenshot_path = os.path.join(self.current_attempt_dir, f"{filename}.png") 
            driver.save_screenshot(screenshot_path)
            logger.info(f"📸 Final screenshot saved")
            
            # Only save HTML if in debug mode
            if self.debug_mode:
                # Save HTML source
                html_path = os.path.join(self.current_attempt_dir, f"{filename}.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                
                # Save URL info
                url_path = os.path.join(self.current_attempt_dir, f"{filename}_url.txt")
                with open(url_path, 'w') as f:
                    f.write(f"Final URL: {driver.current_url}\nTitle: {driver.title}\nTimestamp: {datetime.now()}")
                    
                logger.debug(f"📄 Final HTML and URL saved (debug mode)")
            
            # Return relative path for database storage
            attempt_dir_name = os.path.basename(self.current_attempt_dir)
            return f"{attempt_dir_name}/{filename}.png"
            
        except Exception as e:
            logger.error(f"Error saving final screenshot: {str(e)}")
            return None
    
    def _log_renewal_attempt(self, account, success: bool, message: str, duration: int, is_warning: bool = False, driver=None):
        """Log renewal attempt to database"""
        try:
            from app import app, db, RenewalLog
            from flask import has_app_context
            
            # Get screenshot filename from final screenshot
            screenshot_filename = None
            if self.current_attempt_dir:
                attempt_dir_name = os.path.basename(self.current_attempt_dir)
                screenshot_filename = f"{attempt_dir_name}/final_result.png"
            
            def _create_log_entry():
                log_entry = RenewalLog(
                    account_id=account.id,
                    success=success,
                    message=message,
                    duration_seconds=duration,
                    screenshot_filename=screenshot_filename
                )
                
                db.session.add(log_entry)
                db.session.commit()
                logger.info(f"📝 Log entry created: {'SUCCESS' if success else 'FAILURE'} for {account.name}")
            
            # Execute within app context
            if has_app_context():
                _create_log_entry()
            else:
                with app.app_context():
                    _create_log_entry()
                    
        except Exception as e:
            logger.error(f"Failed to log renewal attempt: {str(e)}")
    
    def _human_delay(self, delay_type: str = 'medium'):
        """Human-like delays based on renewal speed setting"""
        if self.renewal_speed == 'fast':
            multiplier = 0.5
        elif self.renewal_speed == 'slow':
            multiplier = 2.0
        else:  # normal
            multiplier = 1.0
        
        delays = {
            'small': 0.5 * multiplier,
            'medium': 1.5 * multiplier, 
            'long': 3.0 * multiplier
        }
        
        delay = delays.get(delay_type, 1.5 * multiplier)
        time.sleep(delay)
    
    def _human_type(self, element, text: str):
        """Type text with human-like timing"""
        import random
        
        for char in text:
            element.send_keys(char)
            # Small random delay between keystrokes
            if self.renewal_speed != 'fast':
                time.sleep(random.uniform(0.05, 0.15))
    
    def _is_gift_code_url(self, url: str) -> bool:
        """Check if URL is a gift code redemption URL"""
        if not url:
            return False
            
        gift_code_indicators = [
            'subscription/redeem',
            'gift_code=',
            'giftcode=',
            'redeem?',
            'activation?code=',
            'promo_code=',
            'pass_code=',
            'enter-redemption-code',  # WSJ redemption code URL pattern
            'partner.wsj.com/p/'      # WSJ partner redemption URL pattern
        ]
        
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in gift_code_indicators)
    
    def _click_newspaper_access_link(self, driver, newspaper_type: str) -> bool:
        """Click newspaper access link on library portal pages"""
        try:
            if newspaper_type == 'wsj':
                link_selectors = [
                    "//a[contains(text(), 'Visit the Wall Street Journal')]",
                    "//a[contains(text(), 'Visit The Wall Street Journal')]",
                    "//a[contains(text(), 'Wall Street Journal')]",
                    "//a[contains(text(), 'Access Wall Street Journal')]",
                    "//a[contains(text(), 'Go to Wall Street Journal')]",
                    "//a[contains(@href, 'wsj.com')]",
                    "a[href*='wsj.com']",
                    "//a[contains(@href, '/wsj')]"
                ]
            else:  # nyt
                link_selectors = [
                    "//a[contains(text(), 'Visit the New York Times')]",
                    "//a[contains(text(), 'Visit The New York Times')]",
                    "//a[contains(text(), 'New York Times')]",
                    "//a[contains(text(), 'Access New York Times')]",
                    "//a[contains(text(), 'Go to New York Times')]",
                    "//a[contains(text(), 'NYTimes')]",
                    "//a[contains(@href, 'nytimes.com')]",
                    "//a[contains(@href, 'nyt.com')]",
                    "a[href*='nytimes.com']",
                    "//a[contains(@href, '/nyt')]"
                ]
            
            for selector in link_selectors:
                try:
                    if selector.startswith("//"):
                        element = driver.find_element(By.XPATH, selector)
                    else:
                        element = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if element and element.is_displayed() and element.is_enabled():
                        logger.info(f"Found {newspaper_type.upper()} link: {selector}")
                        element.click()
                        return True
                except:
                    continue
                    
            return False
        except Exception as e:
            logger.debug(f"Error clicking {newspaper_type.upper()} access link: {str(e)}")
            return False
    
    def _handle_gift_code_redemption(self, adapter, account, gift_code_url: str) -> bool:
        """Handle gift code redemption flow"""
        try:
            logger.info(f"🎁 Processing gift code redemption for {account.name}")
            
            # Navigate to gift code URL
            adapter.driver.get(gift_code_url)
            self._human_delay('medium')
            
            # Save screenshot of gift code page
            self._save_debug_screenshot(account, adapter.driver, "gift_code_page")
            
            # Check if we've been redirected to a login page (WSJ partner URLs do this)
            current_url = adapter.driver.current_url.lower()
            if any(indicator in current_url for indicator in ['login', 'signin', 'auth', 'sso']):
                logger.info(f"🔄 Gift code URL redirected to login page: {current_url[:100]}...")
                # The gift code has been applied via URL, just need to login now
                return True
            
            # Look for and click redemption button (for URLs that have a redemption page)
            redeem_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Redeem')",
                "button:contains('Submit')",
                "button:contains('Continue')",
                "button:contains('Get Access')",
                "button:contains('Activate')",
                "[data-testid*='redeem']",
                "[data-testid*='submit']",
                ".redeem-button",
                ".submit-button"
            ]
            
            button_clicked = False
            for selector in redeem_selectors:
                try:
                    if ":contains" in selector:
                        # XPath for text content
                        text = selector.split("'")[1]
                        button = adapter.driver.find_element(By.XPATH, f"//button[contains(text(),'{text}')]")
                    else:
                        button = adapter.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if button and button.is_displayed() and button.is_enabled():
                        logger.info(f"Clicking redemption button: {selector}")
                        button.click()
                        button_clicked = True
                        break
                except:
                    continue
            
            if button_clicked:
                logger.info("✅ Gift code redemption button clicked")
                self._human_delay('medium')
                self._save_debug_screenshot(account, adapter.driver, "gift_code_submitted")
                return True
            else:
                # If no button found but we're on a valid page, assume auto-redirect will happen
                logger.info("⚠️ No redemption button found - assuming auto-redirect flow")
                self._human_delay('long')  # Wait for potential redirect
                return True
                
        except Exception as e:
            logger.error(f"Gift code redemption error: {str(e)}")
            return False