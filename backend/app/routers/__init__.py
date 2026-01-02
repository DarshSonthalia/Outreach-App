"""
Routers package.
"""
from app.routers import auth, workspaces, mailboxes, domains, leads, campaigns, inbox, booking

__all__ = [
    "auth",
    "workspaces",
    "mailboxes",
    "domains",
    "leads",
    "campaigns",
    "inbox",
    "booking",
]
