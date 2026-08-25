"""BarterGrid backend e2e tests — iteration 2 retest.

Covers: auth/signup, profile coords, listings (case-insensitive kind), matching,
full trade lifecycle (propose→accept→meetup→chat→complete→rate), authorization,
listing detail enrichment, discover filters, blocks, duplicate rating guard.
"""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/") + "/api"

LAT, LNG = 37.7749, -122.4194


def _signup(name):
    email = f"TEST_{name}_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/auth/signup", json={"email": email, "password": "Passw0rd!23", "display_name": f"TEST_{name}"}, timeout=30)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    assert d["user"]["email"] == email.lower()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "h": {"Authorization": f"Bearer {d['token']}"}}


def _set_profile(u, city="San Francisco"):
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={"city": city, "state": "CA", "country": "USA",
                                                               "approx_lat": LAT, "approx_lng": LNG, "search_radius_miles": 25}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["city"] == city and d["approx_lat"] == LAT
    return d


# ---- Session-scoped shared world: users A, B, C + listings + trade ----
@pytest.fixture(scope="module")
def world():
    a = _signup("alice")
    b = _signup("bob")
    c = _signup("carol")
    _set_profile(a)
    _set_profile(b)
    _set_profile(c)

    # A posts HAVE (uppercase kind to test case-insensitivity)
    ra = requests.post(f"{BASE}/listings", headers=a["h"], json={
        "kind": "HAVE", "title": "Water Filter", "description": "TEST_ Berkey style water filter",
        "category": "home", "wants": ["Bike Lock"], "tags": ["filter", "water"]}, timeout=30)
    assert ra.status_code == 200, f"create listing A failed {ra.status_code} {ra.text[:300]}"
    la = ra.json()

    rb = requests.post(f"{BASE}/listings", headers=b["h"], json={
        "kind": "Have", "title": "Bike Lock", "description": "TEST_ heavy duty u-lock",
        "category": "home", "wants": ["Water Filter"], "tags": ["bike", "lock"]}, timeout=30)
    assert rb.status_code == 200, rb.text[:300]
    lb = rb.json()

    w = {"a": a, "b": b, "c": c, "la": la, "lb": lb}
    yield w
    # cleanup listings
    for u, l in ((a, la), (b, lb)):
        requests.delete(f"{BASE}/listings/{l['listing_id']}", headers=u["h"], timeout=30)


# ---- Health ----
def test_root():
    r = requests.get(f"{BASE}/", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---- Listings: kind normalization + enrichment ----
def test_kind_case_insensitive_normalized(world):
    assert world["la"]["kind"] == "have"
    assert world["lb"]["kind"] == "have"


def test_invalid_kind_rejected(world):
    r = requests.post(f"{BASE}/listings", headers=world["a"]["h"], json={"kind": "bogus", "title": "x", "category": "home"}, timeout=30)
    assert r.status_code == 422, r.status_code


def test_listing_detail_enrichment(world):
    # B views A's listing -> enrichment fields + distance
    r = requests.get(f"{BASE}/listings/{world['la']['listing_id']}", headers=world["b"]["h"], timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for f in ("user_display_name", "user_city", "user_reputation", "user_trades", "distance_miles"):
        assert f in d, f"missing {f}"
    assert d["user_city"] == "San Francisco"
    assert d["user_display_name"].startswith("TEST_alice")
    assert d["distance_miles"] == 0.0, f"distance_miles={d['distance_miles']}"
    assert "_id" not in d


# ---- Discover filters ----
def test_filter_mine(world):
    r = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"mine": "true"}, timeout=30)
    assert r.status_code == 200
    ids = [x["listing_id"] for x in r.json()]
    assert world["la"]["listing_id"] in ids
    assert all(x["user_id"] == world["a"]["user_id"] for x in r.json())


def test_filter_excludes_own_listings(world):
    r = requests.get(f"{BASE}/listings", headers=world["a"]["h"], timeout=30)
    assert r.status_code == 200
    assert world["la"]["listing_id"] not in [x["listing_id"] for x in r.json()]


def test_filter_kind_lowercase(world):
    r = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"kind": "have"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data, "no have listings returned"
    assert all(x["kind"] == "have" for x in data)


def test_filter_kind_uppercase_query(world):
    """kind query param should be case-insensitive too (matches create behaviour)."""
    r = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"kind": "HAVE"}, timeout=30)
    assert r.status_code == 200
    up = r.json()
    assert len(up) > 0, "GET /listings?kind=HAVE returned 0 results (kind filter not normalized)"
    assert all(x["kind"] == "have" for x in up)
    assert world["lb"]["listing_id"] in [x["listing_id"] for x in up]
    # uppercase result set must equal lowercase result set
    low = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"kind": "have"}, timeout=30).json()
    assert sorted(x["listing_id"] for x in up) == sorted(x["listing_id"] for x in low)
    # mixed case too
    mix = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"kind": "HaVe"}, timeout=30)
    assert mix.status_code == 200 and len(mix.json()) > 0, "mixed-case kind returned 0"


def test_filter_category_and_q(world):
    r = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"category": "home", "q": "Bike Lock"}, timeout=30)
    assert r.status_code == 200
    ids = [x["listing_id"] for x in r.json()]
    assert world["lb"]["listing_id"] in ids
    r2 = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"q": "zzz_no_match_zzz"}, timeout=30)
    assert r2.status_code == 200 and r2.json() == []


def test_filter_radius(world):
    r = requests.get(f"{BASE}/listings", headers=world["a"]["h"], params={"radius": 5}, timeout=30)
    assert r.status_code == 200
    assert world["lb"]["listing_id"] in [x["listing_id"] for x in r.json()]


def test_blocked_user_excluded_then_unblocked(world):
    a, b = world["a"], world["b"]
    rb = requests.post(f"{BASE}/blocks/{b['user_id']}", headers=a["h"], timeout=30)
    assert rb.status_code == 200, f"block failed {rb.status_code} {rb.text[:200]}"
    r = requests.get(f"{BASE}/listings", headers=a["h"], timeout=30)
    assert world["lb"]["listing_id"] not in [x["listing_id"] for x in r.json()], "blocked user's listing still visible"
    # reverse direction also hidden
    r2 = requests.get(f"{BASE}/listings", headers=b["h"], timeout=30)
    assert world["la"]["listing_id"] not in [x["listing_id"] for x in r2.json()], "blocker's listing visible to blocked user"
    ru = requests.delete(f"{BASE}/blocks/{b['user_id']}", headers=a["h"], timeout=30)
    assert ru.status_code == 200
    r3 = requests.get(f"{BASE}/listings", headers=a["h"], timeout=30)
    assert world["lb"]["listing_id"] in [x["listing_id"] for x in r3.json()], "unblock did not restore visibility"


# ---- Matching ----
def test_matches_both_directions(world):
    for who, mine, theirs in (("a", "la", "lb"), ("b", "lb", "la")):
        r = requests.get(f"{BASE}/matches", headers=world[who]["h"], timeout=30)
        assert r.status_code == 200, r.text[:300]
        ms = r.json()
        pair = [m for m in ms if m["my_listing"]["listing_id"] == world[mine]["listing_id"]
                and m["their_listing"]["listing_id"] == world[theirs]["listing_id"]]
        assert pair, f"no match found for user {who}: {ms}"
        assert pair[0]["score"] >= 6, pair[0]
        assert pair[0]["label"] in ("Excellent Match", "Strong Match")
        assert pair[0]["their_listing"]["distance_miles"] == 0.0


# ---- Authorization ----
def test_unauthenticated_trades_401():
    r = requests.get(f"{BASE}/trades", timeout=30)
    assert r.status_code == 401, r.status_code


def test_unauthenticated_listings_public():
    """Iteration 4 contract change: /listings is public for guest browsing (was 401)."""
    r = requests.get(f"{BASE}/listings", timeout=30)
    assert r.status_code == 200, r.status_code
    assert isinstance(r.json(), list)
    # ...but ?mine=true still requires auth
    r2 = requests.get(f"{BASE}/listings", params={"mine": "true"}, timeout=30)
    assert r2.status_code == 401, r2.status_code


def test_non_owner_cannot_patch_or_delete(world):
    lid = world["la"]["listing_id"]
    payload = {"kind": "have", "title": "Hacked", "category": "home"}
    r = requests.patch(f"{BASE}/listings/{lid}", headers=world["c"]["h"], json=payload, timeout=30)
    assert r.status_code == 403, f"PATCH by non-owner returned {r.status_code}"
    r2 = requests.delete(f"{BASE}/listings/{lid}", headers=world["c"]["h"], timeout=30)
    assert r2.status_code == 403, f"DELETE by non-owner returned {r2.status_code}"
    # listing intact
    r3 = requests.get(f"{BASE}/listings/{lid}", headers=world["a"]["h"], timeout=30)
    assert r3.status_code == 200 and r3.json()["title"] == "Water Filter"


def test_unknown_listing_404(world):
    r = requests.get(f"{BASE}/listings/lst_doesnotexist", headers=world["a"]["h"], timeout=30)
    assert r.status_code == 404


# ---- Full trade lifecycle ----
@pytest.fixture(scope="module")
def trade(world):
    a, b = world["a"], world["b"]
    r = requests.post(f"{BASE}/trades", headers=a["h"], json={
        "to_user_id": b["user_id"], "my_listing_id": world["la"]["listing_id"],
        "their_listing_id": world["lb"]["listing_id"], "message": "TEST_ swap?"}, timeout=30)
    assert r.status_code == 200, f"propose failed {r.status_code} {r.text[:300]}"
    t = r.json()
    assert t["status"] == "proposed" and "_id" not in t
    return t


def test_trade_visible_to_both(world, trade):
    for who in ("a", "b"):
        r = requests.get(f"{BASE}/trades", headers=world[who]["h"], timeout=30)
        assert r.status_code == 200
        found = [x for x in r.json() if x["trade_id"] == trade["trade_id"]]
        assert found, f"trade not listed for {who}"
        assert found[0]["other_user"] is not None


def test_third_party_cannot_access_trade(world, trade):
    tid = trade["trade_id"]
    c = world["c"]["h"]
    assert requests.get(f"{BASE}/trades/{tid}", headers=c, timeout=30).status_code == 403
    assert requests.get(f"{BASE}/trades/{tid}/messages", headers=c, timeout=30).status_code == 403
    r = requests.post(f"{BASE}/trades/{tid}/messages", headers=c, json={"text": "intruder"}, timeout=30)
    assert r.status_code == 403, r.status_code


def test_proposer_cannot_accept_own_trade(world, trade):
    r = requests.post(f"{BASE}/trades/{trade['trade_id']}/action", headers=world["a"]["h"], params={"action": "accept"}, timeout=30)
    assert r.status_code == 400, f"proposer self-accept returned {r.status_code}"


def test_lifecycle_accept_meetup_chat_complete_rate(world, trade):
    a, b, tid = world["a"], world["b"], trade["trade_id"]

    # meetup before accept -> 400
    early = requests.post(f"{BASE}/trades/{tid}/meetup", headers=b["h"], json={
        "location_name": "X", "date": "2026-08-01", "time": "10:00", "location_type": "library"}, timeout=30)
    assert early.status_code == 400, f"meetup before accept returned {early.status_code}"

    # accept
    r = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"], params={"action": "accept"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] == "accepted"

    # meetup
    r = requests.post(f"{BASE}/trades/{tid}/meetup", headers=b["h"], json={
        "location_name": "Main Library", "date": "2026-08-01", "time": "14:30", "location_type": "library"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["status"] == "meetup_planned"
    assert d["meetup"]["location_name"] == "Main Library" and d["meetup"]["time"] == "14:30"
    assert d["meetup"]["location_type"] == "library"

    # chat both ways
    for u, txt in ((a, "TEST_ see you at 2:30"), (b, "TEST_ confirmed")):
        rm = requests.post(f"{BASE}/trades/{tid}/messages", headers=u["h"], json={"text": txt}, timeout=30)
        assert rm.status_code == 200, rm.text[:300]
        assert rm.json()["text"] == txt
    rmsgs = requests.get(f"{BASE}/trades/{tid}/messages", headers=a["h"], timeout=30)
    assert rmsgs.status_code == 200
    texts = [m["text"] for m in rmsgs.json()]
    assert "TEST_ swap?" in texts and "TEST_ see you at 2:30" in texts and "TEST_ confirmed" in texts

    # baseline trade counts
    before = {}
    for k, u in (("a", a), ("b", b)):
        me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
        before[k] = me.get("successful_trades", 0)

    # complete by A only -> still not completed
    r = requests.post(f"{BASE}/trades/{tid}/action", headers=a["h"], params={"action": "complete"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] != "completed", "trade completed with only one party confirming"
    # complete by B
    r = requests.post(f"{BASE}/trades/{tid}/action", headers=b["h"], params={"action": "complete"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] == "completed", r.json()["status"]

    # ratings
    for u in (a, b):
        rr = requests.post(f"{BASE}/trades/{tid}/rate", headers=u["h"], json={"stars": 5, "tags": ["punctual"], "comment": "TEST_ great"}, timeout=30)
        assert rr.status_code == 200, rr.text[:300]

    # duplicate rating -> 400
    dup = requests.post(f"{BASE}/trades/{tid}/rate", headers=a["h"], json={"stars": 5}, timeout=30)
    assert dup.status_code == 400, f"duplicate rating returned {dup.status_code}"

    # verify counters + reputation persisted
    for k, u in (("a", a), ("b", b)):
        me = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30).json()
        assert me["successful_trades"] == before[k] + 1, f"{k} successful_trades {me['successful_trades']} != {before[k]+1}"
        assert me["reputation_score"] == 5.0, f"{k} reputation {me['reputation_score']}"
        assert me["ratings_count"] == 1

    # ratings endpoint
    rl = requests.get(f"{BASE}/users/{b['user_id']}/ratings", headers=a["h"], timeout=30)
    assert rl.status_code == 200 and len(rl.json()) == 1 and rl.json()[0]["stars"] == 5

    # third party cannot rate
    tp = requests.post(f"{BASE}/trades/{tid}/rate", headers=world["c"]["h"], json={"stars": 1}, timeout=30)
    assert tp.status_code == 403


@pytest.mark.parametrize("stars", [0, -5, 6, 99])
def test_rating_out_of_range_rejected(world, trade, stars):
    """stars must be validated to 1..5 by Pydantic (422) before any auth/state check."""
    r = requests.post(f"{BASE}/trades/{trade['trade_id']}/rate", headers=world["a"]["h"], json={"stars": stars}, timeout=30)
    assert r.status_code == 422, f"stars={stars} returned {r.status_code} {r.text[:200]}"


def test_rating_valid_boundaries_pass_validation(world, trade):
    """stars=1 and stars=5 must pass validation (rejected later for duplicate, not 422)."""
    for stars in (1, 5):
        r = requests.post(f"{BASE}/trades/{trade['trade_id']}/rate", headers=world["a"]["h"], json={"stars": stars}, timeout=30)
        assert r.status_code != 422, f"valid stars={stars} rejected as 422"
        assert r.status_code == 400, f"expected duplicate-rating 400, got {r.status_code} {r.text[:200]}"


def test_invalid_trade_listings_400(world):
    r = requests.post(f"{BASE}/trades", headers=world["a"]["h"], json={
        "to_user_id": world["b"]["user_id"], "my_listing_id": "lst_nope", "their_listing_id": world["lb"]["listing_id"]}, timeout=30)
    assert r.status_code == 400


def test_community_stats(world):
    r = requests.get(f"{BASE}/community/stats", headers=world["a"]["h"], timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["total_users"] >= 3 and d["completed_trades"] >= 1
    assert d["haves"] >= 2


def test_notifications(world):
    r = requests.get(f"{BASE}/notifications", headers=world["b"]["h"], timeout=30)
    assert r.status_code == 200
    types = [n["type"] for n in r.json()]
    assert "trade_proposal" in types
    assert requests.post(f"{BASE}/notifications/read", headers=world["b"]["h"], timeout=30).status_code == 200


def test_public_user_profile_hides_pii(world):
    r = requests.get(f"{BASE}/users/{world['b']['user_id']}", headers=world["a"]["h"], timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "email" not in d and "approx_lat" not in d and "password_hash" not in d
