#!/usr/bin/env python3
"""
Debug script: Check campaign pause reasons and mailbox auth status.
Helps identify which campaigns are stuck due to token refresh failures.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import SessionLocal
from app.models import Campaign, Mailbox, Event, CampaignStatus
from datetime import datetime

def main():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("CAMPAIGN STATUS REPORT")
        print("="*80)
        
        # Get all campaigns
        campaigns = db.query(Campaign).all()
        
        if not campaigns:
            print("\nNo campaigns found.")
            return
        
        paused_by_auth = []
        paused_other = []
        active = []
        
        for campaign in campaigns:
            status = campaign.status.value if campaign.status else "UNKNOWN"
            reason = campaign.pause_reason or "(none)"
            
            if status == "PAUSED":
                if campaign.pause_reason and "re-authentication" in campaign.pause_reason.lower():
                    paused_by_auth.append(campaign)
                else:
                    paused_other.append(campaign)
            else:
                active.append(campaign)
        
        print(f"\nTotal campaigns: {len(campaigns)}")
        print(f"  - Active (RUNNING/THROTTLED): {len(active)}")
        print(f"  - Paused (auth issues): {len(paused_by_auth)}")
        print(f"  - Paused (other reasons): {len(paused_other)}")
        
        if paused_by_auth:
            print("\n" + "="*80)
            print("CAMPAIGNS PAUSED DUE TO AUTH ISSUES")
            print("="*80)
            
            for campaign in paused_by_auth:
                mailbox = db.query(Mailbox).filter(Mailbox.id == campaign.mailbox_id).first()
                
                print(f"\nCampaign ID {campaign.id}: {campaign.name}")
                print(f"  Status: {campaign.status.value}")
                print(f"  Pause Reason: {campaign.pause_reason}")
                print(f"  Launched: {campaign.launched_at}")
                print(f"  Mailbox: {mailbox.email if mailbox else 'NOT FOUND'}")
                print(f"  Mailbox Active: {mailbox.is_active if mailbox else 'N/A'}")
                print(f"  Mailbox Status: {mailbox.status.value if mailbox and mailbox.status else 'N/A'}")
                print(f"  Token Expiry: {mailbox.token_expiry if mailbox else 'N/A'}")
                
                # Check for related events
                recent_events = db.query(Event).filter(
                    Event.entity_type == "mailbox",
                    Event.entity_id == campaign.mailbox_id
                ).order_by(Event.timestamp.desc()).limit(3).all()
                
                if recent_events:
                    print(f"  Recent Events:")
                    for event in recent_events:
                        print(f"    - {event.timestamp}: {event.action}")
                        if event.explanation:
                            print(f"      {event.explanation}")
        
        if paused_other:
            print("\n" + "="*80)
            print("CAMPAIGNS PAUSED FOR OTHER REASONS")
            print("="*80)
            
            for campaign in paused_other:
                print(f"\nCampaign ID {campaign.id}: {campaign.name}")
                print(f"  Status: {campaign.status.value}")
                print(f"  Pause Reason: {campaign.pause_reason}")
        
        if active:
            print("\n" + "="*80)
            print("ACTIVE CAMPAIGNS")
            print("="*80)
            
            for campaign in active:
                mailbox = db.query(Mailbox).filter(Mailbox.id == campaign.mailbox_id).first()
                print(f"\nCampaign ID {campaign.id}: {campaign.name}")
                print(f"  Status: {campaign.status.value}")
                print(f"  Mailbox: {mailbox.email if mailbox else 'NOT FOUND'}")
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        
        if paused_by_auth:
            print("\nTo fix campaigns paused due to auth issues:")
            print("\n1. User re-authenticates mailbox:")
            print("   GET /api/mailboxes/oauth/url?workspace_id=<workspace_id>")
            print("   Follow the OAuth flow")
            print("\n2. After re-auth, campaigns will auto-resume within seconds")
            print("   OR manually resume via:")
            print("   POST /api/campaigns/{campaign_id}/resume")
            print("\nFor API testing:")
            print("   curl -X POST http://localhost:8000/api/campaigns/1/resume \\")
            print("     -H 'Authorization: Bearer <token>'")
        
        print("\n")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
