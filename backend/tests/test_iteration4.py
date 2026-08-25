"""BarterGrid iteration-4 backend tests.

Covers: public/guest browsing, storefront profile fields, direct messaging (DMs),
DM authorization + blocking, trade lifecycle notifications, referral system,
AI category suggestion, email queue, MongoDB indexes.
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

LAT, LNG = 37.7749, -122.4194
PW = "Passw0rd!23"


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


def _signup(name, referral_code=None):
    email = f"TEST_{name}_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": PW, "display_name": f"TEST_{name}"}
    if referral_code:
        payload["referral_code"] = referral_code
    r = requests.post(f"{BASE}/auth/signup", json=payload, timeout=30)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "name": f"TEST_{name}", "h": {"Authorization": f"Bearer {d['token']}"}}


def _set_profile(u):
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={
        "city": "San Francisco", "state": "CA", "country": "USA",
        "approx_lat": LAT, "approx_lng": LNG, "search_radius_miles": 25}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _listing(u, title, wants):
    r = requests.post(f"{BASE}/listings", headers=u["h"], json={
        "kind": "HAVE", "title": title, "description": f"TEST_ {title}",
        "category": "home", "wants": wants, "tags": title.lower().split()}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


@pytest.fixture(scope="module")
def world():
    a = _signup("i4alice")
    b = _signup("i4bob")
    c = _signup("i4carol")
    for u in (a, b, c):
        _set_profile(u)
    la = _listing(a, "Solar Lantern", ["Camp Stove"])
    lb = _listing(b, "Camp Stove", ["Solar Lantern"])
    w = {"a": a, "b": b, "c": c, "la": la, "lb": lb}
    yield w
    for u, l in ((a, la), (b, lb)):
        requests.delete(f"{BASE}/listings/{l['listing_id']}", headers=u["h"], timeout=30)


# ------------------------- Public / guest browsing -------------------------
def test_public_listings_no_auth(world):
    r = requests.get(f"{BASE}/listings", timeout=30)
    assert r.status_code == 200, f"guest GET /listings -> {r.status_code} {r.text[:200]}"
    data = r.json()
    assert isinstance(data, list) and len(data) > 0
    assert all("_id" not in x for x in data)
    ids = [x["listing_id"] for x in data]
    assert world["la"]["listing_id"] in ids


def test_public_community_stats_no_auth():
    r = requests.get(f"{BASE}/community/stats", timeout=30)
    assert r.status_code == 200, r.status_code
    d = r.json()
    for k in ("total_users", "active_listings", "haves", "needs", "services", "completed_trades"):
        assert k in d, f"missing {k}"
    assert d["total_users"] >= 3


def test_public_storefront_no_auth_and_no_pii(world):
    r = requests.get(f"{BASE}/users/{world['a']['user_id']}", timeout=30)
    assert r.status_code == 200, f"guest GET /users/id -> {r.status_code}"
    d = r.json()
    for leak in ("email", "approx_lat", "approx_lng", "password_hash", "_id"):
        assert leak not in d, f"public profile leaks {leak}"
    assert "listings" in d and isinstance(d["listings"], list)
    assert world["la"]["listing_id"] in [x["listing_id"] for x in d["listings"]]


def test_public_storefront_unknown_user_404():
    r = requests.get(f"{BASE}/users/user_doesnotexist", timeout=30)
    assert r.status_code == 404, r.status_code


def test_mine_filter_requires_auth():
    r = requests.get(f"{BASE}/listings", params={"mine": "true"}, timeout=30)
    assert r.status_code == 401, r.status_code


# ------------------------- Storefront profile fields -------------------------
STORE_FIELDS = {
    "store_name": "TEST_ Alice Trading Post",
    "store_tagline": "Barter first, cash never",
    "banner_photo": "https://example.com/banner.png",
    "accent_color": "#2f5f3d",
    "cashapp_tag": "$alicebarter",
    "venmo_tag": "@alice-barter",
    "paypal_link": "https://paypal.me/alicebarter",
    "bitcoin_address": "bc1qtestaddressxyz",
    "solana_address": "SoLtestAddress123",
    "ethereum_address": "0xTestEthAddress",
    "accepts_donations": True,
}


def test_profile_storefront_fields_persist(world):
    a = world["a"]
    r = requests.patch(f"{BASE}/profile", headers=a["h"], json=STORE_FIELDS, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for k, v in STORE_FIELDS.items():
        assert d.get(k) == v, f"PATCH response {k}={d.get(k)!r} != {v!r}"
    me = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=30).json()
    for k, v in STORE_FIELDS.items():
        assert me.get(k) == v, f"persisted {k}={me.get(k)!r} != {v!r}"


def test_storefront_fields_visible_publicly(world):
    d = requests.get(f"{BASE}/users/{world['a']['user_id']}", timeout=30).json()
    assert d.get("store_name") == STORE_FIELDS["store_name"]
    assert d.get("cashapp_tag") == STORE_FIELDS["cashapp_tag"]
    assert d.get("accepts_donations") is True


def test_accepts_donations_can_be_set_false(world):
    a = world["a"]
    r = requests.patch(f"{BASE}/profile", headers=a["h"], json={"accepts_donations": False}, timeout=30)
    assert r.status_code == 200
    assert r.json().get("accepts_donations") is False, "accepts_donations=False not persisted"
    requests.patch(f"{BASE}/profile", headers=a["h"], json={"accepts_donations": True}, timeout=30)


# ------------------------- Direct messaging -------------------------
def test_conversation_created_idempotently(world):
    a, b = world["a"], world["b"]
    r1 = requests.get(f"{BASE}/conversations/{b['user_id']}", headers=a["h"], timeout=30)
    assert r1.status_code == 200, r1.text[:300]
    d1 = r1.json()
    assert "conversation" in d1 and "other_user" in d1 and "messages" in d1
    assert d1["other_user"]["user_id"] == b["user_id"]
    assert "email" not in d1["other_user"]
    cid = d1["conversation"]["conversation_id"]
    # same conversation from the other side
    r2 = requests.get(f"{BASE}/conversations/{a['user_id']}", headers=b["h"], timeout=30)
    assert r2.status_code == 200
    assert r2.json()["conversation"]["conversation_id"] == cid, "conversation id not symmetric"
    # idempotent
    r3 = requests.get(f"{BASE}/conversations/{b['user_id']}", headers=a["h"], timeout=30)
    assert r3.json()["conversation"]["conversation_id"] == cid


def test_dm_send_and_persist(world, mdb):
    a, b = world["a"], world["b"]
    text = f"TEST_ dm hello {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE}/conversations/{b['user_id']}/messages", headers=a["h"],
                      json={"to_user_id": b["user_id"], "text": text}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    msg = r.json()
    assert msg["text"] == text and "_id" not in msg
    assert msg["user_id"] == a["user_id"]
    # fetch from recipient side
    thread = requests.get(f"{BASE}/conversations/{a['user_id']}", headers=b["h"], timeout=30).json()
    assert text in [m["text"] for m in thread["messages"]], "message not persisted in thread"
    assert thread["conversation"].get("last_message") == text[:140], f"last_message={thread['conversation'].get('last_message')!r}"
    assert thread["conversation"].get("last_message_at")
    # notification for recipient
    notifs = requests.get(f"{BASE}/notifications", headers=b["h"], timeout=30).json()
    dm_notifs = [n for n in notifs if n["type"] == "message" and n.get("conversation_with") == a["user_id"]]
    assert dm_notifs, "no DM notification created for recipient"
    # email queued
    q = list(mdb.email_queue.find({"user_id": b["user_id"], "kind": "direct_message"}))
    assert q, "no direct_message entry in email_queue"


def test_conversation_list_and_unread(world):
    a, b, c = world["a"], world["b"], world["c"]
    text = f"TEST_ unread probe {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE}/conversations/{c['user_id']}/messages", headers=a["h"],
                      json={"to_user_id": c["user_id"], "text": text}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    convs = requests.get(f"{BASE}/conversations", headers=c["h"], timeout=30).json()
    mine = [x for x in convs if x["other_user"] and x["other_user"]["user_id"] == a["user_id"]]
    assert mine, "conversation not listed for recipient"
    assert mine[0]["unread"] >= 1, f"unread={mine[0]['unread']} expected >=1"
    assert mine[0]["last_message"] == text[:140]
    # open thread -> unread clears
    requests.get(f"{BASE}/conversations/{a['user_id']}", headers=c["h"], timeout=30)
    convs2 = requests.get(f"{BASE}/conversations", headers=c["h"], timeout=30).json()
    mine2 = [x for x in convs2 if x["other_user"] and x["other_user"]["user_id"] == a["user_id"]]
    assert mine2[0]["unread"] == 0, f"unread not cleared after opening thread: {mine2[0]['unread']}"
    # sender's own conversation list shows 0 unread
    convs3 = requests.get(f"{BASE}/conversations", headers=a["h"], timeout=30).json()
    own = [x for x in convs3 if x["other_user"] and x["other_user"]["user_id"] == c["user_id"]]
    assert own and own[0]["unread"] == 0
    assert all("_id" not in x for x in convs3)


def test_third_party_cannot_read_ab_thread(world):
    """Carol must not see Alice<->Bob messages via her own conversation endpoint."""
    a, b, c = world["a"], world["b"], world["c"]
    secret = f"TEST_ secret {uuid.uuid4().hex[:6]}"
    requests.post(f"{BASE}/conversations/{b['user_id']}/messages", headers=a["h"],
                  json={"to_user_id": b["user_id"], "text": secret}, timeout=30)
    ab_cid = requests.get(f"{BASE}/conversations/{b['user_id']}", headers=a["h"], timeout=30).json()["conversation"]["conversation_id"]
    r = requests.get(f"{BASE}/conversations/{a['user_id']}", headers=c["h"], timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["conversation"]["conversation_id"] != ab_cid, "third party got the A-B conversation id"
    assert secret not in [m["text"] for m in d["messages"]], "A-B message leaked to third party"
    # C's conversation list must not include the A-B conversation
    convs = requests.get(f"{BASE}/conversations", headers=c["h"], timeout=30).json()
    assert ab_cid not in [x["conversation_id"] for x in convs]


def test_dm_self_rejected(world):
    a = world["a"]
    r = requests.get(f"{BASE}/conversations/{a['user_id']}", headers=a["h"], timeout=30)
    assert r.status_code == 400, r.status_code
    r2 = requests.post(f"{BASE}/conversations/{a['user_id']}/messages", headers=a["h"],
                       json={"to_user_id": a["user_id"], "text": "hi me"}, timeout=30)
    assert r2.status_code == 400, r2.status_code


def test_dm_requires_auth(world):
    r = requests.get(f"{BASE}/conversations", timeout=30)
    assert r.status_code == 401
    r2 = requests.get(f"{BASE}/conversations/{world['b']['user_id']}", timeout=30)
    assert r2.status_code == 401


def test_dm_unknown_user(world):
    r = requests.get(f"{BASE}/conversations/user_nope123", headers=world["a"]["h"], timeout=30)
    assert r.status_code == 404, r.status_code
    r2 = requests.post(f"{BASE}/conversations/user_nope123/messages", headers=world["a"]["h"],
                       json={"to_user_id": "user_nope123", "text": "ghost"}, timeout=30)
    assert r2.status_code == 404, f"POST DM to nonexistent user returned {r2.status_code} (expected 404)"


def test_block_prevents_dm_both_directions(world):
    a, c = world["a"], world["c"]
    assert requests.post(f"{BASE}/blocks/{c['user_id']}", headers=a["h"], timeout=30).status_code == 200
    try:
        # blocker -> blocked
        assert requests.get(f"{BASE}/conversations/{c['user_id']}", headers=a["h"], timeout=30).status_code == 403
        assert requests.post(f"{BASE}/conversations/{c['user_id']}/messages", headers=a["h"],
                             json={"to_user_id": c["user_id"], "text": "blocked?"}, timeout=30).status_code == 403
        # blocked -> blocker
        assert requests.get(f"{BASE}/conversations/{a['user_id']}", headers=c["h"], timeout=30).status_code == 403
        assert requests.post(f"{BASE}/conversations/{a['user_id']}/messages", headers=c["h"],
                             json={"to_user_id": a["user_id"], "text": "blocked back?"}, timeout=30).status_code == 403
    finally:
        assert requests.delete(f"{BASE}/blocks/{c['user_id']}", headers=a["h"], timeout=30).status_code == 200
    # restored
    assert requests.get(f"{BASE}/conversations/{c['user_id']}", headers=a["h"], timeout=30).status_code == 200


# ------------------------- Trade lifecycle notifications + email queue -------------------------
def _notif_texts(u, ntype=None):
    ns = requests.get(f"{BASE}/notifications", headers=u["h"], timeout=30).json()
    return [n["text"] for n in ns if ntype is None or n["type"] == ntype]


@pytest.fixture(scope="module")
def lifecycle(world, mdb):
    a, b = world["a"], world["b"]
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": world["la"]["listing_id"],
        "their_listing_id": world["lb"]["listing_id"], "message": "TEST_ swap?"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_notif_trade_proposal(world, lifecycle, mdb):
    texts = _notif_texts(world["b"], "trade_proposal")
    assert any("proposed a trade" in t and "Solar Lantern" in t for t in texts), texts[:5]
    assert list(mdb.email_queue.find({"user_id": world["b"]["user_id"], "kind": "trade_proposal"})), "no trade_proposal email queued"


def test_notif_accept(world, lifecycle):
    r = requests.post(f"{BASE}/trades/{lifecycle['trade_id']}/action", headers=world["b"]["h"],
                      params={"action": "accept"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] == "accepted"
    texts = _notif_texts(world["a"])
    assert any("accepted your trade proposal" in t for t in texts), texts[:5]


def test_notif_meetup(world, lifecycle, mdb):
    r = requests.post(f"{BASE}/trades/{lifecycle['trade_id']}/meetup", headers=world["b"]["h"], json={
        "location_name": "Main Library", "date": "2026-09-01", "time": "14:30", "location_type": "library"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] == "meetup_planned"
    texts = _notif_texts(world["a"], "meetup")
    assert any("Main Library" in t for t in texts), texts[:5]
    assert list(mdb.email_queue.find({"user_id": world["a"]["user_id"], "kind": "meetup_planned"})), "no meetup_planned email queued"


def test_notif_complete_and_rating_requests(world, lifecycle, mdb):
    a, b, tid = world["a"], world["b"], lifecycle["trade_id"]
    r1 = requests.post(f"{BASE}/trades/{tid}/action", headers=a["h"], params={"action": "complete"}, timeout=30)
    assert r1.status_code == 200 and r1.json()["status"] != "completed"
    # one-sided complete notifies the other user + queues trade_update email
    assert any("marked the trade complete" in t for t in _notif_texts(b)), "no one-sided completion notification"
    assert list(mdb.email_queue.find({"user_id": b["user_id"], "kind": "trade_update"})), "no trade_update email queued"
    r2 = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"], params={"action": "complete"}, timeout=30)
    assert r2.status_code == 200 and r2.json()["status"] == "completed"
    # rating_request to BOTH users
    for u in (a, b):
        assert any("Trade complete!" in t for t in _notif_texts(u, "rating_request")), f"no rating_request for {u['name']}"


def test_notif_decline(world):
    """Decline path generates a notification for the proposer."""
    a, b = world["a"], world["b"]
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": world["la"]["listing_id"],
        "their_listing_id": world["lb"]["listing_id"], "message": "TEST_ second swap"}, timeout=30)
    assert r.status_code == 200
    tid = r.json()["trade_id"]
    d = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"], params={"action": "decline"}, timeout=30)
    assert d.status_code == 200 and d.json()["status"] == "declined"
    assert any("declined your trade proposal" in t for t in _notif_texts(a))


# ------------------------- Referrals -------------------------
@pytest.fixture(scope="module")
def referral_world(world):
    a = world["a"]
    r = requests.get(f"{BASE}/referrals/mine", headers=a["h"], timeout=30)
    assert r.status_code == 200, r.text[:300]
    code = r.json()["referral_code"]
    dave = _signup("i4dave", referral_code=code)
    _set_profile(dave)
    erin = _signup("i4erin")
    _set_profile(erin)
    ld = _listing(dave, "Hand Saw", ["Axe Head"])
    le = _listing(erin, "Axe Head", ["Hand Saw"])
    yield {"code": code, "dave": dave, "erin": erin, "ld": ld, "le": le}
    requests.delete(f"{BASE}/listings/{ld['listing_id']}", headers=dave["h"], timeout=30)
    requests.delete(f"{BASE}/listings/{le['listing_id']}", headers=erin["h"], timeout=30)


def test_referrals_mine_shape(world, referral_world):
    r = requests.get(f"{BASE}/referrals/mine", headers=world["a"]["h"], timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("referral_code", "referred_count", "verified_count", "referred_users"):
        assert k in d, f"missing {k}"
    assert d["referred_count"] >= 1, d
    names = [u["display_name"] for u in d["referred_users"]]
    assert referral_world["dave"]["name"] in names, names
    assert all("email" not in u for u in d["referred_users"])


def test_referral_lookup_public(world, referral_world):
    r = requests.get(f"{BASE}/referrals/lookup/{referral_world['code']}", timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    d = r.json()
    assert d["display_name"] == world["a"]["name"]
    assert "city" in d and "reputation_score" in d
    assert "email" not in d and "password_hash" not in d and "_id" not in d
    # lowercase code should also work (server upper-cases)
    r2 = requests.get(f"{BASE}/referrals/lookup/{referral_world['code'].lower()}", timeout=30)
    assert r2.status_code == 200, "lowercase invite code not accepted"


def test_referral_lookup_invalid_404():
    r = requests.get(f"{BASE}/referrals/lookup/ZZZZZZZZ", timeout=30)
    assert r.status_code == 404, r.status_code


def test_referral_verified_on_first_trade(world, referral_world):
    a, dave, erin = world["a"], referral_world["dave"], referral_world["erin"]
    r = requests.post(f"{BASE}/trades", headers=dave["h"], json={
        "to_user_id": erin["user_id"], "my_listing_id": referral_world["ld"]["listing_id"],
        "their_listing_id": referral_world["le"]["listing_id"], "message": "TEST_ saw for axe"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    tid = r.json()["trade_id"]
    assert requests.post(f"{BASE}/trades/{tid}/action", headers=erin["h"], params={"action": "accept"}, timeout=30).status_code == 200
    assert requests.post(f"{BASE}/trades/{tid}/action", headers=dave["h"], params={"action": "complete"}, timeout=30).status_code == 200
    rc = requests.post(f"{BASE}/trades/{tid}/action", headers=erin["h"], params={"action": "complete"}, timeout=30)
    assert rc.status_code == 200 and rc.json()["status"] == "completed"

    me_dave = requests.get(f"{BASE}/auth/me", headers=dave["h"], timeout=30).json()
    assert me_dave.get("verified_referral") is True, "referred user not verified after first trade"
    me_alice = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=30).json()
    assert me_alice.get("verified_referral") is True, "referrer not verified after referee's first trade"

    assert any(n["type"] == "referral_verified" for n in requests.get(f"{BASE}/notifications", headers=dave["h"], timeout=30).json()), "referee got no referral_verified notification"
    assert any(n["type"] == "referral_verified" for n in requests.get(f"{BASE}/notifications", headers=a["h"], timeout=30).json()), "referrer got no referral_verified notification"

    d = requests.get(f"{BASE}/referrals/mine", headers=a["h"], timeout=30).json()
    assert d["verified_count"] >= 1, d


def test_signup_bogus_referral_code_still_works():
    u = _signup("i4frank", referral_code="NOSUCHCODE")
    me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
    assert me.get("referred_by") is None


# ------------------------- AI category suggestion -------------------------
def test_ai_suggest_category(world):
    r = requests.post(f"{BASE}/ai/suggest-category", headers=world["a"]["h"],
                      json={"title": "Cordless drill and battery", "description": ""}, timeout=60)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    d = r.json()
    assert "category" in d and isinstance(d["category"], str) and d["category"].strip(), d
    print(f"AI suggested category: {d['category']}")


def test_ai_suggest_requires_auth():
    r = requests.post(f"{BASE}/ai/suggest-category", json={"title": "x"}, timeout=30)
    assert r.status_code == 401, r.status_code


# ------------------------- Kind normalization regression -------------------------
def test_kind_normalization_and_filter(world):
    assert world["la"]["kind"] == "have"
    r = requests.get(f"{BASE}/listings", headers=world["c"]["h"], params={"kind": "Have"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data and all(x["kind"] == "have" for x in data)
    assert world["la"]["listing_id"] in [x["listing_id"] for x in data]


# ------------------------- MongoDB indexes -------------------------
EXPECTED_INDEXES = {
    "users": [[("user_id", 1)], [("email", 1)], [("referral_code", 1)]],
    "listings": [[("listing_id", 1)], [("user_id", 1), ("kind", 1), ("is_active", 1)],
                 [("created_at", 1)], [("category", 1)]],
    "trades": [[("trade_id", 1)], [("proposer_id", 1), ("recipient_id", 1)], [("updated_at", 1)]],
    "trade_messages": [[("trade_id", 1), ("created_at", 1)]],
    "notifications": [[("user_id", 1), ("created_at", -1)]],
    "blocks": [[("blocker", 1), ("blocked", 1)]],
    "conversations": [[("conversation_id", 1)], [("participants", 1)]],
    "dm_messages": [[("conversation_id", 1), ("created_at", 1)]],
}


@pytest.mark.parametrize("coll", list(EXPECTED_INDEXES))
def test_indexes_present(mdb, coll, world):
    existing = [list(v["key"]) for v in mdb[coll].index_information().values()]
    existing_norm = [[(k, int(d)) for k, d in key] for key in existing]
    for want in EXPECTED_INDEXES[coll]:
        assert want in existing_norm, f"{coll} missing index {want}; have {existing_norm}"


def test_unique_indexes(mdb, world):
    ui = {("users", "user_id"), ("users", "email"), ("listings", "listing_id"),
          ("trades", "trade_id"), ("conversations", "conversation_id")}
    for coll, field in ui:
        info = mdb[coll].index_information()
        match = [v for v in info.values() if list(v["key"]) == [(field, 1)]]
        assert match, f"{coll}.{field} index missing"
        assert match[0].get("unique") is True, f"{coll}.{field} index is not unique"


def test_email_queue_kinds_present(mdb, world, lifecycle):
    kinds = set(mdb.email_queue.distinct("kind"))
    for k in ("trade_proposal", "direct_message", "meetup_planned", "trade_update"):
        assert k in kinds, f"email_queue missing kind {k}; found {kinds}"
    doc = mdb.email_queue.find_one({"kind": "direct_message"})
    for f in ("id", "user_id", "to_email", "subject", "status", "created_at"):
        assert f in doc, f"email_queue doc missing {f}"
    assert doc["status"] == "pending"
