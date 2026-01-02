# Google Cloud Project Setup Guide

This guide walks you through setting up Google Cloud for the Email Outreach Platform.

## 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name: `email-outreach-platform`
4. Click **Create**
5. Wait for project creation, then select it

## 2. Enable Required APIs

1. Go to **APIs & Services** → **Library**
2. Search and enable each:
   - **Gmail API** → Click **Enable**
   - **Google Calendar API** → Click **Enable**

## 3. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (or Internal if using Google Workspace)
3. Click **Create**
4. Fill in required fields:
   - **App name**: `Email Outreach Platform`
   - **User support email**: Your email
   - **Developer contact**: Your email
5. Click **Save and Continue**
6. Add scopes → **Add or Remove Scopes**:
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar.events`
7. Click **Save and Continue**
8. Add test users (your Gmail addresses)
9. Click **Save and Continue**

## 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Web application**
4. Name: `Email Outreach Web Client`
5. Add **Authorized redirect URIs**:
   - Development: `http://localhost:8000/api/mailboxes/oauth/callback`
   - Production: `https://yourdomain.com/api/mailboxes/oauth/callback`
6. Click **Create**
7. **Download JSON** or copy:
   - Client ID
   - Client Secret

## 5. Store Credentials Securely

Add to your `.env` file:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/mailboxes/oauth/callback
```

> **SECURITY**: Never commit `.env` to version control. Add it to `.gitignore`.

## 6. Production Verification (Optional)

For production with >100 users:
1. Go to **OAuth consent screen**
2. Click **Publish App**
3. Complete Google's verification process

For testing/internal use, test users mode is sufficient.

---

## Quick Reference

| Item | Value |
|------|-------|
| Gmail Scopes | `gmail.send`, `gmail.readonly`, `gmail.modify` |
| Calendar Scope | `calendar.events` |
| Redirect URI (dev) | `http://localhost:8000/api/mailboxes/oauth/callback` |
