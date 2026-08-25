"""BarterGrid iteration-6 targeted regression tests.

Covers the 4 fixes applied on top of iteration 5:
 1. get_current_user rejects role in ('deleted','suspended')
 2. users.username unique-sparse index + PATCH /profile format/duplicate validation
 3. DM + trade-message endpoints reject whitespace-only text
 4. per-category notification prefs (notify_matches/notify_messages/notify_trades)
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


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


def _signup(display_name="TEST_i6 User"):
    email = f"TEST_i6_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE}/auth/signup", json={
        "email": email, "password": PW, "display_name": display_name}, timeout=30)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "user": d["user"], "h": {"Authorization": f"Bearer {d['token']}"}}


def _listing(u, title, **extra):
    payload = {"kind": "have", "title": title, "description": "TEST_ i6",
               "category": "home", "wants": ["anything"], "tags": ["test"]}
    payload.update(extra)
    return requests.post(f"{BASE}/listings", headers=u["h"], json=payload, timeout=30)


# ============================ 1. Token revocation ============================
def test_delete_account_revokes_old_token():
    u = _signup("TEST_i6 Quitter")
    assert requests.delete(f"{BASE}/account", headers=u["h"], timeout=30).status_code == 200
    r = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30)
    assert r.status_code == 401, f"old JWT still valid: {r.status_code} {r.text[:200]}"


def test_deleted_user_cannot_create_listing():
    u = _signup("TEST_i6 Quitter3")
    assert requests.delete(f"{BASE}/account", headers=u["h"], timeout=30).status_code == 200
    r = _listing(u, "TEST_i6 ghost listing")
    assert r.status_code == 401, f"deleted user created a listing: {r.status_code} {r.text[:200]}"


def test_suspended_user_token_rejected(mdb):
    u = _signup("TEST_i6 Suspended")
    assert requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).status_code == 200
    mdb.users.update_one({"user_id": u["user_id"]}, {"$set": {"role": "suspended"}})
    r = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30)
    assert r.status_code == 401, f"suspended user still authenticated: {r.status_code}"
    r2 = _listing(u, "TEST_i6 suspended listing")
    assert r2.status_code == 401, f"suspended user created a listing: {r2.status_code}"


# ============================ 2. Username validation ============================
def test_username_too_short_422():
    u = _signup("TEST_i6 Uname1")
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={"username": "ab"}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"


def test_username_bad_chars_422():
    u = _signup("TEST_i6 Uname2")
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={"username": "Bad!Chars"}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"


def test_username_too_long_422():
    u = _signup("TEST_i6 Uname2b")
    r = requests.patch(f"{BASE}/profile", headers=u["h"],
                       json={"username": "a" * 21}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"


def test_username_valid_persists():
    u = _signup("TEST_i6 Uname3")
    uname = f"good_{uuid.uuid4().hex[:8]}"
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={"username": uname}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["username"] == uname
    me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
    assert me["username"] == uname


def test_username_duplicate_409():
    a = _signup("TEST_i6 UnameA")
    b = _signup("TEST_i6 UnameB")
    uname = f"uniq_{uuid.uuid4().hex[:8]}"
    ra = requests.patch(f"{BASE}/profile", headers=a["h"], json={"username": uname}, timeout=30)
    assert ra.status_code == 200, ra.text[:300]
    rb = requests.patch(f"{BASE}/profile", headers=b["h"], json={"username": uname}, timeout=30)
    assert rb.status_code == 409, f"expected 409, got {rb.status_code}: {rb.text[:300]}"
    assert "already taken" in rb.json().get("detail", "").lower(), rb.text[:200]
    # B's username unchanged
    me = requests.get(f"{BASE}/auth/me", headers=b["h"], timeout=30).json()
    assert me["username"] != uname


def test_username_unique_index_exists(mdb):
    idx = mdb.users.index_information()
    match = [name for name, spec in idx.items()
             if spec.get("key") == [("username", 1)] and spec.get("unique")]
    assert match, f"no unique index on users.username: {list(idx.keys())}"


def test_username_setting_own_same_value_ok():
    """Re-saving your own username must not 409 on yourself."""
    u = _signup("TEST_i6 Uname4")
    uname = f"self_{uuid.uuid4().hex[:8]}"
    assert requests.patch(f"{BASE}/profile", headers=u["h"],
                          json={"username": uname}, timeout=30).status_code == 200
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={"username": uname}, timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"


# ============================ 3. Whitespace-only messages ============================
def test_dm_whitespace_only_422(mdb):
    a = _signup("TEST_i6 Sender")
    b = _signup("TEST_i6 Receiver")
    r = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                      headers=a["h"], json={"text": "   "}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"
    assert "blank" in r.text.lower(), r.text[:200]
    # nothing stored
    assert mdb.dm_messages.count_documents({"user_id": a["user_id"]}) == 0, \
        "blank DM was persisted"
    conv = mdb.conversations.find_one({"participants": {"$all": [a["user_id"], b["user_id"]]}})
    assert conv is None or (conv.get("last_message") or "").strip() != "", \
        f"conversation created with blank last_message: {conv.get('last_message')!r}"


def test_dm_whitespace_stripped_and_stored(mdb):
    a = _signup("TEST_i6 Stripper")
    b = _signup("TEST_i6 Strippee")
    r = requests.post(f"{BASE}/conversations/{b['user_id']}/messages",
                      headers=a["h"], json={"text": "   TEST_i6 padded   "}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["text"] == "TEST_i6 padded", repr(r.json()["text"])
    convs = requests.get(f"{BASE}/conversations", headers=a["h"], timeout=30).json()
    assert convs, "no conversations returned"
    lm = convs[0].get("last_message")
    assert lm == "TEST_i6 padded", f"last_message not stripped: {lm!r}"


def test_trade_message_whitespace_only_422():
    a = _signup("TEST_i6 TraderA")
    b = _signup("TEST_i6 TraderB")
    la = _listing(a, "TEST_i6 Drill")
    lb = _listing(b, "TEST_i6 Saw")
    assert la.status_code == 200 and lb.status_code == 200
    tr = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la.json()["listing_id"],
        "their_listing_id": lb.json()["listing_id"], "message": "TEST_i6 swap"}, timeout=30)
    assert tr.status_code == 200, tr.text[:300]
    tid = tr.json()["trade_id"]
    r = requests.post(f"{BASE}/trades/{tid}/messages", headers=a["h"],
                      json={"text": "   "}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"
    r2 = requests.post(f"{BASE}/trades/{tid}/messages", headers=a["h"],
                       json={"text": "  TEST_i6 padded trade msg  "}, timeout=30)
    assert r2.status_code == 200, r2.text[:300]
    assert r2.json()["text"] == "TEST_i6 padded trade msg", repr(r2.json()["text"])
    for u, l in ((a, la), (b, lb)):
        requests.delete(f"{BASE}/listings/{l.json()['listing_id']}", headers=u["h"], timeout=30)


# ============================ 4. Notification preferences ============================
def test_notify_messages_false_suppresses_inapp_and_email(mdb):
    sender = _signup("TEST_i6 Pinger")
    rec = _signup("TEST_i6 Muted")
    assert requests.patch(f"{BASE}/profile", headers=rec["h"], json={
        "notify_messages": False, "notify_trades": False}, timeout=30).status_code == 200

    r = requests.post(f"{BASE}/conversations/{rec['user_id']}/messages",
                      headers=sender["h"], json={"text": "TEST_i6 muted dm"}, timeout=30)
    assert r.status_code == 200, r.text[:300]

    qrows = mdb.email_queue.count_documents({"user_id": rec["user_id"]})
    assert qrows == 0, f"email queued despite notify_messages=false ({qrows} rows)"
    ns = requests.get(f"{BASE}/notifications", headers=rec["h"], timeout=30).json()
    assert ns == [], f"in-app notification created despite notify_messages=false: {ns}"

    # flip back on -> both appear
    assert requests.patch(f"{BASE}/profile", headers=rec["h"],
                          json={"notify_messages": True}, timeout=30).status_code == 200
    r2 = requests.post(f"{BASE}/conversations/{rec['user_id']}/messages",
                       headers=sender["h"], json={"text": "TEST_i6 unmuted dm"}, timeout=30)
    assert r2.status_code == 200, r2.text[:300]
    ns2 = requests.get(f"{BASE}/notifications", headers=rec["h"], timeout=30).json()
    assert any("TEST_i6 unmuted dm" in n["text"] for n in ns2), \
        f"notification missing after re-enabling: {ns2}"
    assert mdb.email_queue.count_documents(
        {"user_id": rec["user_id"], "kind": "direct_message"}) >= 1, \
        "email not queued after re-enabling notify_messages"


def test_notify_trades_false_suppresses_trade_proposal(mdb):
    a = _signup("TEST_i6 ProposerX")
    b = _signup("TEST_i6 MutedTrader")
    assert requests.patch(f"{BASE}/profile", headers=b["h"],
                          json={"notify_trades": False}, timeout=30).status_code == 200
    la = _listing(a, "TEST_i6 Lamp")
    lb = _listing(b, "TEST_i6 Chair")
    assert la.status_code == 200 and lb.status_code == 200
    tr = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la.json()["listing_id"],
        "their_listing_id": lb.json()["listing_id"], "message": "TEST_i6 offer"}, timeout=30)
    assert tr.status_code == 200, tr.text[:300]
    assert mdb.email_queue.count_documents(
        {"user_id": b["user_id"], "kind": "trade_proposal"}) == 0, \
        "trade_proposal email queued despite notify_trades=false"
    ns = requests.get(f"{BASE}/notifications", headers=b["h"], timeout=30).json()
    assert not [n for n in ns if n["type"] in ("trade_proposal", "trade")], \
        f"trade notification created despite notify_trades=false: {ns}"
    for u, l in ((a, la), (b, lb)):
        requests.delete(f"{BASE}/listings/{l.json()['listing_id']}", headers=u["h"], timeout=30)


def test_prefs_do_not_leak_to_other_user(mdb):
    """Muting my own notifications must not stop the OTHER party being notified."""
    muted = _signup("TEST_i6 SelfMuted")
    other = _signup("TEST_i6 Listener")
    assert requests.patch(f"{BASE}/profile", headers=muted["h"], json={
        "notify_messages": False, "notify_trades": False,
        "notify_matches": False}, timeout=30).status_code == 200
    r = requests.post(f"{BASE}/conversations/{other['user_id']}/messages",
                      headers=muted["h"], json={"text": "TEST_i6 leak check"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    ns = requests.get(f"{BASE}/notifications", headers=other["h"], timeout=30).json()
    assert any("TEST_i6 leak check" in n["text"] for n in ns), \
        f"recipient lost notification because SENDER muted themselves: {ns}"
    assert mdb.email_queue.count_documents(
        {"user_id": other["user_id"], "kind": "direct_message"}) >= 1, \
        "recipient email suppressed by sender's prefs"


def test_notify_matches_pref_persists():
    u = _signup("TEST_i6 Matcher")
    r = requests.patch(f"{BASE}/profile", headers=u["h"],
                       json={"notify_matches": False}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("notify_matches") is False
    me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
    assert me.get("notify_matches") is False
