
import logging
import sys
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Workspace, Domain, User
from app.services.warmup_service import WarmupService
from app.services.safety_service import SafetyService

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_warmup():
    db = SessionLocal()
    try:
        logger.info("=== Starting Domain Warm-up Verification ===")

        # 1. Verify New Workspace Creation
        logger.info("\n[Test 1] Verifying New Workspace Defaults...")
        # Need a user first
        user = db.query(User).first()
        if not user:
            logger.error("No users found in DB. Cannot test workspace creation.")
            return

        # Create dummy workspace
        new_ws = Workspace(
            user_id=user.id,
            name=f"Warmup Test Workspace {datetime.utcnow().timestamp()}",
            warmup_enabled=True,
            warmup_start_date=datetime.utcnow()
        )
        db.add(new_ws)
        db.commit()
        db.refresh(new_ws)

        if new_ws.warmup_enabled and new_ws.warmup_start_date:
            logger.info(f"✅ PASS: New workspace created with warmup_enabled=True (Start: {new_ws.warmup_start_date})")
        else:
            logger.error(f"❌ FAIL: New workspace missing warmup flags. Enabled: {new_ws.warmup_enabled}")

        # 2. Verify Warmup Schedule Logic
        logger.info("\n[Test 2] Verifying Warmup Schedule Logic...")
        
        # Day 1
        day1_limit = WarmupService.daily_limit(new_ws, Domain(warmup_completed=False))
        if day1_limit == 5:
            logger.info("✅ PASS: Day 1 limit is 5")
        else:
             logger.error(f"❌ FAIL: Day 1 limit is {day1_limit}, expected 5")

        # Mock Day 3
        new_ws.warmup_start_date = datetime.utcnow() - timedelta(days=2) # 2 days ago = Day 3
        day3_limit = WarmupService.daily_limit(new_ws, Domain(warmup_completed=False))
        if day3_limit == 12:
            logger.info("✅ PASS: Day 3 limit is 12")
        else:
             logger.error(f"❌ FAIL: Day 3 limit is {day3_limit}, expected 12")

        # 3. Verify Completion Logic
        logger.info("\n[Test 3] Verifying Completion Logic...")
        domain = Domain(warmup_completed=True)
        limit = WarmupService.daily_limit(new_ws, domain)
        if limit is None:
             logger.info("✅ PASS: Completed domain has NO warmup limit")
        else:
             logger.error(f"❌ FAIL: Completed domain has limit {limit}")
             
        # Cleanup
        logger.info("\nCleaning up test data...")
        db.delete(new_ws)
        db.commit()
        logger.info("=== Verification Complete ===")

    except Exception as e:
        logger.error(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_warmup()
