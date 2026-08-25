"""BarterGrid iteration-8 targeted tests.

Covers:
 1. Notifications work for FRESH signups (no PATCH /profile) — message, trade_proposal, meetup, rating_request
 2. Preferences still respected (notify_messages false -> no in-app + no email; flip back -> resumes)
 3. GET /api/dashboard/stats — all 10 fields, PERSONAL counts, 401 w/o auth, nearby counts
 4. GET /api/search/suggest — shape, own-listing exclusion, case-insensitivity, distance sort, 401, 422
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
LAT, LNG = 37.7749, -122.4194


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


# ---------------- helpers ----------------
def _signup(display_name="TEST_i8 User"):
    email = f"TEST_i8_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE}/auth/signup",
                      json={"email": email, "password": PW, "display_name": display_name}, timeout=T)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "user": d["user"], "h": {"Authorization": f"Bearer {d['token']}"}}


def _patch(u, **kw):
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json=kw, timeout=T)
    assert r.status_code == 200, f"profile patch failed {r.status_code} {r.text[:300]}"
    return r.json()


def _listing(u, title, kind="have", **extra):
    payload = {"kind": kind, "title": title, "description": "TEST_ i8",
               "category": "tools", "wants": ["anything"], "tags": ["testi8"]}
    payload.update(extra)
    r = requests.post(f"{BASE}/listings", headers=u["h"], json=payload, timeout=T)
    assert r.status_code == 200, f"listing failed {r.status_code} {r.text[:300]}"
    return r.json()["listing_id"]


def _notifs(u):
    r = requests.get(f"{BASE}/notifications", headers=u["h"], timeout=T)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def _cleanup(pairs):
    for u, lid in pairs:
        requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=T)


def _stats(u):
    r = requests.get(f"{BASE}/dashboard/stats", headers=u["h"], timeout=T)
    assert r.status_code == 200, f"dashboard/stats {r.status_code} {r.text[:300]}"
    return r.json()


# ============ 1. fresh signup gets notification defaults in the DB doc ============
def test_fresh_signup_has_notification_prefs_true(mdb):
    u = _signup("TEST_i8 FreshPrefs")
    doc = mdb.users.find_one({"user_id": u["user_id"]})
    assert doc is not None
    for f in ("email_notifications", "notify_matches", "notify_messages", "notify_trades"):
        assert doc.get(f) is True, f"{f} is {doc.get(f)!r} on a fresh signup, expected True"


# ============ 2. fresh users get DM notification without any PATCH ============
def test_fresh_signup_dm_creates_message_notification():
    alice = _signup("TEST_i8 Alice")
    bob = _signup("TEST_i8 Bob")
    r = requests.post(f"{BASE}/conversations/{bob['user_id']}/messages",
                      headers=alice["h"], json={"text": "TEST_i8 hello bob"}, timeout=T)
    assert r.status_code == 200, r.text[:300]

    ns = _notifs(bob)
    msgs = [n for n in ns if n["type"] == "message"]
    assert len(msgs) == 1, f"expected exactly 1 message notification for fresh user, got {ns}"
    assert "TEST_i8 hello bob" in msgs[0]["text"], msgs[0]
    assert "TEST_i8 Alice" in msgs[0]["text"], msgs[0]
    assert msgs[0]["read"] is False


# ============ 3. fresh users get trade_proposal / meetup / rating_request ============
def test_fresh_signup_trade_meetup_rating_notifications():
    a = _signup("TEST_i8 Proposer")
    b = _signup("TEST_i8 Recipient")
    la = _listing(a, "TEST_i8 Hammer")
    lb = _listing(b, "TEST_i8 Wrench")

    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la,
        "their_listing_id": lb, "message": "TEST_i8 offer"}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    tid = r.json()["trade_id"]
    assert any(n["type"] == "trade_proposal" for n in _notifs(b)), \
        f"no trade_proposal notification for fresh user: {_notifs(b)}"

    # accept -> proposer gets 'trade' notification
    ra = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"], params={"action": "accept"}, timeout=T)
    assert ra.status_code == 200, ra.text[:300]
    assert any(n["type"] == "trade" for n in _notifs(a)), f"no trade update notification: {_notifs(a)}"

    # meetup -> other party gets 'meetup'
    rm = requests.post(f"{BASE}/trades/{tid}/meetup", headers=a["h"], json={
        "location_name": "TEST_i8 Library", "date": "2026-08-01", "time": "10:00"}, timeout=T)
    assert rm.status_code == 200, rm.text[:300]
    assert any(n["type"] == "meetup" for n in _notifs(b)), f"no meetup notification: {_notifs(b)}"

    # both complete -> rating_request for both
    for who in (a, b):
        rc = requests.post(f"{BASE}/trades/{tid}/action", headers=who["h"],
                           params={"action": "complete"}, timeout=T)
        assert rc.status_code == 200, rc.text[:300]
    for who in (a, b):
        assert any(n["type"] == "rating_request" for n in _notifs(who)), \
            f"no rating_request notification for fresh user: {_notifs(who)}"

    _cleanup([(a, la), (b, lb)])


# ============ 4. preferences still respected ============
def test_notify_messages_false_still_suppresses_then_resumes(mdb):
    sender = _signup("TEST_i8 Sender")
    bob = _signup("TEST_i8 MutedBob")
    _patch(bob, notify_messages=False)

    r = requests.post(f"{BASE}/conversations/{bob['user_id']}/messages",
                      headers=sender["h"], json={"text": "TEST_i8 muted dm"}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    assert [n for n in _notifs(bob) if n["type"] == "message"] == [], \
        "message notification created despite notify_messages=false"
    assert mdb.email_queue.count_documents(
        {"user_id": bob["user_id"], "kind": "direct_message"}) == 0, \
        "email queued despite notify_messages=false"

    _patch(bob, notify_messages=True)
    r2 = requests.post(f"{BASE}/conversations/{bob['user_id']}/messages",
                       headers=sender["h"], json={"text": "TEST_i8 unmuted dm"}, timeout=T)
    assert r2.status_code == 200, r2.text[:300]
    assert any("TEST_i8 unmuted dm" in n["text"] for n in _notifs(bob)), \
        "notification did not resume after re-enabling notify_messages"
    assert mdb.email_queue.count_documents(
        {"user_id": bob["user_id"], "kind": "direct_message"}) >= 1


# ============ 5. dashboard/stats shape + personal counts ============
def test_dashboard_stats_shape_and_personal_counts(mdb):
    u = _signup("TEST_i8 Dash")
    s = _stats(u)
    expected = {"my_haves", "my_needs", "my_services", "my_completed_trades", "my_active_trades",
                "has_location", "radius_miles", "nearby_haves", "nearby_needs", "nearby_services"}
    assert expected.issubset(set(s.keys())), f"missing fields: {expected - set(s.keys())}"
    assert s["my_haves"] == 0 and s["my_needs"] == 0 and s["my_services"] == 0, s
    assert s["has_location"] is False, s
    assert s["radius_miles"] == 10, s
    # nearby must be 0 without location
    assert s["nearby_haves"] == 0 and s["nearby_needs"] == 0 and s["nearby_services"] == 0, s

    l1 = _listing(u, "TEST_i8 Ladder", kind="have")
    l2 = _listing(u, "TEST_i8 Paint", kind="have")
    l3 = _listing(u, "TEST_i8 Need Bike", kind="need")
    l4 = _listing(u, "TEST_i8 Tutoring", kind="service")
    s2 = _stats(u)
    assert s2["my_haves"] == 2, s2
    assert s2["my_needs"] == 1, s2
    assert s2["my_services"] == 1, s2

    # must be personal, not global
    global_haves = mdb.listings.count_documents({"kind": "have", "is_active": True})
    assert s2["my_haves"] < global_haves, "my_haves looks like a global total"

    # completed trades must match db
    db_completed = mdb.trades.count_documents(
        {"$or": [{"proposer_id": u["user_id"]}, {"recipient_id": u["user_id"]}], "status": "completed"})
    assert s2["my_completed_trades"] == db_completed == 0, s2

    _cleanup([(u, l1), (u, l2), (u, l3), (u, l4)])


def test_dashboard_stats_completed_and_active_trades(mdb):
    a = _signup("TEST_i8 TA")
    b = _signup("TEST_i8 TB")
    la = _listing(a, "TEST_i8 Drill A")
    lb = _listing(b, "TEST_i8 Drill B")
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": la,
        "their_listing_id": lb, "message": "TEST_i8"}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    tid = r.json()["trade_id"]

    sa = _stats(a)
    assert sa["my_active_trades"] == 1, sa
    assert sa["my_completed_trades"] == 0, sa

    requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"], params={"action": "accept"}, timeout=T)
    for who in (a, b):
        requests.post(f"{BASE}/trades/{tid}/action", headers=who["h"], params={"action": "complete"}, timeout=T)

    sa2 = _stats(a)
    db_completed = mdb.trades.count_documents(
        {"$or": [{"proposer_id": a["user_id"]}, {"recipient_id": a["user_id"]}], "status": "completed"})
    assert sa2["my_completed_trades"] == db_completed == 1, (sa2, db_completed)
    assert sa2["my_active_trades"] == 0, sa2
    _cleanup([(a, la), (b, lb)])


def test_dashboard_stats_nearby_excludes_own():
    carol = _signup("TEST_i8 Carol")
    _patch(carol, approx_lat=LAT, approx_lng=LNG, search_radius_miles=10)
    dan = _signup("TEST_i8 Dan")
    _patch(dan, approx_lat=LAT, approx_lng=LNG, search_radius_miles=10)

    dan_ls = [_listing(dan, f"TEST_i8 Dan Item {i}") for i in range(3)]
    s_before = _stats(carol)
    assert s_before["has_location"] is True, s_before
    assert s_before["radius_miles"] == 10, s_before
    assert s_before["nearby_haves"] >= 3, s_before

    carol_l = _listing(carol, "TEST_i8 Carol Own Item")
    s_after = _stats(carol)
    assert s_after["nearby_haves"] == s_before["nearby_haves"], \
        f"own listing counted in nearby_haves: {s_before['nearby_haves']} -> {s_after['nearby_haves']}"
    assert s_after["my_haves"] == 1, s_after

    _cleanup([(dan, x) for x in dan_ls] + [(carol, carol_l)])


def test_dashboard_stats_requires_auth():
    r = requests.get(f"{BASE}/dashboard/stats", timeout=T)
    assert r.status_code == 401, f"expected 401, got {r.status_code} {r.text[:200]}"


# ============ 6. search/suggest ============
def test_search_suggest_shape_excludes_own_and_sorted():
    viewer = _signup("TEST_i8 Viewer")
    _patch(viewer, approx_lat=LAT, approx_lng=LNG, search_radius_miles=50)
    near = _signup("TEST_i8 NearOwner")
    _patch(near, approx_lat=LAT, approx_lng=LNG)
    far = _signup("TEST_i8 FarOwner")
    _patch(far, approx_lat=34.0522, approx_lng=-118.2437)  # LA ~347mi

    own = _listing(viewer, "TEST_i8 my own drill")
    lnear = _listing(near, "TEST_i8 Cordless drill near")
    lfar = _listing(far, "TEST_i8 Cordless drill far")

    r = requests.get(f"{BASE}/search/suggest", headers=viewer["h"], params={"q": "TEST_i8 Cordless drill"}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    items = r.json()
    assert isinstance(items, list) and len(items) <= 10, items
    ids = [i["listing_id"] for i in items]
    assert own not in ids, "search/suggest returned caller's own listing"
    assert lnear in ids and lfar in ids, ids
    keys = {"listing_id", "title", "kind", "category", "user_id", "photos", "distance_miles"}
    for it in items:
        assert keys.issubset(set(it.keys())), f"missing keys: {keys - set(it.keys())} in {it}"
    dists = [i["distance_miles"] for i in items if i["distance_miles"] is not None]
    assert dists == sorted(dists), f"not sorted ascending by distance: {dists}"
    assert items[ids.index(lnear)]["distance_miles"] <= items[ids.index(lfar)]["distance_miles"]

    # case insensitive
    r2 = requests.get(f"{BASE}/search/suggest", headers=viewer["h"], params={"q": "CORDLESS DRILL NEAR"}, timeout=T)
    assert r2.status_code == 200, r2.text[:300]
    assert lnear in [i["listing_id"] for i in r2.json()], r2.json()

    _cleanup([(viewer, own), (near, lnear), (far, lfar)])


def test_search_suggest_limit_max_10():
    viewer = _signup("TEST_i8 LimitViewer")
    owner = _signup("TEST_i8 LimitOwner")
    ls = [_listing(owner, f"TEST_i8 uniqueterm{uuid.uuid4().hex[:4]} widget") for _ in range(12)]
    r = requests.get(f"{BASE}/search/suggest", headers=viewer["h"], params={"q": "TEST_i8 uniqueterm"}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    assert len(r.json()) <= 10, len(r.json())
    _cleanup([(owner, x) for x in ls])


def test_search_suggest_auth_and_validation():
    r = requests.get(f"{BASE}/search/suggest", params={"q": "drill"}, timeout=T)
    assert r.status_code == 401, f"expected 401, got {r.status_code} {r.text[:200]}"

    u = _signup("TEST_i8 Validation")
    r2 = requests.get(f"{BASE}/search/suggest", headers=u["h"], params={"q": ""}, timeout=T)
    assert r2.status_code == 422, f"expected 422 for empty q, got {r2.status_code} {r2.text[:200]}"
    r3 = requests.get(f"{BASE}/search/suggest", headers=u["h"], timeout=T)
    assert r3.status_code == 422, f"expected 422 for missing q, got {r3.status_code} {r3.text[:200]}"
