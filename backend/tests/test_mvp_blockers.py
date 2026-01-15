import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import hmac
import hashlib

from fastapi import HTTPException

from app.routers.booking import calendly_webhook
from app.models import BookingEvent, Lead, Message, CampaignLead, Campaign, Domain
from app.enums import FollowupState, CancelReason, CampaignStatus
from app.routers import health as health_router
from app.workers.campaign_worker import process_single_send


class QueryMock:
    def __init__(self, result=None, list_result=None):
        self._result = result
        self._list_result = list_result or []

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._list_result


class FakeRequest:
    def __init__(self, body_bytes, json_data):
        self._body = body_bytes
        self._json = json_data

    async def body(self):
        return self._body

    async def json(self):
        return self._json


@pytest.mark.asyncio
async def test_calendly_webhook_invalid_signature_returns_401(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "calendly_webhook_secret", "test_secret")

    request = FakeRequest(b'{"event":"invitee.created","payload":{}}', {"event": "invitee.created", "payload": {}})
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await calendly_webhook(request=request, db=db, calendly_webhook_signature="bad")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_calendly_webhook_duplicate_uuid_noop(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "calendly_webhook_secret", "test_secret")

    payload = {"event": "invitee.created", "payload": {"event": {"uuid": "abc"}, "invitee": {"email": "a@b.com"}}}
    body = b'{"event":"invitee.created","payload":{"event":{"uuid":"abc"}}}'
    request = FakeRequest(body, payload)
    signature = hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    booking_query = QueryMock(result=BookingEvent())
    db = MagicMock()
    db.query.side_effect = lambda model: booking_query if model is BookingEvent else QueryMock()

    resp = await calendly_webhook(request=request, db=db, calendly_webhook_signature=f"v1,{signature}")
    assert resp["status"] == "ok"
    assert resp["message"] == "duplicate event ignored"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_calendly_webhook_booking_cancels_followups_and_logs(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "calendly_webhook_secret", "test_secret")

    payload = {
        "event": "invitee.created",
        "payload": {
            "event": {"uuid": "evt-123"},
            "invitee": {"email": "lead@example.com"}
        }
    }
    import json
    body = json.dumps(payload).encode("utf-8")
    request = FakeRequest(body, payload)
    signature = hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    lead = SimpleNamespace(id=1, workspace_id=2, email="lead@example.com")
    campaign = SimpleNamespace(id=10, mailbox_id=3, status=CampaignStatus.RUNNING)
    campaign_lead = SimpleNamespace(id=99, campaign=campaign)

    db = MagicMock()
    db.query.side_effect = lambda model: (
        QueryMock(result=None) if model is BookingEvent else
        QueryMock(result=lead) if model is Lead else
        QueryMock(result=None) if model is Message else
        QueryMock(list_result=[campaign_lead]) if model is CampaignLead else
        QueryMock()
    )

    with patch("app.routers.booking.FollowupService.cancel_followups") as cancel_followups:
        resp = await calendly_webhook(request=request, db=db, calendly_webhook_signature=f"v1,{signature}")
        assert resp["status"] == "ok"
        cancel_followups.assert_called_with(db, campaign_lead.id, CancelReason.BOOKED, "Calendly booking confirmed: evt-123")
        added_events = [call.args[0] for call in db.add.call_args_list if hasattr(call.args[0], "action")]
        assert any(evt.action == "BOOKING_CONFIRMED" for evt in added_events)


@pytest.mark.asyncio
async def test_launch_blocked_when_domain_invalid():
    from app.routers.campaigns import launch_campaign

    mailbox = SimpleNamespace(email="user@bad.com", is_active=True, workspace_id=1)
    campaign = SimpleNamespace(
        id=1,
        name="Test",
        status=CampaignStatus.DRAFT,
        subject="Hello",
        body="Body",
        mailbox=mailbox,
        mailbox_id=1,
        workspace_id=1
    )
    domain = SimpleNamespace(domain="bad.com", spf_valid=False, dmarc_valid=True, spf_record=None, dmarc_record=None)

    db = MagicMock()
    db.query.side_effect = lambda model: (
        QueryMock(result=campaign) if model is Campaign else
        QueryMock(result=domain) if model is Domain else
        QueryMock()
    )

    with pytest.raises(HTTPException) as exc:
        await launch_campaign(campaign_id=1, current_user=SimpleNamespace(id=1), db=db)

    assert exc.value.status_code == 400


def test_health_celery_no_workers(monkeypatch):
    class InspectMock:
        def __init__(self, app=None):
            pass

        def active(self):
            return None

        def scheduled(self):
            return None

        def registered(self):
            return None

    monkeypatch.setattr(health_router, "Inspect", InspectMock)
    resp = health_router.celery_health()
    assert resp["status"] == "no_workers"
    assert resp["workers_active"] == 0


def test_worker_blocks_send_when_followups_cancelled():
    campaign_lead = SimpleNamespace(
        id=1,
        followup_state=FollowupState.CANCELLED,
        cancel_reason=CancelReason.BOUNCE
    )

    db = MagicMock()
    db.refresh = MagicMock()
    db.add = MagicMock()

    with patch("app.workers.campaign_worker.GmailService.send_email") as send_email:
        process_single_send(db, campaign_lead)
        send_email.assert_not_called()
        db.add.assert_called()
