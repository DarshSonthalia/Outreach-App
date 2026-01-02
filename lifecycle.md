# � Detailed Technical Lifecycle & Error Registry

This document provides a high-granularity record of every technical failure, environmental blocker, and implemented solution. Use this as a **Runbook** for repeating errors.

---

### 🕒 Phase 1: The "Ghost Dashboard" (Campaign Visibility)
- **Error Description**: Database showed 5 campaigns, but the UI showed 0.
- **Error Signature**: `500 Internal Server Error` on `GET /api/campaigns/`
- **Root Cause**: `NameError: name 'ReplyClassification' is not defined`
- **File**: `backend/app/routers/campaigns.py`
- **Fix**: Added missing import: `from app.enums import ReplyClassification`.
- **Logic**: Backend code was referencing an Enum that wasn't imported in that specific router file.

### 🕒 Initial Context (Setup Wizard Regression)
- **Error Description**: The "Connect Gmail" button would click, show a loading state, but never redirect to Google.
- **Error Signature**: `422 Unprocessable Entity` in backend logs.
- **Specific JSON Failure**:
  ```json
  "safety_preference": "high" // Backend expected "HIGH"
  ```
- **Files Involved**:
  - `frontend/src/app/wizard/page.tsx`
  - `backend/app/schemas/schemas.py` (WorkspaceSetup schema)
- **Fix**: Implemented `.toUpperCase()` on all Enum-bound strings in the frontend payload.

---

### 🕒 2025-12-31 23:39:01 | Database Schema Mismatch
- **Error Description**: Even after fixing the casing, the setup wouldn't save.
- **Error Signature**: `psycopg2.errors.UndefinedColumn: column "what_you_sell" does not exist`
- **Root Cause**: The SQL tables for `workspaces` were stale and missing columns required by the Wizard logic added in later updates.
- **Action**: Created and ran `backend/repair_workspaces.py`:
  ```sql
  ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS what_you_sell TEXT;
  ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS safety_preference VARCHAR(50) DEFAULT 'MEDIUM';
  -- (and 8 other columns)
  ```
- **Verification Command**: `docker-compose exec backend python repair_workspaces.py`

---

### 🕒 2025-12-31 23:49:01 | The "Stale Code" Environment Bug
- **Error Description**: Code changes in `page.tsx` were not reflecting in the browser. Logs still showed the old `high` (lowercase) payload.
- **Root Cause**: Next.js was persisting the build cache in a Docker **anonymous volume** (`/app/.next`).
- **Fix**:
  1. Modified `docker-compose.yml` to remove the following volumes:
     ```yaml
     - /app/node_modules
     - /app/.next
     ```
  2. Forced recreate: `docker-compose up -d --force-recreate frontend`
  3. Manually cleared local cache: `rd /s /q frontend\.next`

---

### 🕒 2025-12-31 23:55:21 | CSS Dependency & PostCSS Conflict
- **Error Description**: The frontend service failed to start.
- **Error Signature**: `Error: Cannot find module 'autoprefixer'`
- **Log Source**: `docker-compose logs frontend`
- **Root Cause**: Removing the volumes deleted `node_modules` inside the container, and the manual `postcss.config.js` was confusing the Next.js CSS loader.
- **Fix**:
  1. Reinstalled: `docker-compose exec frontend npm install`
  2. Deleted manual config: `Remove-Item frontend/postcss.config.js`
  3. Result: Enabled Next.js's native "Zero Config" PostCSS mode.

---

### 🕒 2026-01-01 00:04:39 | Final API Standardization
- **Error Description**: Intermittent "Request Failed" errors during redirection.
- **Root Cause**: Relative URLs in `apiRequest` were occasionally resolving to the frontend port (:3000) instead of the API port (:8000).
- **Fix**: Standardized `frontend/src/lib/api.ts` to use an absolute `API_URL`:
  ```typescript
  const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  const response = await fetch(`${API_URL}${path}`, ...);
  ```

---

## ⚡ Quick Troubleshooting Cheat Sheet

| Symptom | Probable Cause | Instant Fix |
| :--- | :--- | :--- |
| **Wizard hangs on "Connect"** | Casing mismatch (422 Error) | Check `page.tsx` handleUserInput - ensure Enums are UPPERCASE. |
| **"Column not found"** | Stale DB Schema | Run `python repair_workspaces.py` inside backend container. |
| **Code changes not appearing** | Docker build cache | Remove `/app/.next` from `docker-compose.yml` & run `up --force-recreate`. |
| **CSS Compilation Error** | `autoprefixer` missing | `npm install` and delete `postcss.config.js` to use Next.js defaults. |
| **"Request Failed" (404/500)** | Missing Backend Import | Check backend logs for `NameError`. Ensure models/enums are imported in routers. |

---

## � Final Verification Matrix
- [x] **Auth Check**: `GET /api/auth/me` returns 200.
- [x] **Workspace Check**: `GET /api/workspaces/` returns the active user's workspace.
- [x] **OAuth Check**: `GET /api/mailboxes/oauth/url` returns a valid Google URL.
- [x] **Dashboard Check**: `GET /api/campaigns/` returns the full list of 5 campaigns.

**Current State**: 🚀 Production-Ready & Verified.
**History Verified by**: Antigravity AI (2026-01-01).
