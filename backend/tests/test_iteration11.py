"""Iteration 11 — httpOnly cookie auth migration + /api/community/dashboard.

Covers:
- GET /api/community/dashboard (public, shape, emergency propagation)
- signup/login set httpOnly Secure SameSite=None session_token cookie
- /api/auth/me works via cookie ONLY and via Bearer ONLY
- /api/auth/logout clears cookie
- emergency listings float to top of /api/listings for all sort params
- full trade flow regression (signup -> listing -> propose -> accept -> meetup -> complete -> rate)
- regression: conversations, matches/chains, referrals, public discover
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
PW = "Passw0rd!23"


def _new_email(name):
    return f"TEST_i11_{name}_{uuid.uuid4().hex[:8]}@example.com"


def _signup_raw(email, display="TEST_user"):
    return requests.post(f"{BASE}/auth/signup",
                         json={"email": email, "password": PW, "display_name": display}, timeout=30)


def _signup(name):
    email = _new_email(name)
    r = _signup_raw(email, f"TEST_{name}")
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "h": {"Authorization": f"Bearer {d['token']}"}, "cookies": r.cookies}


def _set_profile(u):
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={
        "city": "San Francisco", "state": "CA", "country": "USA",
        "approx_lat": LAT, "approx_lng": LNG, "search_radius_miles": 25}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _cookie_attrs(resp):
    """Parse raw Set-Cookie headers for session_token attributes."""
    raw = []
    # requests exposes multiple headers joined; use raw urllib3 headers
    try:
        raw = resp.raw.headers.getlist("Set-Cookie")
    except Exception:
        sc = resp.headers.get("Set-Cookie")
        raw = [sc] if sc else []
    for h in raw:
        if h.strip().lower().startswith("session_token="):
            return h
    return None


# ---------------- Cookie auth ----------------
class TestCookieAuth:
    def test_signup_sets_httponly_cookie(self):
        email = _new_email("cookie")
        r = _signup_raw(email)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert isinstance(body.get("token"), str) and len(body["token"]) > 20
        assert body["user"]["email"] == email.lower()
        assert "_id" not in body["user"]

        assert "session_token" in r.cookies, f"no session_token cookie; cookies={r.cookies.get_dict()}"
        hdr = _cookie_attrs(r)
        assert hdr, "Set-Cookie header for session_token missing"
        low = hdr.lower()
        assert "httponly" in low, f"HttpOnly missing: {hdr}"
        assert "secure" in low, f"Secure missing: {hdr}"
        assert "samesite=none" in low, f"SameSite=None missing: {hdr}"
        assert "path=/" in low

    def test_login_sets_cookie_and_returns_token(self):
        email = _new_email("login")
        _signup_raw(email)
        r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PW}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d.get("token"), str)
        assert d["user"]["email"] == email.lower()
        assert "password_hash" not in d["user"]
        hdr = _cookie_attrs(r)
        assert hdr and "httponly" in hdr.lower() and "samesite=none" in hdr.lower()

    def test_me_with_cookie_only(self):
        email = _new_email("cookieonly")
        s = requests.Session()
        r = s.post(f"{BASE}/auth/signup", json={"email": email, "password": PW, "display_name": "TEST_c"}, timeout=30)
        assert r.status_code == 200
        uid = r.json()["user"]["user_id"]
        # No Authorization header at all — cookie jar only
        me = s.get(f"{BASE}/auth/me", timeout=30)
        assert me.status_code == 200, f"cookie-only auth failed {me.status_code} {me.text[:300]}"
        assert me.json()["user_id"] == uid
        assert me.json()["email"] == email.lower()

    def test_me_with_bearer_only(self):
        u = _signup("bearer")
        r = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user_id"] == u["user_id"]

    def test_me_unauthenticated_401(self):
        r = requests.get(f"{BASE}/auth/me", timeout=30)
        assert r.status_code == 401

    def test_logout_clears_cookie_and_session(self):
        email = _new_email("logout")
        s = requests.Session()
        r = s.post(f"{BASE}/auth/signup", json={"email": email, "password": PW, "display_name": "TEST_l"}, timeout=30)
        assert r.status_code == 200
        out = s.post(f"{BASE}/auth/logout", timeout=30)
        assert out.status_code == 200, out.text[:300]
        assert out.json().get("ok") is True
        hdr = _cookie_attrs(out)
        assert hdr, "logout did not send Set-Cookie for session_token"
        low = hdr.lower()
        assert ("max-age=0" in low) or ("expires=thu, 01 jan 1970" in low) or ('session_token=""' in low) or ("session_token=;" in low), hdr
        # cookie jar should now be empty -> subsequent /me unauthenticated
        assert "session_token" not in s.cookies.get_dict(), s.cookies.get_dict()
        me = s.get(f"{BASE}/auth/me", timeout=30)
        assert me.status_code == 401, f"expected 401 after logout, got {me.status_code}"

    def test_invalid_token_cookie_rejected(self):
        r = requests.get(f"{BASE}/auth/me", cookies={"session_token": "garbage.token.value"}, timeout=30)
        assert r.status_code == 401


# ---------------- Community dashboard ----------------
@pytest.fixture(scope="module")
def emergency_world():
    u = _signup("emg")
    _set_profile(u)
    r = requests.post(f"{BASE}/listings", headers=u["h"], json={
        "kind": "need", "title": "TEST_i11 Emergency Food Boxes",
        "description": "TEST_i11 family needs food urgently",
        "category": "food", "is_emergency": True, "emergency_type": "food",
        "tags": ["urgent"]}, timeout=30)
    assert r.status_code == 200, f"emergency listing create failed {r.status_code} {r.text[:400]}"
    listing = r.json()
    # a service listing so top_services is populated
    rs = requests.post(f"{BASE}/listings", headers=u["h"], json={
        "kind": "service", "title": "TEST_i11 Bicycle Repair", "description": "TEST_i11 tune ups",
        "category": "services"}, timeout=30)
    assert rs.status_code == 200, rs.text[:300]
    svc = rs.json()
    yield {"u": u, "listing": listing, "svc": svc}
    requests.delete(f"{BASE}/listings/{listing['listing_id']}", headers=u["h"], timeout=30)
    requests.delete(f"{BASE}/listings/{svc['listing_id']}", headers=u["h"], timeout=30)


class TestCommunityDashboard:
    def test_dashboard_public_shape(self, emergency_world):
        r = requests.get(f"{BASE}/community/dashboard", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        d = r.json()
        for k in ["total_users", "by_kind", "by_category", "emergency", "emergency_count",
                  "completed_trades", "recent_completed_30d", "top_services"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["total_users"], int) and d["total_users"] > 0
        assert set(d["by_kind"].keys()) == {"have", "need", "service"}
        assert all(isinstance(v, int) for v in d["by_kind"].values())
        assert isinstance(d["by_category"], list) and len(d["by_category"]) > 0
        row = d["by_category"][0]
        assert set(["category", "have", "need", "service", "total"]).issubset(row.keys())
        assert row["total"] == row["have"] + row["need"] + row["service"]
        # sorted desc by total
        totals = [x["total"] for x in d["by_category"]]
        assert totals == sorted(totals, reverse=True)
        assert isinstance(d["top_services"], list)
        assert isinstance(d["completed_trades"], int)
        assert isinstance(d["recent_completed_30d"], int)
        assert d["recent_completed_30d"] <= d["completed_trades"]

    def test_dashboard_emergency_listing_present(self, emergency_world):
        r = requests.get(f"{BASE}/community/dashboard", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["emergency_count"] >= 1, d["emergency_count"]
        ids = [e["listing_id"] for e in d["emergency"]]
        assert emergency_world["listing"]["listing_id"] in ids, f"emergency listing not surfaced; got {ids}"
        e = next(x for x in d["emergency"] if x["listing_id"] == emergency_world["listing"]["listing_id"])
        assert e["is_emergency"] is True
        assert e.get("emergency_type") == "food"
        assert "_id" not in e
        assert e.get("user_display_name") or e.get("user_username")

    def test_dashboard_top_services_includes_new_service(self, emergency_world):
        r = requests.get(f"{BASE}/community/dashboard", timeout=60)
        d = r.json()
        assert emergency_world["svc"]["title"] in d["top_services"], d["top_services"]

    def test_dashboard_no_auth_leakage(self, emergency_world):
        """Public call must not error and must agree with the stats endpoint.
        Counters move while the parallel suite runs, so allow a small delta."""
        d = requests.get(f"{BASE}/community/dashboard", timeout=60).json()
        s = requests.get(f"{BASE}/community/stats", timeout=60).json()
        for a, b, label in [
            (d["total_users"], s["total_users"], "total_users"),
            (d["by_kind"]["have"], s["haves"], "haves"),
            (d["by_kind"]["need"], s["needs"], "needs"),
            (d["by_kind"]["service"], s["services"], "services"),
            (d["completed_trades"], s["completed_trades"], "completed_trades"),
        ]:
            assert abs(a - b) <= 5, f"{label} mismatch: dashboard={a} stats={b}"


class TestEmergencyFloatsTop:
    @pytest.mark.parametrize("sort", ["recent", "distance", "reputation"])
    def test_emergency_first(self, emergency_world, sort):
        u = emergency_world["u"]
        r = requests.get(f"{BASE}/listings", headers=u["h"], params={"sort": sort, "limit": 50}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        items = r.json()
        assert isinstance(items, list) and len(items) > 0
        flags = [bool(x.get("is_emergency")) for x in items]
        # all True must come before any False
        first_false = flags.index(False) if False in flags else len(flags)
        assert all(flags[:first_false]), flags[:10]
        assert not any(flags[first_false:]), f"emergency listing after non-emergency for sort={sort}"


# ---------------- Full trade flow regression ----------------
class TestTradeFlowRegression:
    def test_full_flow_with_cookie_sessions(self):
        sa, sb = requests.Session(), requests.Session()
        ea, eb = _new_email("flowa"), _new_email("flowb")
        ra = sa.post(f"{BASE}/auth/signup", json={"email": ea, "password": PW, "display_name": "TEST_FlowA"}, timeout=30)
        rb = sb.post(f"{BASE}/auth/signup", json={"email": eb, "password": PW, "display_name": "TEST_FlowB"}, timeout=30)
        assert ra.status_code == 200 and rb.status_code == 200
        a_id, b_id = ra.json()["user"]["user_id"], rb.json()["user"]["user_id"]

        for s in (sa, sb):
            pr = s.patch(f"{BASE}/profile", json={"city": "San Francisco", "state": "CA", "country": "USA",
                                                 "approx_lat": LAT, "approx_lng": LNG, "search_radius_miles": 25}, timeout=30)
            assert pr.status_code == 200, pr.text[:300]

        la = sa.post(f"{BASE}/listings", json={"kind": "have", "title": "TEST_i11 Camp Stove",
                                               "description": "TEST_i11 propane stove", "category": "outdoors",
                                               "wants": ["TEST_i11 Tent"]}, timeout=30)
        lb = sb.post(f"{BASE}/listings", json={"kind": "have", "title": "TEST_i11 Tent",
                                               "description": "TEST_i11 2 person tent", "category": "outdoors",
                                               "wants": ["TEST_i11 Camp Stove"]}, timeout=30)
        assert la.status_code == 200 and lb.status_code == 200, (la.text[:200], lb.text[:200])
        la, lb = la.json(), lb.json()

        # propose (cookie-only auth)
        tp = sa.post(f"{BASE}/trades", json={"to_user_id": b_id, "my_listing_id": la["listing_id"],
                                             "their_listing_id": lb["listing_id"], "message": "TEST_i11 swap?"}, timeout=30)
        assert tp.status_code == 200, f"propose failed {tp.status_code} {tp.text[:300]}"
        trade = tp.json()
        tid = trade["trade_id"]
        assert trade["status"] == "proposed"

        # accept
        acc = sb.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"}, timeout=30)
        assert acc.status_code == 200, acc.text[:300]
        assert acc.json()["status"] == "accepted"

        # meetup
        mu = sb.post(f"{BASE}/trades/{tid}/meetup", json={"location_name": "TEST_i11 Public Library",
                                                          "date": "2026-08-01", "time": "14:00",
                                                          "location_type": "library"}, timeout=30)
        assert mu.status_code == 200, mu.text[:300]
        got = sa.get(f"{BASE}/trades/{tid}", timeout=30)
        assert got.status_code == 200
        assert got.json()["meetup"]["location_name"] == "TEST_i11 Public Library"

        # chat
        cm = sa.post(f"{BASE}/trades/{tid}/messages", json={"text": "TEST_i11 see you there"}, timeout=30)
        assert cm.status_code == 200, cm.text[:300]
        msgs = sb.get(f"{BASE}/trades/{tid}/messages", timeout=30)
        assert msgs.status_code == 200
        assert any(m["text"] == "TEST_i11 see you there" for m in msgs.json())

        # complete both sides
        c1 = sa.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"}, timeout=30)
        assert c1.status_code == 200, c1.text[:300]
        c2 = sb.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"}, timeout=30)
        assert c2.status_code == 200, c2.text[:300]
        final = sa.get(f"{BASE}/trades/{tid}", timeout=30).json()
        assert final["status"] == "completed", final["status"]

        # rate
        rt = sa.post(f"{BASE}/trades/{tid}/rate", json={"stars": 5, "tags": ["punctual"], "comment": "TEST_i11 great"}, timeout=30)
        assert rt.status_code == 200, rt.text[:300]
        prof = requests.get(f"{BASE}/users/{b_id}", timeout=30)
        assert prof.status_code == 200
        assert prof.json()["ratings_count"] >= 1
        # duplicate rating blocked
        dup = sa.post(f"{BASE}/trades/{tid}/rate", json={"stars": 4}, timeout=30)
        assert dup.status_code in (400, 409), dup.status_code

        # cleanup
        sa.delete(f"{BASE}/listings/{la['listing_id']}", timeout=30)
        sb.delete(f"{BASE}/listings/{lb['listing_id']}", timeout=30)
        assert a_id != b_id


# ---------------- Other regressions ----------------
class TestOtherRegressions:
    def test_public_listings_browse_unauthenticated(self):
        r = requests.get(f"{BASE}/listings", params={"limit": 10}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        items = r.json()
        assert isinstance(items, list)
        for it in items:
            assert "_id" not in it
            assert "listing_id" in it and "kind" in it

    def test_conversations(self):
        ua, ub = _signup("conva"), _signup("convb")
        r = requests.get(f"{BASE}/conversations/{ub['user_id']}", headers=ua["h"], timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        conv = r.json()["conversation"]
        cid = conv["conversation_id"]
        m = requests.post(f"{BASE}/conversations/{ub['user_id']}/messages", headers=ua["h"], json={"text": "TEST_i11 hi"}, timeout=30)
        assert m.status_code == 200, m.text[:300]
        lst = requests.get(f"{BASE}/conversations/{ua['user_id']}", headers=ub["h"], timeout=30)
        assert lst.status_code == 200
        assert any(x["text"] == "TEST_i11 hi" for x in lst.json()["messages"])
        inbox = requests.get(f"{BASE}/conversations", headers=ub["h"], timeout=30)
        assert inbox.status_code == 200
        assert any(c["conversation_id"] == cid for c in inbox.json())

    def test_trade_chains(self):
        u = _signup("chain")
        _set_profile(u)
        r = requests.get(f"{BASE}/matches/chains", headers=u["h"], timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert isinstance(r.json(), list)

    def test_referrals(self):
        u = _signup("ref")
        r = requests.get(f"{BASE}/referrals/mine", headers=u["h"], timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        assert d.get("referral_code")
        look = requests.get(f"{BASE}/referrals/lookup/{d['referral_code']}", timeout=30)
        assert look.status_code == 200, look.text[:300]
        # signup with the referral code links referrer
        email = _new_email("refd")
        r2 = requests.post(f"{BASE}/auth/signup", json={"email": email, "password": PW,
                                                       "display_name": "TEST_refd",
                                                       "referral_code": d["referral_code"]}, timeout=30)
        assert r2.status_code == 200, r2.text[:300]
        assert r2.json()["user"]["referred_by"] == u["user_id"]

    def test_recent_completed_30d_counts_a_just_completed_trade(self):
        """BUG: trades never persist `completed_at`, so recent_completed_30d is always 0."""
        sa, sb = requests.Session(), requests.Session()
        ea, eb = _new_email("cmpa"), _new_email("cmpb")
        ra = sa.post(f"{BASE}/auth/signup", json={"email": ea, "password": PW, "display_name": "TEST_CmpA"}, timeout=30)
        rb = sb.post(f"{BASE}/auth/signup", json={"email": eb, "password": PW, "display_name": "TEST_CmpB"}, timeout=30)
        b_id = rb.json()["user"]["user_id"]
        assert ra.status_code == 200 and rb.status_code == 200
        la = sa.post(f"{BASE}/listings", json={"kind": "have", "title": "TEST_i11 Ladder",
                                               "description": "TEST_i11 8ft", "category": "Tools"}, timeout=30).json()
        lb = sb.post(f"{BASE}/listings", json={"kind": "have", "title": "TEST_i11 Drill",
                                               "description": "TEST_i11 cordless", "category": "Tools"}, timeout=30).json()
        before = requests.get(f"{BASE}/community/dashboard", timeout=60).json()["recent_completed_30d"]
        tid = sa.post(f"{BASE}/trades", json={"to_user_id": b_id, "my_listing_id": la["listing_id"],
                                              "their_listing_id": lb["listing_id"]}, timeout=30).json()["trade_id"]
        sb.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"}, timeout=30)
        sa.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"}, timeout=30)
        sb.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"}, timeout=30)
        assert sa.get(f"{BASE}/trades/{tid}", timeout=30).json()["status"] == "completed"
        after = requests.get(f"{BASE}/community/dashboard", timeout=60).json()
        sa.delete(f"{BASE}/listings/{la['listing_id']}", timeout=30)
        sb.delete(f"{BASE}/listings/{lb['listing_id']}", timeout=30)
        assert after["recent_completed_30d"] >= before + 1, (
            f"recent_completed_30d did not increase ({before} -> {after['recent_completed_30d']}); "
            "trade_action never writes `completed_at`, so the 30-day stat is permanently 0")

    def test_dashboard_stats_requires_auth(self):
        r = requests.get(f"{BASE}/dashboard/stats", timeout=30)
        assert r.status_code == 401
