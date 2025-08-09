"""
Delhi High Court Case Scraper Module
"""

import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Callable
import logging
import requests
from urllib.parse import urljoin
import json

class DatabaseManager:
    """Database operations for storing and retrieving case search data"""
    
    DB_NAME = 'court_data.db'
    
    @classmethod
    def initialize(cls):
        """Initialize SQLite database with required tables"""
        try:
            with sqlite3.connect(cls.DB_NAME) as conn:
                cursor = conn.cursor()
                
                # Create main search history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_number TEXT NOT NULL,
                        case_type TEXT NOT NULL,
                        filing_year INTEGER NOT NULL,
                        search_timestamp TEXT NOT NULL,
                        case_data TEXT,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create application logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS application_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        log_level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
        except sqlite3.Error as e:
            logging.error(f"Database initialization failed: {e}")
            raise
    
    @classmethod
    def save_search_record(cls, case_data: Dict, success: bool = True, error_message: str = None):
        """Save search record with data and error tracking"""
        try:
            with sqlite3.connect(cls.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO search_history 
                    (case_number, case_type, filing_year, search_timestamp, case_data, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    case_data.get('case_number', ''),
                    case_data.get('case_type', ''),
                    case_data.get('filing_year', 0),
                    datetime.now().isoformat(),
                    json.dumps(case_data) if success else None,
                    success,
                    error_message
                ))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to save search record: {e}")
    
    @classmethod
    def get_complete_search_history(cls) -> List[Dict]:
        """Retrieve search history with all case details for history display"""
        try:
            with sqlite3.connect(cls.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT case_data, created_at
                    FROM search_history
                    WHERE success = 1 AND case_data IS NOT NULL
                    ORDER BY created_at DESC
                ''')
                
                results = []
                for row in cursor.fetchall():
                    try:
                        case_data_json, created_at = row
                        if case_data_json:
                            case_data = json.loads(case_data_json)
                            case_data['search_time'] = created_at
                            results.append(case_data)
                    except Exception as e:
                        logging.error(f"Error parsing case data: {e}")
                        continue
                        
                return results
        except sqlite3.Error as e:
            logging.error(f"Failed to retrieve search history: {e}")
            return []
    
    @classmethod
    def get_all_searches(cls) -> List[Dict]:
        """Retrieve all search history for CSV export"""
        try:
            with sqlite3.connect(cls.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT case_number, case_type, filing_year, search_timestamp, success, error_message, created_at
                    FROM search_history
                    ORDER BY created_at DESC
                ''')
                columns = ['case_number', 'case_type', 'filing_year', 'search_timestamp', 'success', 'error_message', 'created_at']
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to retrieve all searches: {e}")
            return []
    
    @classmethod
    def get_recent_searches(cls, limit: int = 10) -> List[Dict]:
        """Retrieve recent successful searches for sidebar display"""
        try:
            with sqlite3.connect(cls.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT case_number, case_type, filing_year, search_timestamp
                    FROM search_history
                    WHERE success = 1
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
                columns = ['case_number', 'case_type', 'filing_year', 'search_time']
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to retrieve recent searches: {e}")
            return []
    
    @classmethod
    def get_search_statistics(cls) -> Dict:
        """Calculate and return search statistics for dashboard"""
        try:
            with sqlite3.connect(cls.DB_NAME) as conn:
                cursor = conn.cursor()
                
                # Get basic search counts
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_searches,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_searches,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_searches
                    FROM search_history
                ''')
                result = cursor.fetchone()
                
                # Calculate success rate
                total = result[0] if result and result[0] else 0
                successful = result[1] if result and result[1] else 0
                success_rate = (successful / total * 100) if total > 0 else 0
                
                return {
                    'total_searches': total,
                    'successful_searches': successful,
                    'failed_searches': result[2] if result and result[2] else 0,
                    'success_rate': round(success_rate, 1)
                }
        except sqlite3.Error as e:
            logging.error(f"Failed to get search statistics: {e}")
            return {'total_searches': 0, 'successful_searches': 0, 'failed_searches': 0, 'success_rate': 0}

class WebDriverManager:
    """WebDriver management with Chrome configuration"""
    
    @staticmethod
    def create_driver():
        """Create and configure Chrome WebDriver instance"""
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome resource problems
        chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Avoid detection
        chrome_options.add_argument("--disable-extensions")  # Disable extensions
        chrome_options.add_argument("--disable-plugins")  # Disable plugins
        
        # Stealth options
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Initialize Chrome driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            # Fallback configuration
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e2:
                raise Exception(f"Failed to create WebDriver: {str(e2)}")
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        # Remove webdriver property to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver

class FormHandler:
    """Form handling with multiple fallback strategies"""
    
    def __init__(self, driver, wait_timeout: int = 20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)
        self.logger = logging.getLogger(__name__)
    
    def wait_for_page_load(self, timeout: int = 10):
        """Wait for page loading"""
        try:
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # Additional buffer
        except Exception as e:
            self.logger.warning(f"Page load timeout: {e}")
    
    def fill_case_type(self, case_type: str) -> bool:
        """Fill case type dropdown with multiple selector strategies"""
        selectors = [
            (By.NAME, "case_type"),
            (By.ID, "case_type"),
            (By.XPATH, "//select[contains(@name, 'case') and contains(@name, 'type')]"),
            (By.XPATH, "//select[contains(@id, 'case_type')]")
        ]
        
        for by, selector in selectors:
            try:
                element = self.wait.until(EC.element_to_be_clickable((by, selector)))
                select_obj = Select(element)
                
                # Try exact text match first
                try:
                    select_obj.select_by_visible_text(case_type)
                    self.logger.info(f"Selected case type: {case_type}")
                    time.sleep(1)
                    return True
                except:
                    # Try partial text match
                    for option in select_obj.options:
                        if case_type in option.text:
                            select_obj.select_by_visible_text(option.text)
                            self.logger.info(f"Selected case type by partial match: {option.text}")
                            time.sleep(1)
                            return True
            except Exception as e:
                self.logger.debug(f"Case type selector {selector} failed: {e}")
                continue
        
        self.logger.error("Failed to select case type")
        return False
    
    def fill_case_number(self, case_number: str) -> bool:
        """Fill case number input field"""
        selectors = [
            (By.NAME, "case_no"),
            (By.NAME, "case_number"),
            (By.ID, "case_no"),
            (By.ID, "case_number"),
            (By.XPATH, "//input[contains(@name, 'case') and contains(@name, 'no')]"),
            (By.XPATH, "//input[contains(@placeholder, 'case')]")
        ]
        
        for by, selector in selectors:
            try:
                element = self.wait.until(EC.element_to_be_clickable((by, selector)))
                element.clear()
                element.send_keys(str(case_number))
                
                # Validate input
                if element.get_attribute('value') == str(case_number):
                    self.logger.info(f"Entered case number: {case_number}")
                    time.sleep(1)
                    return True
            except Exception as e:
                self.logger.debug(f"Case number selector {selector} failed: {e}")
                continue
        
        self.logger.error("Failed to enter case number")
        return False
    
    def fill_filing_year(self, year: int) -> bool:
        """Fill filing year dropdown"""
        selectors = [
            (By.NAME, "case_year"),
            (By.NAME, "year"),
            (By.NAME, "filing_year"),
            (By.ID, "case_year"),
            (By.ID, "year"),
            (By.XPATH, "//select[contains(@name, 'year')]")
        ]
        
        for by, selector in selectors:
            try:
                element = self.wait.until(EC.element_to_be_clickable((by, selector)))
                select_obj = Select(element)
                
                # Try selection by value first, then by text
                try:
                    select_obj.select_by_value(str(year))
                    self.logger.info(f"Selected filing year: {year}")
                    time.sleep(1)
                    return True
                except:
                    select_obj.select_by_visible_text(str(year))
                    self.logger.info(f"Selected filing year by text: {year}")
                    time.sleep(1)
                    return True
            except Exception as e:
                self.logger.debug(f"Filing year selector {selector} failed: {e}")
                continue
        
        self.logger.error("Failed to select filing year")
        return False
    
    def solve_captcha(self) -> bool:
        """CAPTCHA solving with multiple detection strategies"""
        try:
            # Look for CAPTCHA elements
            captcha_selectors = [
                (By.ID, "captcha-code"),
                (By.CLASS_NAME, "captcha-code"),
                (By.XPATH, "//span[contains(@class, 'captcha')]"),
                (By.XPATH, "//div[contains(@class, 'captcha')]//span"),
                (By.XPATH, "//*[contains(text(), 'CAPTCHA') or contains(@id, 'captcha')]")
            ]
            
            captcha_code = None
            # Search for CAPTCHA code
            for by, selector in captcha_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) >= 3 and (text.isdigit() or text.isalnum()):
                            captcha_code = text
                            self.logger.info(f"Found CAPTCHA code: {captcha_code}")
                            break
                    if captcha_code:
                        break
                except:
                    continue
            
            if not captcha_code:
                self.logger.warning("No CAPTCHA code found")
                return False
            
            # Find CAPTCHA input field and enter code
            input_selectors = [
                (By.NAME, "captchaInput"),
                (By.NAME, "captcha"),
                (By.ID, "captchaInput"),
                (By.ID, "captcha"),
                (By.XPATH, "//input[contains(@name, 'captcha')]"),
                (By.XPATH, "//input[contains(@placeholder, 'captcha')]")
            ]
            
            for by, selector in input_selectors:
                try:
                    input_element = self.wait.until(EC.element_to_be_clickable((by, selector)))
                    input_element.clear()
                    input_element.send_keys(captcha_code)
                    
                    # Verify input
                    if input_element.get_attribute('value') == captcha_code:
                        self.logger.info("CAPTCHA code entered successfully")
                        time.sleep(2)
                        return True
                except Exception as e:
                    self.logger.debug(f"CAPTCHA input selector {selector} failed: {e}")
                    continue
            
            self.logger.error("Failed to enter CAPTCHA code")
            return False
            
        except Exception as e:
            self.logger.error(f"CAPTCHA solving failed: {e}")
            return False
    
    def submit_form(self) -> bool:
        """Submit search form with multiple button strategies"""
        submit_selectors = [
            "//button[@id='search']",
            "//button[contains(@class, 'yellow-btn')]",
            "//button[contains(@class, 'search-btn')]",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//button[contains(text(), 'Search')]",
            "//button[contains(text(), 'Submit')]",
            "//input[contains(@value, 'Search')]"
        ]
        
        for selector in submit_selectors:
            try:
                button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                if button.is_enabled() and button.is_displayed():
                    # Scroll to button
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    
                    # Click submit button
                    button.click()
                    self.logger.info("Form submitted successfully")
                    
                    # Wait for results
                    time.sleep(8)
                    return True
            except Exception as e:
                self.logger.debug(f"Submit selector {selector} failed: {e}")
                continue
        
        self.logger.error("Failed to submit form")
        return False

class DataExtractor:
    """Data extraction with parsing capabilities"""
    
    def __init__(self, driver, base_url: str):
        self.driver = driver
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def extract_case_data(self, case_type: str, case_number: str, filing_year: int) -> Optional[Dict]:
        """Extract case data from search results"""
        try:
            # Wait for search results
            time.sleep(5)
            
            # Parse page content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for results table
            table_selectors = [
                {'id': 'caseTable'},
                {'class': 'case-table'},
                {'class': 'result-table'}
            ]
            
            table = None
            for selector in table_selectors:
                table = soup.find('table', selector)
                if table:
                    break
            
            if not table:
                self.logger.error("No results table found")
                return None
            
            # Extract table rows
            tbody = table.find('tbody')
            rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]  # Skip header
            
            if not rows:
                self.logger.error("No data rows found in table")
                return None
            
            # Process rows to find matching case data
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    case_data = self._parse_case_row(cells, case_type, case_number, filing_year)
                    if case_data:
                        return case_data
            
            self.logger.error("No matching case data found")
            return None
            
        except Exception as e:
            self.logger.error(f"Case data extraction failed: {e}")
            return None
    
    def _parse_case_row(self, cells, case_type: str, case_number: str, filing_year: int) -> Optional[Dict]:
        """Parse table row to extract case information"""
        try:
            # Extract basic information
            case_info = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            parties_info = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            court_info = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            
            # Extract case status
            status = self._extract_status(case_info)
            
            # Extract court details
            next_date, last_date, court_no = self._extract_court_details(court_info)
            
            # Extract orders page link
            orders_link = self._extract_orders_link(cells[1] if len(cells) > 1 else None)
            
            # Compile case data
            case_data = {
                'case_number': f"{case_type} {case_number}/{filing_year}",
                'case_type': case_type,
                'filing_year': str(filing_year),
                'status': status,
                'parties': parties_info,
                'next_date': next_date,
                'last_date': last_date,
                'court_no': court_no,
                'orders_link': orders_link,
                'extracted_at': datetime.now().isoformat(),
                'raw_case_info': case_info,
                'raw_court_info': court_info
            }
            
            self.logger.info(f"Successfully parsed case data for {case_data['case_number']}")
            return case_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse case row: {e}")
            return None
    
    def _extract_status(self, case_text: str) -> str:
        """Extract case status using pattern matching"""
        if "[DISPOSED]" in case_text:
            return "DISPOSED"
        elif "[CLOSED]" in case_text:
            return "CLOSED"
        elif "[PENDING]" in case_text:
            return "PENDING"
        elif "[" in case_text and "]" in case_text:
            # Extract status from brackets
            match = re.search(r'\[([^\]]+)\]', case_text)
            return match.group(1).strip() if match else "ACTIVE"
        return "ACTIVE"
    
    def _extract_court_details(self, court_text: str) -> tuple:
        """Extract court dates and number from text"""
        next_date = "Not Scheduled"
        last_date = "Not Available"
        court_no = "Not Assigned"
        
        # Extract next hearing date
        if "NEXT DATE:" in court_text:
            next_date = court_text.split("NEXT DATE:")[-1].split("Last Date:")[0].strip()
        elif "Next Date:" in court_text:
            next_date = court_text.split("Next Date:")[-1].split("Last Date:")[0].strip()
        
        # Extract last hearing date
        if "Last Date:" in court_text:
            last_date = court_text.split("Last Date:")[-1].split("COURT NO:")[0].strip()
        elif "LAST DATE:" in court_text:
            last_date = court_text.split("LAST DATE:")[-1].split("COURT NO:")[0].strip()
        
        # Extract court number
        if "COURT NO:" in court_text:
            court_no = court_text.split("COURT NO:")[-1].strip()
        elif "Court No:" in court_text:
            court_no = court_text.split("Court No:")[-1].strip()
        
        return next_date, last_date, court_no
    
    def _extract_orders_link(self, cell) -> Optional[str]:
        """Extract orders page link from table cell"""
        if not cell:
            return None
        
        try:
            # Find all links in the cell
            links = cell.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                # Look for order/status/detail related links
                if any(keyword in href.lower() for keyword in ['order', 'status', 'detail']):
                    # Ensure absolute URL
                    if href.startswith('http'):
                        return href
                    else:
                        return urljoin(self.base_url, href)
            return None
        except Exception as e:
            self.logger.error(f"Failed to extract orders link: {e}")
            return None
    
    def extract_orders_data(self, orders_url: str) -> List[Dict]:
        """Extract orders and documents from orders page"""
        try:
            self.logger.info(f"Extracting orders from: {orders_url}")
            self.driver.get(orders_url)
            time.sleep(5)
            
            # Parse orders page content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for orders table
            table = soup.find('table', {'id': 'caseTable'}) or soup.find('table', {'class': 'order-table'})
            if not table:
                self.logger.warning("No orders table found")
                return []
            
            orders = []
            # Extract table rows
            tbody = table.find('tbody')
            rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]  # Skip header
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        order_data = self._parse_order_row(cells, i)
                        if order_data:
                            orders.append(order_data)
                except Exception as e:
                    self.logger.warning(f"Failed to parse order row {i}: {e}")
                    continue
            
            self.logger.info(f"Extracted {len(orders)} orders")
            return orders
            
        except Exception as e:
            self.logger.error(f"Orders extraction failed: {e}")
            return []
    
    def _parse_order_row(self, cells, index: int) -> Optional[Dict]:
        """Parse order row to extract order information"""
        try:
            # Extract order information
            case_link_cell = cells[1] if len(cells) > 1 else cells[0]
            order_date = cells[2].get_text(strip=True) if len(cells) > 2 else "Date not available"
            
            # Extract PDF link and case information
            pdf_link = None
            case_info = "Not Available"
            
            a_tag = case_link_cell.find('a', href=True)
            if a_tag:
                pdf_link = a_tag.get('href')
                case_info = a_tag.get_text(strip=True)
                
                # Ensure absolute URL
                if pdf_link and not pdf_link.startswith('http'):
                    pdf_link = urljoin(self.base_url, pdf_link)
            
            return {
                'order_index': index + 1,
                'date': order_date,
                'case_info': case_info,
                'pdf_link': pdf_link
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse order row: {e}")
            return None

class CourtScraper:
    """Main court scraper class with error handling"""
    
    # Delhi High Court URLs
    BASE_URL = "https://delhihighcourt.nic.in/"
    SEARCH_URL = "https://delhihighcourt.nic.in/app/get-case-type-status"
    
    def __init__(self):
        self.driver = None
        self.form_handler = None
        self.data_extractor = None
        self.logger = logging.getLogger(__name__)
    
    def search_case_details(self, case_type: str, case_number: str, filing_year: int, 
                           progress_callback: Optional[Callable] = None) -> Optional[Dict]:
        """Main method to search for case details"""
        error_message = None
        case_data = None
        
        try:
            # Initialize browser session
            if progress_callback:
                progress_callback("Initializing browser session", 10)
            self._setup_browser()
            
            # Navigate to search page
            if progress_callback:
                progress_callback("Loading court website", 25)
            self.driver.get(self.SEARCH_URL)
            self.form_handler.wait_for_page_load()
            
            # Fill search form
            if progress_callback:
                progress_callback("Filling case search form", 40)
            if not self._fill_search_form(case_type, case_number, filing_year):
                error_message = "Unable to fill search form"
                raise Exception(error_message)
            
            # Handle CAPTCHA
            if progress_callback:
                progress_callback("Processing security verification", 60)
            if not self.form_handler.solve_captcha():
                error_message = "Security verification failed - please try again"
                raise Exception(error_message)
            
            # Submit search form
            if progress_callback:
                progress_callback("Submitting search request", 70)
            if not self.form_handler.submit_form():
                error_message = "Search submission failed"
                raise Exception(error_message)
            
            # Extract case data from results
            if progress_callback:
                progress_callback("Extracting case information", 85)
            case_data = self.data_extractor.extract_case_data(case_type, case_number, filing_year)
            
            if not case_data:
                error_message = "No case found with the provided details"
                return None
            
            # Extract orders if available
            if case_data.get('orders_link'):
                if progress_callback:
                    progress_callback("Retrieving order documents", 95)
                orders = self.data_extractor.extract_orders_data(case_data['orders_link'])
                case_data['orders'] = orders
            
            if progress_callback:
                progress_callback("Search completed successfully", 100)
            
            # Save successful search to database
            DatabaseManager.save_search_record(case_data, success=True)
            return case_data
            
        except Exception as e:
            error_message = str(e) or "Unknown error occurred during search"
            self.logger.error(f"Search failed: {error_message}")
            
            # Save failed search record
            failed_data = {
                'case_number': f"{case_type} {case_number}/{filing_year}",
                'case_type': case_type,
                'filing_year': filing_year
            }
            DatabaseManager.save_search_record(failed_data, success=False, error_message=error_message)
            
            raise Exception(error_message)
        
        finally:
            # Clean up browser resources
            self._cleanup()
    
    def _setup_browser(self):
        """Initialize browser components"""
        try:
            self.driver = WebDriverManager.create_driver()
            self.form_handler = FormHandler(self.driver)
            self.data_extractor = DataExtractor(self.driver, self.BASE_URL)
            self.logger.info("Browser components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to setup browser: {e}")
            raise
    
    def _fill_search_form(self, case_type: str, case_number: str, filing_year: int) -> bool:
        """Fill search form with validation"""
        try:
            # Fill case type dropdown
            if not self.form_handler.fill_case_type(case_type):
                self.logger.error("Failed to select case type")
                return False
            
            # Fill case number input
            if not self.form_handler.fill_case_number(case_number):
                self.logger.error("Failed to enter case number")
                return False
            
            # Fill filing year dropdown
            if not self.form_handler.fill_filing_year(filing_year):
                self.logger.error("Failed to select filing year")
                return False
            
            self.logger.info("Search form filled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Form filling failed: {e}")
            return False
    
    def _cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser session closed successfully")
            except Exception as e:
                self.logger.warning(f"Browser cleanup warning: {e}")
            finally:
                # Reset all references
                self.driver = None
                self.form_handler = None
                self.data_extractor = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
