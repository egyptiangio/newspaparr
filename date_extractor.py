"""
Unified date extraction module for finding and parsing expiration dates
from web pages. Consolidates all date extraction logic in one place.
"""

import re
import os
import logging
from datetime import datetime
from typing import Optional, Tuple
import pytz
from dateutil import parser

logger = logging.getLogger(__name__)


class DateExtractor:
    """Centralized date extraction and parsing utilities"""
    
    # Patterns with time (higher priority) - using case-insensitive flag
    DATETIME_PATTERNS = [
        # NYT with HTML spans: "expire on <span>August 7th, 2025</span> at <span>10:12 PM</span>"
        r'expire\s+on\s+[^>]*>([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})<[^>]*>\s+at\s+[^>]*>(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)<',
        # "Your pass is active and will expire on August 6th, 2025 at 9:09 PM"
        r'expire\s+on\s+([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)',
        # "August 7th, 2025 at 10:12 PM"
        r'([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4}\s+at\s+\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)',
        # "expires on March 15, 2024 at 11:59 PM"
        r'expires?\s+(?:on\s+)?([A-Za-z]+ \d{1,2},? \d{4}\s+at\s+\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)',
        # "valid until 03/15/2024 11:59 PM"
        r'(?:valid|active)\s+(?:through|until)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)',
    ]
    
    # Date-only patterns (lower priority) - using case-insensitive flag
    DATE_PATTERNS = [
        # NYT with HTML span: "expire on <span>August 7th, 2025</span>"
        r'expire\s+on\s+[^>]*>([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})<',
        r'expires?\s+(?:on\s+)?([A-Za-z]+ \d{1,2},? \d{4})',
        r'until\s+(\d{1,2}/\d{1,2}/\d{4})',
        r'(?:valid|active)\s+(?:through|until)\s+([A-Za-z]+ \d{1,2},? \d{4})',
        r'renewal\s+date:?\s*([A-Za-z]+ \d{1,2},? \d{4})',
        r'next\s+billing:?\s*([A-Za-z]+ \d{1,2},? \d{4})',
        r'expire\s+on\s+([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})',
    ]
    
    @classmethod
    def extract_expiration(cls, page_source: str, source_type: str = "unknown") -> Tuple[Optional[datetime], Optional[str]]:
        """
        Extract expiration date from page source.
        
        Args:
            page_source: HTML page source to search
            source_type: Type of source (e.g., "NYT", "WSJ") for logging
            
        Returns:
            Tuple of (datetime in UTC, formatted string for display)
            Both will be None if no date found
        """
        logger.info(f"📅 Extracting expiration date from {source_type} page ({len(page_source)} chars)")
        
        try:
            # Debug: Check if 'expire' exists in page
            if 'expire' in page_source.lower():
                expire_index = page_source.lower().index('expire')
                snippet = page_source[max(0, expire_index-50):min(len(page_source), expire_index+250)]
                logger.info(f"📋 Found 'expire' text context: ...{snippet}...")
            else:
                logger.info("📋 No 'expire' text found in page")
            
            # Get timezone from environment
            tz_name = os.environ.get('TZ', 'America/New_York')
            local_tz = pytz.timezone(tz_name)
            
            # Try patterns with both date and time first
            for pattern in cls.DATETIME_PATTERNS:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    logger.info(f"✅ DateTime pattern matched: {pattern[:50]}...")
                    
                    # Handle patterns that return tuples (date, time) separately
                    if isinstance(matches[0], tuple):
                        date_str = f"{matches[0][0]} {matches[0][1]}"
                    else:
                        date_str = matches[0]
                    
                    logger.info(f"📅 Extracted datetime string: {date_str}")
                    
                    try:
                        # Clean up the string (remove 'st', 'nd', 'rd', 'th')
                        cleaned_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str, flags=re.IGNORECASE)
                        
                        # Parse the date
                        expiration_date = parser.parse(cleaned_str)
                        
                        # Make timezone-aware if needed
                        if expiration_date.tzinfo is None:
                            expiration_date = local_tz.localize(expiration_date)
                            logger.info(f"📅 Localized to {tz_name}: {expiration_date}")
                        
                        # Convert to UTC for storage
                        expiration_date_utc = expiration_date.astimezone(pytz.UTC)
                        
                        # Check if date is reasonable (not in the past)
                        now_utc = datetime.now(pytz.UTC)
                        if expiration_date_utc < now_utc:
                            logger.warning(f"📅 Date appears to be in the past ({expiration_date_utc}), adding a year")
                            expiration_date_utc = expiration_date_utc.replace(year=expiration_date_utc.year + 1)
                        
                        # Format for display (in local timezone)
                        display_date = expiration_date.strftime('%B %d, %Y at %I:%M %p %Z')
                        
                        logger.info(f"✅ Successfully extracted expiration: {expiration_date_utc} (UTC)")
                        return expiration_date_utc, display_date
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to parse datetime '{date_str}': {e}")
                        continue
            
            # Try date-only patterns as fallback
            logger.info("📅 No datetime patterns matched, trying date-only patterns...")
            for pattern in cls.DATE_PATTERNS:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    logger.info(f"✅ Date pattern matched: {pattern[:50]}...")
                    date_str = matches[0]
                    logger.info(f"📅 Extracted date string: {date_str}")
                    
                    try:
                        # Clean up the string
                        cleaned_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str, flags=re.IGNORECASE)
                        
                        # Parse the date (will default to midnight)
                        expiration_date = parser.parse(cleaned_str)
                        
                        # Make timezone-aware
                        if expiration_date.tzinfo is None:
                            expiration_date = local_tz.localize(expiration_date)
                            logger.info(f"📅 Localized to {tz_name} (midnight): {expiration_date}")
                        
                        # Convert to UTC
                        expiration_date_utc = expiration_date.astimezone(pytz.UTC)
                        
                        # Check if reasonable
                        now_utc = datetime.now(pytz.UTC)
                        if expiration_date_utc < now_utc:
                            logger.warning(f"📅 Date appears to be in the past ({expiration_date_utc}), adding a year")
                            expiration_date_utc = expiration_date_utc.replace(year=expiration_date_utc.year + 1)
                        
                        # Format for display
                        display_date = expiration_date.strftime('%B %d, %Y')
                        
                        logger.info(f"✅ Successfully extracted expiration date: {expiration_date_utc} (UTC)")
                        return expiration_date_utc, display_date
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to parse date '{date_str}': {e}")
                        continue
            
            logger.warning(f"⚠️ No expiration date found in {source_type} page")
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Error during expiration extraction: {e}")
            return None, None
    
    @classmethod
    def extract_expiration_from_driver(cls, driver, source_type: str = "unknown") -> Tuple[Optional[datetime], Optional[str]]:
        """
        Extract expiration date from a Selenium WebDriver instance.
        
        Args:
            driver: Selenium WebDriver with loaded page
            source_type: Type of source for logging
            
        Returns:
            Tuple of (datetime in UTC, formatted string for display)
        """
        try:
            page_source = driver.page_source
            return cls.extract_expiration(page_source, source_type)
        except Exception as e:
            logger.error(f"❌ Error getting page source from driver: {e}")
            return None, None