# Interest Filtering Testing Guide

**Date**: January 7, 2026
**Status**: Inbox cleared, ready for testing
**Feature**: Automatic classification of replies based on interest keywords

---

## Overview

The system now automatically detects if a recipient is interested by analyzing their reply for interest keywords. Replies are classified into 4 categories:

| Classification | Keywords | Example |
|---|---|---|
| **BOOKING_INTENT** (✅ Interested) | scheduling, interest, engagement | "Let's schedule a call", "Sounds great" |
| **NEGATIVE** (❌ Not Interested) | rejection, disinterest | "Not interested", "Wrong person" |
| **UNSUBSCRIBE** (🚫 Unsubscribed) | removal requests | "Unsubscribe", "Stop contacting me" |
| **NEUTRAL** (💬 Uncertain) | no clear signal | "Ok", "Thanks for reaching out" |

---

## Testing Steps

### Step 1: Create a Fresh Campaign

1. Go to **http://localhost:3000/dashboard**
2. Click **"Create Campaign"** or **"New Campaign"**
3. Fill in:
   - **Campaign Name**: `Interest Test Campaign`
   - **Subject**: `Quick question for you`
   - **Body**: `Hi there, I'd like to learn more about your needs. Are you open to a quick chat?`
   - **Safety Level**: `MEDIUM`
4. **Launch Campaign**
5. Add test leads:
   - Use your own email or test email addresses
   - Example: `test1@example.com`, `test2@example.com`
6. **Confirm** and wait for emails to be sent

---

### Step 2: Send Test Replies with Different Classifications

#### Test Case 1: BOOKING_INTENT ✅
**Goal**: Verify system correctly identifies interested leads

**Steps**:
1. Reply to the campaign email from one of the test email addresses
2. Use one of these phrases in your reply:
   - ✅ "Sounds great, when can we chat?"
   - ✅ "I'm interested in learning more"
   - ✅ "Let's schedule a call"
   - ✅ "Would love to discuss this"
   - ✅ "How do we get started?"
   - ✅ "What's the next step?"

3. Send the reply
4. Wait 2-3 minutes (inbox polling runs every 2 minutes)
5. Go to **Inbox** tab in dashboard
6. **Verify**:
   - ✅ Reply appears in inbox
   - ✅ Badge shows **"📅 Interested"** (green/success color)
   - ✅ Dashboard campaign tally increases

---

#### Test Case 2: NEGATIVE ❌
**Goal**: Verify system flags disinterested leads

**Steps**:
1. Reply with one of these phrases:
   - ❌ "Not interested"
   - ❌ "No thanks"
   - ❌ "Wrong person"
   - ❌ "We're not looking"
   - ❌ "Leave me alone"

2. Send the reply
3. Wait 2-3 minutes
4. Check Inbox
5. **Verify**:
   - ✅ Reply appears with **"❌ Not Interested"** badge (warning color)
   - ✅ Lead status shows NEGATIVE classification
   - ✅ No future emails will be sent to this lead

---

#### Test Case 3: UNSUBSCRIBE 🚫
**Goal**: Verify system automatically suppresses unsubscribe requests

**Steps**:
1. Reply with:
   - 🚫 "Unsubscribe"
   - 🚫 "Remove me from your list"
   - 🚫 "Stop contacting me"
   - 🚫 "Opt out"

2. Send the reply
3. Wait 2-3 minutes
4. Check Inbox
5. **Verify**:
   - ✅ Reply appears with **"🚫 Unsubscribed"** badge (danger color)
   - ✅ Lead added to suppression list
   - ✅ Dashboard shows lead as UNSUBSCRIBED
   - ✅ Future campaigns will not email this lead

---

#### Test Case 4: NEUTRAL 💬
**Goal**: Verify system defaults to NEUTRAL when no clear signal

**Steps**:
1. Reply with:
   - 💬 "Ok"
   - 💬 "Thanks"
   - 💬 "Got it"
   - 💬 "I'll check it out"
   - 💬 "Will get back to you"

2. Send the reply
3. Wait 2-3 minutes
4. Check Inbox
5. **Verify**:
   - ✅ Reply appears with **"💬 Neutral"** badge (info color)
   - ✅ Requires manual review to determine next action
   - ✅ Can manually change classification using buttons

---

### Step 3: Verify Multi-Reply Thread Support

**Goal**: Ensure multiple replies in same conversation all appear

**Steps**:
1. Take Test Case 1 (BOOKING_INTENT reply)
2. Send a **second reply** to the same campaign email:
   - Example: "I'm free Tuesday at 2pm"
3. Wait 2-3 minutes for polling
4. Check Inbox → Select the conversation
5. **Verify**:
   - ✅ Both replies appear in thread
   - ✅ Messages ordered newest first
   - ✅ Your sent messages on **right side**
   - ✅ Their replies on **left side**
   - ✅ Timestamps show correct chronology
   - ✅ No quoted message clutter

---

### Step 4: Test Manual Classification Override

**Goal**: Verify you can manually change classifications

**Steps**:
1. Select a NEUTRAL reply in inbox
2. At top of message, click a different classification badge:
   - Click **"📅 Interested"**
3. **Verify**:
   - ✅ Badge updates immediately
   - ✅ System saves the new classification
   - ✅ Reload inbox - classification persists

---

### Step 5: Dashboard Tally Verification

**Goal**: Ensure dashboard shows correct reply counts

**Steps**:
1. Go to **Dashboard** tab
2. Click on your test campaign
3. Check stats section
4. **Verify**:
   - ✅ **"Replies"** count matches inbox message count
   - ✅ **"Meetings Booked"** = count of BOOKING_INTENT replies
   - ✅ Tally updates when new replies arrive

---

## Expected Keyword Matches

### BOOKING_INTENT Keywords (✅ Interested)
The system detects these patterns (case-insensitive):

**Scheduling**:
- "schedule a call/meeting/demo"
- "book a time/slot"
- "set up a"
- "when are you free"
- "available"

**Interest**:
- "sounds great/good/interesting"
- "would love to"
- "tell me more"
- "more information"
- "interested in"

**Engagement**:
- "how do we get started"
- "what's the next step"
- "let's move forward"
- "catch up soon"
- "let's chat/meet/discuss"

---

### NEGATIVE Keywords (❌ Not Interested)
- "not interested"
- "no thanks"
- "wrong person/company"
- "we're not looking"
- "leave me alone"
- "no need"

---

### UNSUBSCRIBE Keywords (🚫 Unsubscribe)
- "unsubscribe"
- "remove me"
- "stop emailing/contacting"
- "opt out"
- "take me off"
- "do not contact"

---

## Troubleshooting

### Issue: Reply not appearing in inbox
**Solution**:
1. Wait 2-3 minutes (polling interval)
2. Refresh inbox page (Ctrl+R)
3. Check backend logs: `docker-compose logs -f backend | grep reply`
4. Verify email was actually sent to the test address

### Issue: Classification shows NEUTRAL instead of expected
**Solution**:
1. Check exact wording - keywords are case-insensitive but must match pattern
2. Verify keyword is in message (not quoted from previous email)
3. Look at body in inbox - may be showing cleaned version
4. Try exact phrase from table above

### Issue: Reply visible but tally not updating
**Solution**:
1. Reload dashboard page
2. Check that campaign is running (not paused)
3. Verify reply is for correct campaign_lead
4. Check database: `SELECT COUNT(*) FROM messages WHERE direction='INBOUND';`

### Issue: Multiple replies showing as separate conversations
**Solution**:
1. All replies should be under same "conversation"
2. If showing separately, check gmail_thread_id is same
3. Verify backend logs for thread detection

---

## Success Criteria

✅ All 4 test cases pass  
✅ Replies classified correctly  
✅ Dashboard tally accurate  
✅ Multi-reply threads work  
✅ Manual override works  
✅ Inbox displays properly  
✅ No database errors in logs  

---

## Quick Test Command Reference

```bash
# Clear inbox again if needed
docker-compose exec backend python clear_inbox.py

# Check recent messages in database
docker-compose exec db psql -U postgres outreach -c "SELECT id, direction, body, classification, received_at FROM messages ORDER BY received_at DESC LIMIT 10;"

# Watch backend logs during testing
docker-compose logs -f backend | grep -i "reply\|classify\|poll"

# Check celery worker for polling tasks
docker-compose logs -f celery_worker | grep -i "poll"
```

---

## Timeline

- **0:00** - Create campaign & send emails
- **0:30** - Reply from test email #1 (BOOKING_INTENT)
- **3:00** - Check inbox (polling ran at ~2 min)
- **3:30** - Reply from test email #2 (NEGATIVE)
- **6:00** - Check inbox again
- **6:30** - Reply from test email #3 (UNSUBSCRIBE)
- **9:00** - Final inbox check, verify all 3 showing correctly

---

## Next Steps After Testing

If all tests pass:
1. Test with real campaigns
2. Monitor interest classification accuracy
3. Adjust keyword patterns if needed
4. Train team on interpreting classifications
5. Use BOOKING_INTENT replies for follow-ups

If issues found:
1. Document the issue
2. Check logs
3. Update keyword patterns as needed
4. Re-test affected classification

