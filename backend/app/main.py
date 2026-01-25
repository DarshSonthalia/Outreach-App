"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from app.config import settings
from app.database import engine, Base
from app.routers import auth, workspaces, mailboxes, domains, leads, campaigns, inbox, booking, health, campaigns_ai, inbox_ai, campaign_leads


# Fix H4: Use Alembic migrations instead of create_all in production
# For development, you can uncomment this line:
# Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Email Outreach Platform",
    description="Safety-first email outreach with Gmail integration",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.body()
        body_str = body.decode()
    except:
        body_str = "<could not read body>"
        
    logger.error(f"Validation Error: {exc}")
    logger.error(f"Request Body: {body_str}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": body_str},
    )

def _normalize_origin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url

frontend_origin = _normalize_origin(settings.frontend_url)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=list({frontend_origin}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(mailboxes.router, prefix="/api/mailboxes", tags=["Mailboxes"])
app.include_router(domains.router, prefix="/api/domains", tags=["Domains"])
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(campaigns_ai.router)  # AI endpoints use their own prefix
app.include_router(inbox.router, prefix="/api/inbox", tags=["Inbox"])
app.include_router(inbox_ai.router)  # AI endpoints use their own prefix
app.include_router(booking.router, prefix="/api/booking", tags=["Booking"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(campaign_leads.router, prefix="/api/campaign_leads", tags=["CampaignLeads"])



@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
