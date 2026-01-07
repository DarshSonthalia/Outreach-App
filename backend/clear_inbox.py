#!/usr/bin/env python3
"""
Cleanup Script: Clear all messages from the inbox
This deletes all Message records from the database.
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Message

def clear_inbox():
    """Delete all messages from the database."""
    db = SessionLocal()
    
    try:
        # Count messages before deletion
        count_before = db.query(Message).count()
        print(f"Messages in database before cleanup: {count_before}")
        
        # Delete all messages
        deleted_count = db.query(Message).delete()
        db.commit()
        
        print(f"✅ Successfully deleted {deleted_count} messages")
        
        # Verify deletion
        count_after = db.query(Message).count()
        print(f"Messages in database after cleanup: {count_after}")
        
        if count_after == 0:
            print("✅ Inbox is now empty!")
        else:
            print(f"⚠️  Warning: {count_after} messages still exist")
            
    except Exception as e:
        print(f"❌ Error clearing inbox: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🗑️  Clearing inbox...")
    clear_inbox()
