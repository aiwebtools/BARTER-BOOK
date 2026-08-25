"""BarterGrid iteration-7 targeted regression tests.

Covers the 3 fixes applied on top of iteration 6:
 1. IN-APP notification preferences honoured via _add_notification for all 6 insertion sites
    (trade_proposal, trade action updates, meetup, trade chat message, DM, rating_request)
 2. DM validation happens BEFORE the conversation upsert (422 leaves no dirty write)
 3. DM conversations.last_message is stored stripped
Plus: referral_verified notifications are unconditional.
"""
import os
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

PW = "Passw0rd!23"
T = 30


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


# ---------------- helpers ----------------
def _signup(display_name="TEST_i7 User", referral_code=None):
    email = f"TEST_i7_{uuid.uuid4().hex[:10]}@example.com"
    payload = {"email": email, "password": PW, "display_name": display_name}
    if referral_code:
        payload["referral_code"] = referral_code
    r = requests.post(f"{BASE}/auth/signup", json=payload, timeout=T)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "user": d["user"], "h": {"Authorization": f"Bearer {d['token']}"}}


def _prefs(u, **kw):
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json=kw, timeout=T)
    assert r.status_code == 200, f"prefs patch failed {r.status_code} {r.text[:300]}"
    return r.json()


def _listing(u, title, **extra):
    payload = {"kind": "have", "title": title, "description": "TEST_ i7",
               "category": "home", "wants": ["anything"], "tags": ["test"]}
    payload.update(extra)
    r = requests.post(f"{BASE}/listings", headers=u["h"], json=payload, timeout=T)
    assert r.status_code == 200, f"listing failed {r.status_code} {r.text[:300]}"
    return r.json()["listing_id"]


def _trade(a, b, la, lb, msg="TEST_i7 offer"):
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la,
        "their_listing_id": lb, "message": msg}, timeout=T)
    assert r.status_code == 200, f"trade failed {r.status_code} {r.text[:300]}"
    return r.json()["trade_id"]


def _notifs(u):
    r = requests.get(f"{BASE}/notifications", headers=u["h"], timeout=T)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def _types(u):
    return [n["type"] for n in _notifs(u)]


def _cleanup(pairs):
    for u, lid in pairs:
        requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=T)


# ============ 1. notify_messages=false suppresses DM + trade chat in-app ============
def test_notify_messages_false_suppresses_dm_and_trade_chat(mdb):
    sender = _signup("TEST_i7 Sender")
    rec = _signup("TEST_i7 MutedMsgs")
    _prefs(rec, notify_messages=False)

    # DM
    r = requests.post(f"{BASE}/conversations/{rec['user_id']}/messages",
                      headers=sender["h"], json={"text": "TEST_i7 muted dm"}, timeout=T)
    assert r.status_code == 200, r.text[:300]

    # trade chat (needs a trade; notify_trades left true so proposal notif is expected)
    la = _listing(sender, "TEST_i7 Kettle")
    lb = _listing(rec, "TEST_i7 Mug")
    tid = _trade(sender, rec, la, lb)
    rm = requests.post(f"{BASE}/trades/{tid}/messages", headers=sender["h"],
                       json={"text": "TEST_i7 muted trade chat"}, timeout=T)
    assert rm.status_code == 200, rm.text[:300]

    ns = _notifs(rec)
    msg_notifs = [n for n in ns if n["type"] == "message"]
    assert msg_notifs == [], f"message notifications created despite notify_messages=false: {msg_notifs}"
    # email also skipped for both message kinds
    assert mdb.email_queue.count_documents(
        {"user_id": rec["user_id"], "kind": {"$in": ["direct_message", "trade_message"]}}) == 0, \
        "message email queued despite notify_messages=false"
    # sanity: trade_proposal notification still present (notify_trades untouched)
    assert any(n["type"] == "trade_proposal" for n in ns), \
        f"notify_messages=false wrongly suppressed trade_proposal: {ns}"

    # flip back on -> both appear again
    _prefs(rec, notify_messages=True)
    r2 = requests.post(f"{BASE}/conversations/{rec['user_id']}/messages",
                       headers=sender["h"], json={"text": "TEST_i7 unmuted dm"}, timeout=T)
    assert r2.status_code == 200, r2.text[:300]
    rm2 = requests.post(f"{BASE}/trades/{tid}/messages", headers=sender["h"],
                        json={"text": "TEST_i7 unmuted trade chat"}, timeout=T)
    assert rm2.status_code == 200, rm2.text[:300]

    ns2 = _notifs(rec)
    assert any("TEST_i7 unmuted dm" in n["text"] for n in ns2), f"DM notif missing after re-enable: {ns2}"
    assert any("TEST_i7 unmuted trade chat" in n["text"] for n in ns2), \
        f"trade chat notif missing after re-enable: {ns2}"
    assert mdb.email_queue.count_documents(
        {"user_id": rec["user_id"], "kind": "direct_message"}) >= 1
    assert mdb.email_queue.count_documents(
        {"user_id": rec["user_id"], "kind": "trade_message"}) >= 1
    _cleanup([(sender, la), (rec, lb)])


# ============ 2. notify_trades=false suppresses proposal/actions/meetup/rating ============
def test_notify_trades_false_suppresses_all_trade_notifs(mdb):
    a = _signup("TEST_i7 Prop")        # muted party
    b = _signup("TEST_i7 Recv")
    _prefs(a, notify_trades=False)
    _prefs(b, notify_trades=False)

    la = _listing(a, "TEST_i7 Bike")
    lb = _listing(b, "TEST_i7 Helmet")

    # proposal -> notifies b
    tid = _trade(a, b, la, lb)
    assert not [n for n in _notifs(b) if n["type"] in ("trade_proposal", "trade")], \
        f"trade_proposal notif despite notify_trades=false: {_notifs(b)}"

    # accept -> notifies a
    ra = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"],
                       params={"action": "accept"}, timeout=T)
    assert ra.status_code == 200, ra.text[:300]
    assert not [n for n in _notifs(a) if n["type"] in ("trade", "trade_proposal")], \
        f"trade accept notif despite notify_trades=false: {_notifs(a)}"

    # meetup -> notifies b
    rmt = requests.post(f"{BASE}/trades/{tid}/meetup", headers=a["h"], json={
        "location_name": "TEST_i7 Park", "date": "2026-08-01", "time": "10:00"}, timeout=T)
    assert rmt.status_code == 200, rmt.text[:300]
    assert not [n for n in _notifs(b) if n["type"] == "meetup"], \
        f"meetup notif despite notify_trades=false: {_notifs(b)}"

    # complete both sides -> rating_request for both
    for u in (a, b):
        rc = requests.post(f"{BASE}/trades/{tid}/action", headers=u["h"],
                           params={"action": "complete"}, timeout=T)
        assert rc.status_code == 200, rc.text[:300]
    for u, who in ((a, "proposer"), (b, "recipient")):
        assert not [n for n in _notifs(u) if n["type"] == "rating_request"], \
            f"rating_request notif for {who} despite notify_trades=false: {_notifs(u)}"

    # emails also suppressed
    assert mdb.email_queue.count_documents({"user_id": b["user_id"], "kind": "trade_proposal"}) == 0
    assert mdb.email_queue.count_documents({"user_id": b["user_id"], "kind": "meetup_planned"}) == 0
    _cleanup([(a, la), (b, lb)])


def test_notify_trades_true_all_trade_notifs_appear():
    a = _signup("TEST_i7 PropOn")
    b = _signup("TEST_i7 RecvOn")
    _prefs(a, notify_trades=True)
    _prefs(b, notify_trades=True)
    la = _listing(a, "TEST_i7 Guitar")
    lb = _listing(b, "TEST_i7 Amp")

    tid = _trade(a, b, la, lb)
    assert "trade_proposal" in _types(b), f"missing trade_proposal: {_notifs(b)}"

    assert requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"],
                         params={"action": "accept"}, timeout=T).status_code == 200
    assert "trade" in _types(a), f"missing trade accept notif: {_notifs(a)}"

    assert requests.post(f"{BASE}/trades/{tid}/meetup", headers=a["h"], json={
        "location_name": "TEST_i7 Cafe", "date": "2026-08-02",
        "time": "11:00"}, timeout=T).status_code == 200
    assert "meetup" in _types(b), f"missing meetup notif: {_notifs(b)}"

    for u in (a, b):
        assert requests.post(f"{BASE}/trades/{tid}/action", headers=u["h"],
                             params={"action": "complete"}, timeout=T).status_code == 200
    assert "rating_request" in _types(a), f"missing rating_request for a: {_notifs(a)}"
    assert "rating_request" in _types(b), f"missing rating_request for b: {_notifs(b)}"
    _cleanup([(a, la), (b, lb)])


def test_decline_notif_suppressed_then_delivered():
    """decline path of trade_action honours notify_trades both ways."""
    a = _signup("TEST_i7 DeclProp")
    b = _signup("TEST_i7 Decliner")
    _prefs(a, notify_trades=False)
    la = _listing(a, "TEST_i7 Skis")
    lb = _listing(b, "TEST_i7 Boots")
    tid = _trade(a, b, la, lb)
    assert requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"],
                         params={"action": "decline"}, timeout=T).status_code == 200
    assert not [n for n in _notifs(a) if n["type"] == "trade"], \
        f"decline notif despite notify_trades=false: {_notifs(a)}"

    # re-enable and re-run with a fresh trade
    _prefs(a, notify_trades=True)
    tid2 = _trade(a, b, la, lb, "TEST_i7 offer2")
    assert requests.post(f"{BASE}/trades/{tid2}/action", headers=b["h"],
                         params={"action": "decline"}, timeout=T).status_code == 200
    assert any(n["type"] == "trade" and "declined" in n["text"] for n in _notifs(a)), \
        f"decline notif missing after re-enable: {_notifs(a)}"
    _cleanup([(a, la), (b, lb)])


# ============ 3. referral_verified is unconditional ============
def test_referral_verified_always_fires(mdb):
    referrer = _signup("TEST_i7 Referrer")
    code = requests.get(f"{BASE}/referrals/mine", headers=referrer["h"],
                        timeout=T).json()["referral_code"]
    referred = _signup("TEST_i7 Referred", referral_code=code)
    # mute EVERYTHING for both
    for u in (referrer, referred):
        _prefs(u, notify_trades=False, notify_messages=False, notify_matches=False)

    partner = referred  # trade between referred and referrer to trigger first-trade verification
    la = _listing(referrer, "TEST_i7 Tent")
    lb = _listing(partner, "TEST_i7 Stove")
    tid = _trade(referrer, partner, la, lb)
    assert requests.post(f"{BASE}/trades/{tid}/action", headers=partner["h"],
                         params={"action": "accept"}, timeout=T).status_code == 200
    for u in (referrer, partner):
        assert requests.post(f"{BASE}/trades/{tid}/action", headers=u["h"],
                             params={"action": "complete"}, timeout=T).status_code == 200

    for u, who in ((referrer, "referrer"), (referred, "referred")):
        assert "referral_verified" in _types(u), \
            f"referral_verified missing for {who} (must be unconditional): {_notifs(u)}"
    _cleanup([(referrer, la), (partner, lb)])


# ============ 4. DM 422 leaves no dirty write ============
def test_dm_blank_no_conversation_created(mdb):
    a = _signup("TEST_i7 BlankA")
    b = _signup("TEST_i7 BlankB")
    r = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                      headers=a["h"], json={"text": "   "}, timeout=T)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"
    conv = mdb.conversations.find_one({"participants": {"$all": [a["user_id"], b["user_id"]]}})
    assert conv is None, f"422 created a conversation row (dirty write): {conv}"
    assert mdb.dm_messages.count_documents({"user_id": a["user_id"]}) == 0
    assert requests.get(f"{BASE}/conversations", headers=a["h"], timeout=T).json() == []


def test_dm_blank_does_not_touch_existing_conversation(mdb):
    a = _signup("TEST_i7 DirtyA")
    b = _signup("TEST_i7 DirtyB")
    ok = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                       headers=a["h"], json={"text": "TEST_i7 first real msg"}, timeout=T)
    assert ok.status_code == 200, ok.text[:300]
    before = mdb.conversations.find_one(
        {"participants": {"$all": [a["user_id"], b["user_id"]]}}, {"_id": 0})
    assert before and before["last_message"] == "TEST_i7 first real msg"

    bad = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                        headers=a["h"], json={"text": "  \t \n "}, timeout=T)
    assert bad.status_code == 422, f"expected 422, got {bad.status_code}: {bad.text[:200]}"

    after = mdb.conversations.find_one(
        {"participants": {"$all": [a["user_id"], b["user_id"]]}}, {"_id": 0})
    assert after["last_message"] == before["last_message"], \
        f"last_message mutated by 422: {after['last_message']!r}"
    assert after["last_message_at"] == before["last_message_at"], \
        "last_message_at bumped by a 422 request (dirty write)"
    assert mdb.dm_messages.count_documents({"conversation_id": after["conversation_id"]}) == 1


# ============ 5. DM last_message stripped ============
def test_dm_last_message_stripped(mdb):
    a = _signup("TEST_i7 StripA")
    b = _signup("TEST_i7 StripB")
    r = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                      headers=a["h"], json={"text": "   hello world   "}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["text"] == "hello world", repr(r.json()["text"])

    convs = requests.get(f"{BASE}/conversations", headers=a["h"], timeout=T).json()
    assert convs, "no conversations returned"
    assert convs[0]["last_message"] == "hello world", \
        f"last_message not stripped via API: {convs[0]['last_message']!r}"

    doc = mdb.conversations.find_one(
        {"participants": {"$all": [a["user_id"], b["user_id"]]}}, {"_id": 0})
    assert doc["last_message"] == "hello world", \
        f"last_message not stripped in db: {doc['last_message']!r}"
    # recipient view too
    convs_b = requests.get(f"{BASE}/conversations", headers=b["h"], timeout=T).json()
    assert convs_b[0]["last_message"] == "hello world"
