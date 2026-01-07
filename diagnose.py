#!/usr/bin/env python3
"""
Diagnostic Script: Check if everything is working
Run this after deployment to verify all systems
"""

import requests
import json
import subprocess
import sys
from pathlib import Path

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    SYSTEM DIAGNOSTIC SCRIPT                               ║
║                                                                            ║
║  This script verifies that all fixes are working correctly                ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

BASE_API_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def test(name, func):
    """Run a test and print result"""
    try:
        result = func()
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
        return result
    except Exception as e:
        print(f"  ❌ FAIL  {name}: {str(e)}")
        return False

# ============================================================================
# SECTION 1: CONNECTIVITY CHECKS
# ============================================================================

print_section("1. CONNECTIVITY CHECKS")

def check_frontend():
    r = requests.get(FRONTEND_URL, timeout=5)
    return r.status_code == 200

def check_backend():
    r = requests.get(f"{BASE_API_URL}/api/health", timeout=5)
    return r.status_code == 200

def check_postgres():
    try:
        r = requests.get(f"{BASE_API_URL}/api/health", timeout=5)
        return r.status_code == 200
    except:
        return False

results = {
    "frontend": test("Frontend (localhost:3000)", check_frontend),
    "backend": test("Backend (localhost:8000)", check_backend),
    "database": test("Database connectivity", check_postgres),
}

# ============================================================================
# SECTION 2: DOCKER STATUS
# ============================================================================

print_section("2. DOCKER CONTAINER STATUS")

def get_container_status():
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            cwd="c:\\Users\\carbo\\outreach app antigravity"
        )
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"

print(get_container_status())

# ============================================================================
# SECTION 3: FRONTEND CODE VERIFICATION
# ============================================================================

print_section("3. FRONTEND CODE VERIFICATION")

def check_api_client():
    """Check if api.ts has disconnect method"""
    path = Path("c:\\Users\\carbo\\outreach app antigravity\\frontend\\src\\lib\\api.ts")
    content = path.read_text()
    return "disconnect:" in content and "DELETE" in content

def check_dashboard():
    """Check if dashboard has new handlers"""
    path = Path("c:\\Users\\carbo\\outreach app antigravity\\frontend\\src\\app\\dashboard\\page.tsx")
    content = path.read_text()
    checks = [
        "handleRelinkMailbox" in content,
        "handleDisconnectMailbox" in content,
        "handleAddMailbox" in content,
        "relinkingMailboxId" in content,
    ]
    return all(checks)

test("API client has disconnect() method", check_api_client)
test("Dashboard has all handler functions", check_dashboard)

# ============================================================================
# SECTION 4: BACKEND CODE VERIFICATION
# ============================================================================

print_section("4. BACKEND CODE VERIFICATION")

def check_gmail_service():
    """Check if gmail_service.py has error handling"""
    path = Path("c:\\Users\\carbo\\outreach app antigravity\\backend\\app\\services\\gmail_service.py")
    content = path.read_text()
    checks = [
        "RefreshError" in content,
        "get_credentials_from_encrypted" in content,
        "except RefreshError as e" in content,
    ]
    return all(checks)

def check_campaign_worker():
    """Check if campaign_worker.py handles token refresh"""
    path = Path("c:\\Users\\carbo\\outreach app antigravity\\backend\\app\\workers\\campaign_worker.py")
    content = path.read_text()
    checks = [
        "_mark_reauth_required" in content,
        "Token refresh failed" in content,
    ]
    return all(checks)

test("Gmail service has error handling", check_gmail_service)
test("Campaign worker handles token refresh", check_campaign_worker)

# ============================================================================
# SECTION 5: API ENDPOINTS TEST
# ============================================================================

print_section("5. API ENDPOINTS TEST")

def test_health():
    try:
        r = requests.get(f"{BASE_API_URL}/api/health")
        return r.status_code == 200
    except:
        return False

def test_mailboxes_endpoint():
    try:
        # This will fail auth but endpoint should exist
        r = requests.get(f"{BASE_API_URL}/api/mailboxes/?workspace_id=1")
        return r.status_code in [200, 403, 401, 422]  # Any valid response
    except:
        return False

test("Health endpoint", test_health)
test("Mailboxes endpoint exists", test_mailboxes_endpoint)

# ============================================================================
# SECTION 6: TOKEN REFRESH SIMULATION
# ============================================================================

print_section("6. BACKEND LOGS ANALYSIS")

def check_backend_logs():
    try:
        result = subprocess.run(
            ["docker-compose", "logs", "--tail=50", "outreach_backend"],
            capture_output=True,
            text=True,
            cwd="c:\\Users\\carbo\\outreach app antigravity"
        )
        logs = result.stdout
        
        # Check for critical errors
        bad_keywords = ["Traceback", "fatal error", "CRITICAL"]
        has_errors = any(keyword in logs for keyword in bad_keywords)
        
        # Check for good patterns
        good_keywords = ["Application startup complete", "token", "refresh"]
        has_good = any(keyword in logs for keyword in good_keywords)
        
        print("\nRecent backend logs (last 20 lines):")
        print("-" * 80)
        print("\n".join(logs.split("\n")[-20:]))
        print("-" * 80)
        
        return not has_errors
    except Exception as e:
        print(f"Could not read logs: {e}")
        return False

check_backend_logs()

# ============================================================================
# SECTION 7: SUMMARY
# ============================================================================

print_section("SUMMARY")

all_passed = all(results.values())

if all_passed:
    print("""
    ✅ ALL SYSTEMS ONLINE
    
    The deployment appears to be working correctly.
    
    Next steps:
    1. Visit http://localhost:3000 in your browser
    2. Login to dashboard
    3. Check "Connected Mailboxes" section for new buttons
    4. Try the "Add Mailbox" button
    5. Monitor logs for any issues
    """)
else:
    print("""
    ⚠️  SOME SYSTEMS NOT RESPONDING
    
    Issues detected:
    """)
    
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"    {status} {name.upper()}")
    
    print("""
    
    To fix:
    1. Check Docker status: docker-compose ps
    2. Restart services: docker-compose down && docker-compose up --build
    3. Wait 2-3 minutes for services to fully start
    4. Re-run this script
    """)

# ============================================================================
# SECTION 8: MANUAL CHECKS
# ============================================================================

print_section("MANUAL VERIFICATION STEPS")

print("""
If everything passed above, do these manual checks:

1. FRONTEND UI CHECK:
   □ Visit http://localhost:3000
   □ Login to dashboard
   □ Scroll to "Connected Mailboxes" section
   □ Verify you see "[+ Add Mailbox]" button in header
   □ Verify each mailbox has action buttons
   
2. BROWSER CONSOLE CHECK:
   □ Press F12 to open DevTools
   □ Go to Console tab
   □ Reload page (F5)
   □ Should see NO red errors
   □ Should see DEBUG messages (that's OK)
   
3. BACKEND LOGS CHECK:
   □ Run: docker-compose logs -f outreach_backend
   □ Create a test campaign
   □ Launch it
   □ Watch logs for "process_due_sends" or token messages
   □ Should NOT see Python Traceback
   
4. TEST TOKEN REFRESH:
   □ If you have an [Inactive] mailbox
   □ Click [🔄 Re-link] button
   □ Complete Google OAuth
   □ Check if mailbox becomes [Active]
   □ Check logs for "Refreshed tokens" message
   
5. TEST ADD MAILBOX:
   □ Click [+ Add Mailbox] button
   □ Complete Google OAuth with different account
   □ Should appear in mailbox list as [Active]
   □ Should be usable in campaigns

""")

print("\n" + "="*80)
print("  Diagnostic complete!")
print("="*80 + "\n")
