"""
Lead service for CSV upload, validation, and basic website sourcing.
"""
import csv
import io
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from email_validator import validate_email, EmailNotValidError

from app.config import safety_config

logger = logging.getLogger(__name__)

# Role email patterns - these should be flagged
ROLE_EMAIL_PATTERNS = [
    r'^info@',
    r'^support@',
    r'^sales@',
    r'^help@',
    r'^contact@',
    r'^admin@',
    r'^webmaster@',
    r'^noreply@',
    r'^no-reply@',
    r'^hello@',
    r'^team@',
    r'^hr@',
    r'^jobs@',
    r'^careers@',
    r'^feedback@',
]


class LeadService:
    """
    Service for lead management: CSV upload, validation, and sourcing.
    """
    
    @staticmethod
    def validate_email_address(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an email address.
        Returns (is_valid, normalized_email or None).
        """
        try:
            result = validate_email(email, check_deliverability=False)
            return True, result.normalized
        except EmailNotValidError:
            return False, None
    
    @staticmethod
    def is_role_email(email: str) -> bool:
        """
        Check if email is a role/generic email address.
        """
        email_lower = email.lower()
        for pattern in ROLE_EMAIL_PATTERNS:
            if re.match(pattern, email_lower):
                return True
        return False
    
    @staticmethod
    def parse_csv(file_content: bytes) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Parse CSV file content.
        Returns (columns, rows).
        """
        # Try to detect encoding
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            content = file_content.decode('latin-1')
        
        reader = csv.DictReader(io.StringIO(content))
        columns = reader.fieldnames or []
        rows = list(reader)
        
        return columns, rows
    
    @staticmethod
    def process_csv_leads(
        rows: List[Dict[str, str]],
        column_mapping: Dict[str, str]
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Process CSV rows into leads.
        Returns (leads, invalid_count, role_count).
        """
        leads = []
        invalid_count = 0
        role_count = 0
        
        for row in rows:
            email_col = column_mapping.get('email', '')
            email = row.get(email_col, '').strip()
            
            if not email:
                invalid_count += 1
                continue
            
            is_valid, normalized_email = LeadService.validate_email_address(email)
            if not is_valid:
                invalid_count += 1
                continue
            
            is_role = LeadService.is_role_email(normalized_email)
            if is_role:
                role_count += 1
            
            lead = {
                'email': normalized_email,
                'first_name': row.get(column_mapping.get('first_name', ''), '').strip() or None,
                'last_name': row.get(column_mapping.get('last_name', ''), '').strip() or None,
                'company': row.get(column_mapping.get('company', ''), '').strip() or None,
                'title': row.get(column_mapping.get('title', ''), '').strip() or None,
                'is_valid_email': True,
                'is_role_email': is_role,
                'source': 'csv',
                'source_url': None,
            }
            leads.append(lead)
        
        return leads, invalid_count, role_count
    
    # ==========================================
    # WEBSITE SOURCING
    # ==========================================
    
    @staticmethod
    def extract_emails_from_text(text: str) -> List[str]:
        """
        Extract email addresses from text content.
        """
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        
        # Filter and validate
        valid_emails = []
        for email in emails:
            is_valid, normalized = LeadService.validate_email_address(email)
            if is_valid and normalized not in valid_emails:
                valid_emails.append(normalized)
        
        return valid_emails
    
    @staticmethod
    def crawl_page(url: str, timeout: int = 10) -> Tuple[List[str], Optional[str]]:
        """
        Crawl a single page and extract emails.
        Returns (emails, error_message).
        """
        try:
            headers = {
                'User-Agent': 'EmailOutreach/1.0 (Lead Sourcing Bot)'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            text = soup.get_text()
            emails = LeadService.extract_emails_from_text(text)
            
            return emails, None
            
        except requests.RequestException as e:
            return [], str(e)
    
    @staticmethod
    def source_leads_from_domain(
        domain: str,
        max_pages: int = None
    ) -> List[Dict[str, Any]]:
        """
        Source leads from a single domain.
        Crawls homepage, /about, /contact, /team.
        """
        max_pages = max_pages or safety_config.MAX_PAGES_PER_DOMAIN
        leads = []
        found_emails = set()
        
        # Ensure domain has protocol
        if not domain.startswith('http'):
            base_url = f'https://{domain}'
        else:
            base_url = domain
            domain = urlparse(domain).netloc
        
        # Allowed paths to crawl
        paths = safety_config.ALLOWED_PATHS
        pages_crawled = 0
        
        for path in paths:
            if pages_crawled >= max_pages:
                break
            
            url = urljoin(base_url, path)
            emails, error = LeadService.crawl_page(url)
            
            if error:
                logger.warning(f"Failed to crawl {url}: {error}")
                continue
            
            pages_crawled += 1
            
            for email in emails:
                if email not in found_emails:
                    found_emails.add(email)
                    is_role = LeadService.is_role_email(email)
                    
                    leads.append({
                        'email': email,
                        'first_name': None,
                        'last_name': None,
                        'company': domain,
                        'title': None,
                        'is_valid_email': True,
                        'is_role_email': is_role,
                        'source': 'web_sourcing',
                        'source_url': url,
                    })
        
        return leads
    
    @staticmethod
    def source_leads(
        industry: str,
        region: str,
        max_domains: int = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Source leads by searching for company websites.
        This is a basic implementation - searches for companies
        matching industry/region criteria.
        
        Returns (leads, domains_searched).
        
        NOTE: This is a heuristic approach. Without paid data sources,
        we use web search to find company domains.
        """
        max_domains = max_domains or safety_config.MAX_DOMAINS_PER_RUN
        
        # For V1, we'll search for industry + region companies via a simple approach
        # In practice, user would provide a list of company domains
        
        logger.info(f"Lead sourcing for industry={industry}, region={region}")
        
        # This is a placeholder - in reality, you'd use a search API
        # or the user provides target domains
        # For V1, we'll require user to provide company domains directly
        
        return [], 0
    
    @staticmethod
    def source_leads_from_domains(
        domains: List[str],
        max_domains: int = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Source leads from a list of company domains.
        This is the recommended approach for V1.
        
        Returns (leads, domains_searched).
        """
        max_domains = max_domains or safety_config.MAX_DOMAINS_PER_RUN
        
        all_leads = []
        domains_searched = 0
        
        for domain in domains[:max_domains]:
            leads = LeadService.source_leads_from_domain(domain)
            all_leads.extend(leads)
            domains_searched += 1
            
            logger.info(f"Sourced {len(leads)} leads from {domain}")
        
        return all_leads, domains_searched
