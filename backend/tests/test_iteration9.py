"""BarterGrid iteration-9 targeted tests — Resend email delivery pipeline.

Covers:
 1. email_queue rows transition out of 'pending' (sent w/ provider_id OR failed w/ error) => _deliver_email fired
 2. All kinds queued: trade_proposal, trade_update, meetup_planned, trade_completed, direct_message, trade_message
 3. Preference suppression: email_notifications=false and kind-specific prefs -> NO row + NO delivery
 4. Deleted user (deleted-<uid>@bartergrid.local) -> NO row, NO delivery attempt
 5. No 500s across the flows exercised here
"""
import os
import time
import uuid

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/") + "/api"

MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")
RESEND_KEY = os.environ.get("RESEND_API_KEY") or backend_env.get("RESEND_API_KEY")

PW = "Passw0rd!23"
T = 30


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


# ---------------- helpers ----------------
def _signup(display_name="TEST_i9 User"):
    email = f"TEST_i9_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE}/auth/signup",
                      json={"email": email, "password": PW, "display_name": display_name}, timeout=T)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "name": display_name, "h": {"Authorization": f"Bearer {d['token']}"}}


def _listing(u, title):
    r = requests.post(f"{BASE}/listings", headers=u["h"], json={
        "kind": "have", "title": title, "description": "TEST_ i9",
        "category": "tools", "wants": ["anything"], "tags": ["testi9"]}, timeout=T)
    assert r.status_code == 200, f"listing failed {r.status_code} {r.text[:300]}"
    return r.json()["listing_id"]


def _trade(a, b, la, lb):
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la,
        "their_listing_id": lb, "message": "TEST_i9 offer"}, timeout=T)
    assert r.status_code == 200, f"trade failed {r.status_code} {r.text[:300]}"
    return r.json()["trade_id"]


def _rows(mdb, user_id, kind=None):
    q = {"user_id": user_id}
    if kind:
        q["kind"] = kind
    return list(mdb.email_queue.find(q, {"_id": 0}))


def _wait_resolved(mdb, user_id, kind, timeout=12):
    """Wait for the newest row of `kind` to leave 'pending'."""
    deadline = time.time() + timeout
    row = None
    while time.time() < deadline:
        rows = _rows(mdb, user_id, kind)
        if rows:
            row = rows[-1]
            if row["status"] != "pending":
                return row
        time.sleep(1)
    return row


def _cleanup(pairs):
    for u, lid in pairs:
        requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=T)


# ============ 1. delivery task actually fires on trade_proposal ============
def test_trade_proposal_email_delivered_or_failed(mdb):
    if not RESEND_KEY:
        pytest.skip("RESEND_API_KEY not configured")
    a = _signup("TEST_i9 Alice")
    b = _signup("TEST_i9 Bob")
    la, lb = _listing(a, "TEST_i9 Hammer"), _listing(b, "TEST_i9 Wrench")
    tid = _trade(a, b, la, lb)

    row = _wait_resolved(mdb, b["user_id"], "trade_proposal")
    assert row is not None, "no trade_proposal email_queue row created for Bob"
    assert row["to_email"] == b["email"]
    assert row["data"].get("trade_id") == tid
    assert row["status"] in ("sent", "failed"), \
        f"row still pending after 12s -> _deliver_email never fired: {row}"
    if row["status"] == "sent":
        assert row.get("provider_id"), f"sent row missing provider_id: {row}"
        assert row.get("sent_at")
    else:
        assert row.get("error"), f"failed row missing error: {row}"
        assert row.get("failed_at")
    _cleanup([(a, la), (b, lb)])


# ============ 2. all kinds queued + resolved across a full trade lifecycle ============
def test_all_email_kinds_queued_and_resolved(mdb):
    a = _signup("TEST_i9 Kinds A")
    b = _signup("TEST_i9 Kinds B")
    la, lb = _listing(a, "TEST_i9 Drill"), _listing(b, "TEST_i9 Saw")

    # direct_message -> b
    rdm = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                        headers=a["h"], json={"text": "TEST_i9 hi"}, timeout=T)
    assert rdm.status_code == 200, rdm.text[:300]

    tid = _trade(a, b, la, lb)  # trade_proposal -> b

    # trade_update -> a (accept by b)
    ra = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"],
                       params={"action": "accept"}, timeout=T)
    assert ra.status_code == 200, ra.text[:300]

    # meetup_planned -> b
    rm = requests.post(f"{BASE}/trades/{tid}/meetup", headers=a["h"], json={
        "location_name": "TEST_i9 Library", "date": "2026-09-01", "time": "10:00"}, timeout=T)
    assert rm.status_code == 200, rm.text[:300]

    # trade_message -> b
    rtm = requests.post(f"{BASE}/trades/{tid}/messages", headers=a["h"],
                        json={"text": "TEST_i9 see you"}, timeout=T)
    assert rtm.status_code == 200, rtm.text[:300]

    # trade_completed -> both (both sides complete)
    assert requests.post(f"{BASE}/trades/{tid}/action", headers=a["h"],
                         params={"action": "complete"}, timeout=T).status_code == 200
    fin = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"],
                        params={"action": "complete"}, timeout=T)
    assert fin.status_code == 200, fin.text[:300]

    expected = {
        b["user_id"]: ["direct_message", "trade_proposal", "meetup_planned",
                       "trade_message", "trade_completed"],
        a["user_id"]: ["trade_update", "trade_completed"],
    }
    unresolved = []
    for uid, kinds in expected.items():
        for k in kinds:
            row = _wait_resolved(mdb, uid, k)
            assert row is not None, f"missing email_queue row kind={k} for {uid}"
            if row["status"] == "pending":
                unresolved.append((uid, k))
            elif row["status"] == "sent":
                assert row.get("provider_id"), f"sent row missing provider_id: {row}"
            else:
                assert row.get("error"), f"failed row missing error: {row}"
    assert not unresolved, f"rows never left pending (delivery task did not fire): {unresolved}"
    _cleanup([(a, la), (b, lb)])


# ============ 3. suppression: email_notifications=false -> no row at all ============
def test_email_notifications_false_creates_no_row(mdb):
    a = _signup("TEST_i9 Sender")
    b = _signup("TEST_i9 OptOut")
    assert requests.patch(f"{BASE}/profile", headers=b["h"],
                          json={"email_notifications": False}, timeout=T).status_code == 200

    rdm = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                        headers=a["h"], json={"text": "TEST_i9 suppressed"}, timeout=T)
    assert rdm.status_code == 200, rdm.text[:300]
    la, lb = _listing(a, "TEST_i9 S1"), _listing(b, "TEST_i9 S2")
    _trade(a, b, la, lb)

    time.sleep(3)
    rows = _rows(mdb, b["user_id"])
    assert rows == [], f"email_queue rows created despite email_notifications=false: {rows}"
    _cleanup([(a, la), (b, lb)])


# ============ 3b. kind-specific pref: notify_trades=false blocks trade emails only ============
def test_kind_specific_pref_suppression(mdb):
    a = _signup("TEST_i9 KSender")
    b = _signup("TEST_i9 NoTrades")
    assert requests.patch(f"{BASE}/profile", headers=b["h"],
                          json={"notify_trades": False}, timeout=T).status_code == 200

    la, lb = _listing(a, "TEST_i9 K1"), _listing(b, "TEST_i9 K2")
    _trade(a, b, la, lb)
    rdm = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                        headers=a["h"], json={"text": "TEST_i9 dm allowed"}, timeout=T)
    assert rdm.status_code == 200, rdm.text[:300]

    time.sleep(3)
    assert _rows(mdb, b["user_id"], "trade_proposal") == [], \
        "trade_proposal email queued despite notify_trades=false"
    dm = _rows(mdb, b["user_id"], "direct_message")
    assert dm, "direct_message email should still be queued when only notify_trades is false"
    _cleanup([(a, la), (b, lb)])


# ============ 4. deleted user -> no row, no delivery attempt ============
def test_deleted_user_no_email_queued(mdb):
    a = _signup("TEST_i9 DelSender")
    b = _signup("TEST_i9 ToDelete")
    la, lb = _listing(a, "TEST_i9 D1"), _listing(b, "TEST_i9 D2")

    assert requests.delete(f"{BASE}/account", headers=b["h"], timeout=T).status_code == 200
    doc = mdb.users.find_one({"user_id": b["user_id"]}, {"_id": 0, "email": 1, "role": 1})
    assert doc["email"] == f"deleted-{b['user_id']}@bartergrid.local", doc
    before = len(_rows(mdb, b["user_id"]))

    # sender still tries to reach the deleted user
    requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                  headers=a["h"], json={"text": "TEST_i9 to deleted"}, timeout=T)
    requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la,
        "their_listing_id": lb, "message": "TEST_i9 to deleted"}, timeout=T)

    time.sleep(3)
    after = _rows(mdb, b["user_id"])
    assert len(after) == before, f"email_queue rows created for deleted user: {after}"
    assert not [r for r in after if r["status"] == "failed"], \
        f"failed delivery rows exist for deleted user: {after}"
    _cleanup([(a, la)])


# ============ 4b. happy path: Resend sandbox recipient => status 'sent' + provider_id ============
def test_resend_sandbox_recipient_marked_sent(mdb):
    if not RESEND_KEY:
        pytest.skip("RESEND_API_KEY not configured")
    a = _signup("TEST_i9 SendA")
    email = f"delivered+{uuid.uuid4().hex[:8]}@resend.dev"
    r = requests.post(f"{BASE}/auth/signup",
                      json={"email": email, "password": PW, "display_name": "TEST_i9 SendB"}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    b_uid = r.json()["user"]["user_id"]

    rdm = requests.post(f"{BASE}/conversations/{b_uid}/messages", headers=a["h"],
                        json={"text": "TEST_i9 sandbox delivery"}, timeout=T)
    assert rdm.status_code == 200, rdm.text[:300]

    row = _wait_resolved(mdb, b_uid, "direct_message")
    assert row is not None, "no direct_message row created"
    assert row["status"] == "sent", f"expected 'sent' for Resend sandbox recipient, got {row}"
    assert row.get("provider_id"), f"sent row missing provider_id: {row}"


# ============ 5. no stuck-pending backlog / sanity on the whole collection ============
def test_no_bartergrid_local_recipients_in_queue(mdb):
    bad = list(mdb.email_queue.find({"to_email": {"$regex": "@bartergrid.local$"}}, {"_id": 0}))
    assert bad == [], f"queue contains @bartergrid.local recipients: {bad[:3]}"


def test_recent_rows_are_resolved(mdb):
    """Every row created in this session's kinds should be resolved, not left pending forever."""
    if not RESEND_KEY:
        pytest.skip("RESEND_API_KEY not configured")
    recent = list(mdb.email_queue.find({"to_email": {"$regex": "^test_i9_"}}, {"_id": 0}))
    assert recent, "no TEST_i9 rows found — earlier tests may not have run"
    stuck = [r for r in recent if r["status"] == "pending"]
    assert not stuck, f"{len(stuck)}/{len(recent)} TEST_i9 rows stuck in pending: {stuck[:3]}"
