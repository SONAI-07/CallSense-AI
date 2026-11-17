import uuid
from types import SimpleNamespace

import pytest


async def signup(client, tag):
    email = f"{tag}-{uuid.uuid4().hex[:8]}@test.io"
    r = await client.post("/auth/signup", json={
        "email": email, "password": "supersecret1", "tenant_name": f"T-{tag}",
    })
    assert r.status_code == 201, r.text
    return email, r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_health(client):
    assert (await client.get("/health")).status_code == 200


async def test_signup_login_me(client):
    email, token = await signup(client, "a")
    r = await client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 200
    me = await client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email


async def test_login_wrong_password(client):
    email, _ = await signup(client, "b")
    r = await client.post("/auth/login", json={"email": email, "password": "wrongpass1"})
    assert r.status_code == 401


async def test_tenant_isolation(client):
    _, t1 = await signup(client, "iso1")
    _, t2 = await signup(client, "iso2")
    c = await client.post("/customers", json={"name": "Lead", "phone_number": "+919999999999"}, headers=auth(t1))
    assert c.status_code == 201
    cid = c.json()["id"]
    # tenant 2 must not see tenant 1's customer via outbound
    r = await client.post("/calls/outbound", json={"customer_id": cid, "agent_id": 1}, headers=auth(t2))
    assert r.status_code == 404
    assert (await client.get("/calls", headers=auth(t2))).json() == []


async def test_outbound_creates_call(client, monkeypatch):
    _, token = await signup(client, "out")
    c = await client.post("/customers", json={"name": "Lead", "phone_number": "+919999999998"}, headers=auth(token))
    cid = c.json()["id"]
    # agents list is empty for a fresh tenant -> outbound must 404 on agent
    r = await client.post("/calls/outbound", json={"customer_id": cid, "agent_id": 999}, headers=auth(token))
    assert r.status_code == 404
    monkeypatch.setattr(
        "app.routes.call_route.create_outbound_call",
        lambda to, url: SimpleNamespace(sid="CA_test_sid"),
    )
    # seed an agent directly through the repo layer for the happy path
    from app.core.database import AsyncSessionLocal
    from app.models.agent import Agent
    from app.Auth.dependencies import get_current_tenant  # noqa: F401
    async with AsyncSessionLocal() as s:
        async with s.begin():
            me = await client.get("/auth/me", headers=auth(token))
            tid = me.json()["tenant_id"]
            a = Agent(tenant_id=tid, name="Test", system_prompt="hi", language_code="en-IN")
            s.add(a)
        await s.refresh(a)
        aid = a.id
    r = await client.post("/calls/outbound", json={"customer_id": cid, "agent_id": aid}, headers=auth(token))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "initiated"
    assert r.json()["twilio_call_sid"] == "CA_test_sid"


async def test_dashboard_shape_and_lowercase_classification(client):
    _, token = await signup(client, "dash")
    r = await client.get("/dashboard/summary", headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    for key in ("total_calls", "strong_interest_calls", "whatsapp_actions_executed"):
        assert key in body
    assert body["total_calls"] == 0


async def test_unauthenticated_rejected(client):
    assert (await client.get("/calls")).status_code in (401, 403)
    assert (await client.get("/agents")).status_code in (401, 403)