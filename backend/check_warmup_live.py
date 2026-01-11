
import logging
from app.database import SessionLocal
from app.models import Workspace, Domain, Campaign, Mailbox
from sqlalchemy import desc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_latest_warmup_status():
    db = SessionLocal()
    try:
        # Get latest workspace
        latest_workspace = db.query(Workspace).order_by(desc(Workspace.created_at)).first()
        
        if not latest_workspace:
            logger.info("❌ No workspaces found.")
            return

        logger.info(f"=== Latest Workspace: '{latest_workspace.name}' ===")
        logger.info(f"ID: {latest_workspace.id}")
        logger.info(f"Created At: {latest_workspace.created_at}")
        logger.info(f"Warmup Enabled: {latest_workspace.warmup_enabled}")
        logger.info(f"Warmup Start Date: {latest_workspace.warmup_start_date}")
        
        if latest_workspace.warmup_enabled:
            logger.info("✅ PASS: Warmup is ENABLED.")
        else:
            logger.info("❌ FAIL: Warmup is DISABLED.")

        # Get associated campaigns
        campaigns = db.query(Campaign).filter(Campaign.workspace_id == latest_workspace.id).all()
        if campaigns:
            logger.info(f"\nFound {len(campaigns)} campaign(s).")
        else:
            logger.info("\nNo campaigns found for this workspace.")

        # Get mailboxes/domains
        mailboxes = db.query(Mailbox).filter(Mailbox.workspace_id == latest_workspace.id).all()
        if not mailboxes:
            logger.info("❌ No mailboxes connected.")
        
        for mb in mailboxes:
            domain = mb.domain
            if domain:
                logger.info(f"\n--- Domain: {domain.domain} ---")
                logger.info(f"Warmup Day: {domain.warmup_day}")
                logger.info(f"Warmup Completed: {domain.warmup_completed}")
                
                # Verify logic
                from app.services.warmup_service import WarmupService
                current_day = WarmupService.current_day(latest_workspace)
                limit = WarmupService.daily_limit(latest_workspace, domain)
                
                logger.info(f"Calculated Current Day: {current_day}")
                logger.info(f"Calculated Daily Limit: {limit}")
                
                if current_day == 1 and limit == 5:
                     logger.info("✅ PASS: Schedule logic is correct for Day 1.")
                elif current_day == domain.warmup_day:
                     logger.info(f"ℹ️ Status consistent (DB says day {domain.warmup_day}, Calc says {current_day})")
            else:
                logger.info(f"Mailbox {mb.email} has no domain linked.")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_latest_warmup_status()
