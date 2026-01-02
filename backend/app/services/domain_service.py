"""
Domain service for SPF and DMARC checks.
"""
import dns.resolver
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class DomainService:
    """
    DNS checks for email domain health.
    """
    
    @staticmethod
    def check_spf(domain: str) -> Tuple[bool, Optional[str]]:
        """
        Check if domain has a valid SPF record.
        Returns (is_valid, record_content).
        """
        try:
            # SPF records are TXT records
            answers = dns.resolver.resolve(domain, "TXT")
            
            for rdata in answers:
                txt_record = str(rdata).strip('"')
                if txt_record.startswith("v=spf1"):
                    logger.info(f"SPF record found for {domain}: {txt_record}")
                    return True, txt_record
            
            logger.warning(f"No SPF record found for {domain}")
            return False, None
            
        except dns.resolver.NXDOMAIN:
            logger.error(f"Domain {domain} does not exist")
            return False, None
        except dns.resolver.NoAnswer:
            logger.warning(f"No TXT records found for {domain}")
            return False, None
        except Exception as e:
            logger.error(f"Error checking SPF for {domain}: {e}")
            return False, None
    
    @staticmethod
    def check_dmarc(domain: str) -> Tuple[bool, Optional[str]]:
        """
        Check if domain has a valid DMARC record.
        Returns (is_valid, record_content).
        """
        dmarc_domain = f"_dmarc.{domain}"
        
        try:
            answers = dns.resolver.resolve(dmarc_domain, "TXT")
            
            for rdata in answers:
                txt_record = str(rdata).strip('"')
                if txt_record.startswith("v=DMARC1"):
                    logger.info(f"DMARC record found for {domain}: {txt_record}")
                    return True, txt_record
            
            logger.warning(f"No DMARC record found for {domain}")
            return False, None
            
        except dns.resolver.NXDOMAIN:
            logger.warning(f"No DMARC record found for {domain}")
            return False, None
        except dns.resolver.NoAnswer:
            logger.warning(f"No DMARC TXT record found for {domain}")
            return False, None
        except Exception as e:
            logger.error(f"Error checking DMARC for {domain}: {e}")
            return False, None
    
    @staticmethod
    def get_domain_health_status(spf_valid: bool, dmarc_valid: bool) -> dict:
        """
        Get human-readable health status for a domain.
        """
        issues = []
        warnings = []
        
        if not spf_valid:
            issues.append({
                "type": "error",
                "message": "SPF record not found",
                "explanation": "Without SPF, receiving servers cannot verify your emails are from authorized sources. This increases spam risk."
            })
        
        if not dmarc_valid:
            warnings.append({
                "type": "warning", 
                "message": "DMARC record not found",
                "explanation": "DMARC helps protect your domain from spoofing. While not required, it's strongly recommended."
            })
        
        if spf_valid and dmarc_valid:
            status = "healthy"
            message = "Domain is properly configured for email sending."
        elif spf_valid:
            status = "warning"
            message = "Domain is functional but missing DMARC record."
        else:
            status = "error"
            message = "Domain is missing critical email authentication records."
        
        return {
            "status": status,
            "message": message,
            "issues": issues,
            "warnings": warnings,
            "can_proceed": True  # User can proceed with warning
        }
