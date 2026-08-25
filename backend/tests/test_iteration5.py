"""BarterGrid iteration-5 backend tests.

Covers: anti-spam listing rate limit (20/day), auto-generated unique @username,
first_name field, shipping fields on listings, settings endpoints
(DELETE /notifications, DELETE /account, notification preferences),
DM recipient validation + empty-text 422, public /users/{id} field whitelist,
trade_completed email on final completion, AI category suggestion.
"""
import os
import re
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
LAT, LNG = 37.7749, -122.4194

PUBLIC_FORBIDDEN = ["referral_code", "referred_by", "role", "email",
                    "approx_lat", "approx_lng", "password_hash", "_id"]
PUBLIC_REQUIRED = ["display_name", "username", "first_name", "picture", "city", "state",
                   "reputation_score", "successful_trades", "store_name", "store_tagline",
                   "banner_photo", "accent_color", "cashapp_tag", "venmo_tag", "paypal_link",
                   "bitcoin_address", "solana_address", "ethereum_address",
                   "listings", "verified_referral", "email_verified"]


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


def _signup(display_name, email=None):
    email = email or f"TEST_i5_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE}/auth/signup", json={
        "email": email, "password": PW, "display_name": display_name}, timeout=30)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "name": display_name, "user": d["user"],
            "h": {"Authorization": f"Bearer {d['token']}"}}


def _listing(u, title, **extra):
    payload = {"kind": "have", "title": title, "description": "TEST_ i5",
               "category": "home", "wants": ["anything"], "tags": ["test"]}
    payload.update(extra)
    r = requests.post(f"{BASE}/listings", headers=u["h"], json=payload, timeout=30)
    return r


@pytest.fixture(scope="module")
def world():
    a = _signup("TEST_i5 Alpha")
    b = _signup("TEST_i5 Bravo")
    created = []
    for u in (a, b):
        requests.patch(f"{BASE}/profile", headers=u["h"], json={
            "city": "San Francisco", "state": "CA", "country": "USA",
            "approx_lat": LAT, "approx_lng": LNG}, timeout=30)
    ra = _listing(a, "TEST_i5 Solar Lantern")
    rb = _listing(b, "TEST_i5 Camp Stove")
    assert ra.status_code == 200 and rb.status_code == 200
    created += [(a, ra.json()["listing_id"]), (b, rb.json()["listing_id"])]
    yield {"a": a, "b": b, "la": ra.json(), "lb": rb.json()}
    for u, lid in created:
        requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=30)


# ------------------------- DM recipient validation + empty text -------------------------
def test_dm_unknown_user_returns_404(world):
    r = requests.post(f"{BASE}/conversations/user_nope_i5/messages", headers=world["a"]["h"],
                      json={"to_user_id": "user_nope_i5", "text": "ghost"}, timeout=30)
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"


def test_dm_empty_text_422(world):
    r = requests.post(f"{BASE}/conversations/{world['b']['user_id']}/messages",
                      headers=world["a"]["h"], json={"text": ""}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"


def test_dm_to_user_id_optional(world):
    """to_user_id should now be optional (path param is authoritative)."""
    r = requests.post(f"{BASE}/conversations/{world['b']['user_id']}/messages",
                      headers=world["a"]["h"], json={"text": "TEST_i5 hello"}, timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    assert r.json()["text"] == "TEST_i5 hello"


def test_trade_message_empty_text_422(world):
    a, b = world["a"], world["b"]
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": world["la"]["listing_id"],
        "their_listing_id": world["lb"]["listing_id"], "message": "TEST_i5 swap"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    tid = r.json()["trade_id"]
    r2 = requests.post(f"{BASE}/trades/{tid}/messages", headers=a["h"], json={"text": ""}, timeout=30)
    assert r2.status_code == 422, f"expected 422, got {r2.status_code}: {r2.text[:200]}"
    # non-empty still works
    r3 = requests.post(f"{BASE}/trades/{tid}/messages", headers=a["h"], json={"text": "ok"}, timeout=30)
    assert r3.status_code == 200, r3.text[:200]


# ------------------------- Public /users/{id} whitelist -------------------------
def test_public_user_no_private_leaks(world):
    a = world["a"]
    requests.patch(f"{BASE}/profile", headers=a["h"], json={
        "store_name": "TEST_i5 Store", "store_tagline": "tagline", "banner_photo": "b.png",
        "accent_color": "#112233", "cashapp_tag": "$i5", "venmo_tag": "@i5",
        "paypal_link": "https://paypal.me/i5", "bitcoin_address": "bc1i5",
        "solana_address": "soli5", "ethereum_address": "0xi5"}, timeout=30)
    r = requests.get(f"{BASE}/users/{a['user_id']}", timeout=30)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    leaked = [k for k in PUBLIC_FORBIDDEN if k in d]
    assert not leaked, f"public profile leaks {leaked}"


def test_public_user_has_required_fields(world):
    r = requests.get(f"{BASE}/users/{world['a']['user_id']}", timeout=30)
    d = r.json()
    missing = [k for k in PUBLIC_REQUIRED if k not in d]
    assert not missing, f"public profile missing {missing}"
    assert isinstance(d["listings"], list)
    assert d["store_name"] == "TEST_i5 Store"
    assert d["username"]


# ------------------------- Auto-generated unique username -------------------------
def test_username_generated_and_unique_for_same_display_name():
    u1 = _signup("Alice Wonder")
    u2 = _signup("Alice Wonder")
    n1, n2 = u1["user"].get("username"), u2["user"].get("username")
    assert n1 and n2, f"username missing: {n1} {n2}"
    assert re.fullmatch(r"[a-z0-9_]+", n1), f"bad username format: {n1}"
    assert re.fullmatch(r"[a-z0-9_]+", n2), f"bad username format: {n2}"
    assert n1 != n2, f"duplicate usernames generated: {n1}"
    # persisted and readable
    for u, n in ((u1, n1), (u2, n2)):
        me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
        assert me["username"] == n


def test_first_name_defaults_from_display_name_and_editable():
    u = _signup("Charlie Brown Jr")
    assert u["user"].get("first_name") == "Charlie", u["user"].get("first_name")
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={"first_name": "Chuck"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["first_name"] == "Chuck"
    me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
    assert me["first_name"] == "Chuck"


# ------------------------- Shipping fields -------------------------
def test_shipping_fields_persist():
    u = _signup("TEST_i5 Shipper")
    r = _listing(u, "TEST_i5 Shipped Item", ships=True, shipping_fee="$10",
                 shipping_notes="USPS Priority")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["ships"] is True and d["shipping_fee"] == "$10" and d["shipping_notes"] == "USPS Priority"
    lid = d["listing_id"]
    g = requests.get(f"{BASE}/listings/{lid}", headers=u["h"], timeout=30)
    assert g.status_code == 200, g.text[:200]
    gd = g.json()
    assert gd["ships"] is True
    assert gd["shipping_fee"] == "$10"
    assert gd["shipping_notes"] == "USPS Priority"
    requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=30)


def test_shipping_defaults_false():
    u = _signup("TEST_i5 NoShip")
    r = _listing(u, "TEST_i5 Local Only")
    assert r.status_code == 200
    d = r.json()
    assert d["ships"] is False and d["shipping_fee"] is None and d["shipping_notes"] is None
    requests.delete(f"{BASE}/listings/{d['listing_id']}", headers=u["h"], timeout=30)


# ------------------------- Anti-spam rate limit -------------------------
def test_listing_rate_limit_20_per_day():
    u = _signup("TEST_i5 Spammer")
    ids = []
    try:
        for i in range(20):
            r = _listing(u, f"TEST_i5 Spam {i}")
            assert r.status_code == 200, f"listing #{i + 1} failed: {r.status_code} {r.text[:200]}"
            ids.append(r.json()["listing_id"])
        r21 = _listing(u, "TEST_i5 Spam 21")
        assert r21.status_code == 429, f"21st listing expected 429, got {r21.status_code}"
        detail = r21.json().get("detail", "")
        assert "Daily listing limit reached" in detail, detail
    finally:
        for lid in ids:
            requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=30)


def test_rate_limit_is_per_user():
    """A fresh user is not affected by another user's limit."""
    u = _signup("TEST_i5 Innocent")
    r = _listing(u, "TEST_i5 Innocent Item")
    assert r.status_code == 200, r.text[:200]
    requests.delete(f"{BASE}/listings/{r.json()['listing_id']}", headers=u["h"], timeout=30)


# ------------------------- Notification preferences -------------------------
def test_notification_prefs_persist_and_returned_by_me():
    u = _signup("TEST_i5 Prefs")
    prefs = {"email_notifications": False, "notify_matches": False,
             "notify_messages": False, "notify_trades": False}
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json=prefs, timeout=30)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    for k, v in prefs.items():
        assert d.get(k) == v, f"PATCH response {k}={d.get(k)} expected {v}"
    me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
    for k, v in prefs.items():
        assert me.get(k) == v, f"/auth/me {k}={me.get(k)} expected {v}"
    # can be turned back on
    r2 = requests.patch(f"{BASE}/profile", headers=u["h"],
                        json={"email_notifications": True}, timeout=30)
    assert r2.json().get("email_notifications") is True


def test_email_notifications_off_suppresses_email_queue(mdb, world):
    receiver = _signup("TEST_i5 Silent")
    assert requests.patch(f"{BASE}/profile", headers=receiver["h"],
                          json={"email_notifications": False}, timeout=30).status_code == 200
    before = mdb.email_queue.count_documents({"user_id": receiver["user_id"]})
    assert before == 0, f"unexpected pre-existing queue rows: {before}"
    r = requests.post(f"{BASE}/conversations/{receiver['user_id']}/messages",
                      headers=world["a"]["h"], json={"text": "TEST_i5 silent dm"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    after = mdb.email_queue.count_documents({"user_id": receiver["user_id"]})
    assert after == 0, f"email queued despite email_notifications=false ({after} rows)"
    # in-app notification should still be delivered
    ns = requests.get(f"{BASE}/notifications", headers=receiver["h"], timeout=30).json()
    assert any("TEST_i5 silent dm" in n["text"] for n in ns), "in-app notification missing"


# ------------------------- DELETE /notifications -------------------------
def test_delete_all_notifications(world):
    receiver = _signup("TEST_i5 Clearer")
    for i in range(3):
        assert requests.post(f"{BASE}/conversations/{receiver['user_id']}/messages",
                             headers=world["a"]["h"],
                             json={"text": f"TEST_i5 clear {i}"}, timeout=30).status_code == 200
    ns = requests.get(f"{BASE}/notifications", headers=receiver["h"], timeout=30).json()
    assert len(ns) >= 3, f"expected >=3 notifications, got {len(ns)}"
    r = requests.delete(f"{BASE}/notifications", headers=receiver["h"], timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("ok") is True
    ns2 = requests.get(f"{BASE}/notifications", headers=receiver["h"], timeout=30).json()
    assert ns2 == [], f"notifications not cleared: {ns2}"


def test_delete_notifications_requires_auth():
    r = requests.delete(f"{BASE}/notifications", timeout=30)
    assert r.status_code == 401


def test_delete_notifications_scoped_to_caller(world):
    """Clearing one user's notifications must not touch another user's."""
    victim = _signup("TEST_i5 Keeper")
    clearer = _signup("TEST_i5 Clearer2")
    for target in (victim, clearer):
        assert requests.post(f"{BASE}/conversations/{target['user_id']}/messages",
                             headers=world["a"]["h"],
                             json={"text": "TEST_i5 scoped"}, timeout=30).status_code == 200
    requests.delete(f"{BASE}/notifications", headers=clearer["h"], timeout=30)
    kept = requests.get(f"{BASE}/notifications", headers=victim["h"], timeout=30).json()
    assert len(kept) >= 1, "other user's notifications were wiped"


# ------------------------- DELETE /account -------------------------
def test_delete_account_soft_deletes(mdb):
    u = _signup("TEST_i5 Quitter")
    lr = _listing(u, "TEST_i5 Quitter Item")
    assert lr.status_code == 200
    lid = lr.json()["listing_id"]
    r = requests.delete(f"{BASE}/account", headers=u["h"], timeout=30)
    assert r.status_code == 200, r.text[:200]
    doc = mdb.users.find_one({"user_id": u["user_id"]})
    assert doc is not None
    assert doc.get("role") == "deleted", doc.get("role")
    assert doc.get("display_name") == "[deleted]"
    listing = mdb.listings.find_one({"listing_id": lid})
    assert listing and listing.get("is_active") is False, "listing not deactivated"
    assert mdb.notifications.count_documents({"user_id": u["user_id"]}) == 0
    assert mdb.user_sessions.count_documents({"user_id": u["user_id"]}) == 0
    mdb.listings.delete_one({"listing_id": lid})


def test_delete_account_revokes_old_token():
    u = _signup("TEST_i5 Quitter2")
    assert requests.delete(f"{BASE}/account", headers=u["h"], timeout=30).status_code == 200
    r = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30)
    assert r.status_code in (401, 404), (
        f"old JWT still valid after account deletion: {r.status_code} {r.text[:200]}")


def test_delete_account_requires_auth():
    r = requests.delete(f"{BASE}/account", timeout=30)
    assert r.status_code == 401


# ------------------------- trade_completed email on final completion -------------------------
def test_trade_completed_email_for_both_parties(mdb):
    a = _signup("TEST_i5 TraderA")
    b = _signup("TEST_i5 TraderB")
    ra = _listing(a, "TEST_i5 Hand Saw")
    rb = _listing(b, "TEST_i5 Axe Head")
    assert ra.status_code == 200 and rb.status_code == 200
    la, lb = ra.json(), rb.json()
    tr = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la["listing_id"],
        "their_listing_id": lb["listing_id"], "message": "TEST_i5 deal"}, timeout=30)
    assert tr.status_code == 200, tr.text[:300]
    tid = tr.json()["trade_id"]
    assert requests.post(f"{BASE}/trades/{tid}/action?action=accept",
                         headers=b["h"], timeout=30).status_code == 200
    assert requests.post(f"{BASE}/trades/{tid}/action?action=complete",
                         headers=a["h"], timeout=30).status_code == 200
    fin = requests.post(f"{BASE}/trades/{tid}/action?action=complete", headers=b["h"], timeout=30)
    assert fin.status_code == 200, fin.text[:300]
    assert fin.json()["status"] == "completed"
    for u in (a, b):
        rows = list(mdb.email_queue.find({"user_id": u["user_id"], "kind": "trade_completed"}))
        assert rows, f"no trade_completed email queued for {u['name']}"
        row = rows[-1]
        assert row["data"].get("trade_id") == tid
        assert row["status"] == "pending"
        assert row["to_email"] == u["email"]
        ns = requests.get(f"{BASE}/notifications", headers=u["h"], timeout=30).json()
        assert any(n["type"] == "rating_request" and n.get("trade_id") == tid for n in ns), \
            f"rating_request notification missing for {u['name']}"
    for u, l in ((a, la), (b, lb)):
        requests.delete(f"{BASE}/listings/{l['listing_id']}", headers=u["h"], timeout=30)


# ------------------------- AI -------------------------
def test_ai_suggest_category(world):
    r = requests.post(f"{BASE}/ai/suggest-category", headers=world["a"]["h"],
                      json={"title": "Vintage acoustic guitar",
                            "description": "Gently used dreadnought guitar"}, timeout=120)
    assert r.status_code == 200, r.text[:300]
    cat = r.json().get("category")
    assert cat and isinstance(cat, str), r.text[:200]
    print(f"AI suggested category: {cat}")
