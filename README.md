# Email Outreach Platform V1

A safety-first email outreach platform with Gmail integration.

## Features

- **Gmail Integration**: OAuth-based inbox connection
- **Domain Safety Checks**: SPF/DMARC validation
- **Lead Management**: CSV upload or website sourcing
- **Campaign Engine**: Scheduled sends with follow-ups
- **Safety Engine**: Daily limits, bounce detection, auto-pause
- **Reply Handling**: Automatic classification and send stopping
- **Calendly Integration**: Webhook for meeting bookings

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Google Cloud Project with Gmail API enabled (see [Google Cloud Setup](./docs/GOOGLE_CLOUD_SETUP.md))

### Setup

1. **Clone and configure**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Start services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the app**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Safety Defaults (Hardcoded)

| Setting | Value |
|---------|-------|
| Day 1 Limit | 10 emails |
| Day 2 Limit | 15 emails |
| Day 3 Limit | 20 emails |
| Day 4+ Limit | 25 emails |
| Hard Cap | 30 emails |
| Bounce Throttle | 2 in 24h |
| Bounce Pause | 4 in 24h |

## Project Structure

```
outreach-app/
├── backend/           # FastAPI + Celery
│   ├── app/
│   │   ├── routers/   # API endpoints
│   │   ├── services/  # Business logic
│   │   ├── workers/   # Celery tasks
│   │   └── models/    # SQLAlchemy models
│   └── Dockerfile
├── frontend/          # Next.js
│   └── src/app/       # Pages
├── docs/              # Documentation
└── docker-compose.yml
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register` | User signup |
| `POST /api/auth/login` | Login |
| `GET /api/mailboxes/oauth/url` | Gmail OAuth |
| `POST /api/leads/upload-csv` | Upload leads |
| `POST /api/campaigns` | Create campaign |
| `POST /api/campaigns/{id}/launch` | Launch |
| `GET /api/campaigns/{id}/dashboard` | Stats |
| `GET /api/inbox/replies` | View replies |

## Safety Philosophy

- Emails are sent gradually (never bulk)
- Replies automatically stop follow-ups
- Unsubscribes are permanently blocked
- Bounce spikes pause campaigns
- All actions are logged and explainable
