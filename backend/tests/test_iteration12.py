"""Iteration 12 — regression pass over the refactored server.py helpers.

Covers:
- trade lifecycle end-to-end (propose -> accept -> meetup -> both complete -> rate),
  completed_at persistence, successful_trades increment, referral verification hook
  (_TRADE_ACTIONS dispatch / _handle_trade_complete / _finalize_completed_trade / _mark_referral_verified)
- GET /api/listings filters + sorting (_build_listing_query / _apply_listing_filters / _sort_listings)
- GET /api/matches/chains schema (cached wants_of closure)
- GET /api/dashboard/stats 10-key contract (_get_my_* + _get_nearby_counts via asyncio.gather)
- GET /api/community/dashboard rich schema
- auth via cookie AND Bearer header
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
PW = os.environ.get("BG_TEST_PASSWORD") or f"Tt!{uuid.uuid4().hex[:14]}"
T = 30


def _signup(name, ref_code=None):
    email = f"TEST_i12_{name}_{uuid.uuid4().hex[:8]}@example.com"
    body = {"email": email, "password": PW, "display_name": f"TEST_{name}"}
    if ref_code:
        body["referral_code"] = ref_code
    r = requests.post(f"{BASE}/auth/signup", json=body, timeout=T)
    assert r.status_code == 200, f"signup failed {r.status_code} {r.text[:300]}"
    d = r.json()
    return {"token": d["token"], "user_id": d["user"]["user_id"], "email": email.lower(),
            "user": d["user"], "h": {"Authorization": f"Bearer {d['token']}"},
            "cookies": {"session_token": r.cookies.get("session_token")}}


def _set_profile(u, radius=25):
    r = requests.patch(f"{BASE}/profile", headers=u["h"], json={
        "city": "San Francisco", "state": "CA", "country": "USA",
        "approx_lat": LAT, "approx_lng": LNG, "search_radius_miles": radius}, timeout=T)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _listing(u, kind, title, category="Tools", **extra):
    body = {"kind": kind, "title": title, "description": f"desc {title}",
            "category": category, "tags": extra.pop("tags", ["TEST"])}
    body.update(extra)
    r = requests.post(f"{BASE}/listings", headers=u["h"], json=body, timeout=T)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    return r.json()


def _del_listing(u, lid):
    requests.delete(f"{BASE}/listings/{lid}", headers=u["h"], timeout=T)


# ---------------- Trade lifecycle ----------------
class TestTradeLifecycle:
    def test_full_lifecycle_with_referral_hook(self):
        a = _signup("tlA")
        _set_profile(a)
        # referral: b signs up with a's code -> completing b's first trade verifies both
        ref = requests.get(f"{BASE}/referrals/mine", headers=a["h"], timeout=T)
        assert ref.status_code == 200, ref.text[:300]
        code = ref.json()["referral_code"]
        b = _signup("tlB", ref_code=code)
        _set_profile(b)

        la = _listing(a, "have", f"TEST_drill_{uuid.uuid4().hex[:6]}")
        lb = _listing(b, "have", f"TEST_ladder_{uuid.uuid4().hex[:6]}")

        a_before = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=T).json()["successful_trades"]
        b_before = requests.get(f"{BASE}/auth/me", headers=b["h"], timeout=T).json()["successful_trades"]

        # propose (a -> b)
        r = requests.post(f"{BASE}/trades", headers=a["h"], json={
            "my_listing_id": la["listing_id"], "their_listing_id": lb["listing_id"], "to_user_id": b["user_id"],
            "message": "TEST swap?"}, timeout=T)
        assert r.status_code == 200, r.text[:300]
        trade = r.json()
        tid = trade["trade_id"]
        assert trade["status"] == "proposed"

        # wrong-party accept must fail
        bad = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"},
                            headers=a["h"], timeout=T)
        assert bad.status_code == 400, f"proposer should not accept: {bad.status_code}"

        # unknown action rejected
        bad2 = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "bogus"},
                             headers=a["h"], timeout=T)
        assert bad2.status_code == 400

        # accept
        r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"},
                          headers=b["h"], timeout=T)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] == "accepted"

        # meetup
        r = requests.post(f"{BASE}/trades/{tid}/meetup", headers=a["h"], json={
            "location_name": "TEST Library", "date": "2026-08-01", "time": "10:00",
            "location_type": "library"}, timeout=T)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["meetup"]["location_name"] == "TEST Library"
        assert body["status"] == "meetup_planned"

        # complete side 1
        r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"},
                          headers=a["h"], timeout=T)
        assert r.status_code == 200, r.text[:300]
        half = r.json()
        assert half["status"] == "meetup_planned", f"one-sided complete should not finish trade: {half['status']}"
        assert half.get("proposer_completed") is True

        # complete side 2
        r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"},
                          headers=b["h"], timeout=T)
        assert r.status_code == 200, r.text[:300]
        done = r.json()
        assert done["status"] == "completed"
        assert done.get("completed_at"), "completed_at must be persisted when both sides complete"

        # counters incremented on both users
        a_after = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=T).json()["successful_trades"]
        b_after = requests.get(f"{BASE}/auth/me", headers=b["h"], timeout=T).json()["successful_trades"]
        assert a_after == a_before + 1, f"proposer successful_trades {a_before}->{a_after}"
        assert b_after == b_before + 1, f"recipient successful_trades {b_before}->{b_after}"

        # referral verification hook fired for both sides
        me_a = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=T).json()
        me_b = requests.get(f"{BASE}/auth/me", headers=b["h"], timeout=T).json()
        assert me_b.get("verified_referral") is True, "referred user should be verified_referral"
        assert me_a.get("verified_referral") is True, "referrer should be verified_referral"

        # ratings
        for who, other in ((a, b), (b, a)):
            rr = requests.post(f"{BASE}/trades/{tid}/rate", headers=who["h"],
                               json={"stars": 5, "comment": "TEST great"}, timeout=T)
            assert rr.status_code == 200, rr.text[:300]
        dup = requests.post(f"{BASE}/trades/{tid}/rate", headers=a["h"],
                            json={"stars": 4, "comment": "TEST dup"}, timeout=T)
        assert dup.status_code == 400, f"duplicate rating should be blocked, got {dup.status_code}"

        # cancel after completion is invalid
        c = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "cancel"},
                          headers=a["h"], timeout=T)
        assert c.status_code == 400

        _del_listing(a, la["listing_id"])
        _del_listing(b, lb["listing_id"])

    def test_repeat_complete_on_completed_trade_is_idempotent(self):
        """Calling complete again on an already-completed trade must not re-increment counters."""
        a, b = _signup("idA"), _signup("idB")
        la = _listing(a, "have", f"TEST_idem_a_{uuid.uuid4().hex[:6]}")
        lb = _listing(b, "have", f"TEST_idem_b_{uuid.uuid4().hex[:6]}")
        tid = requests.post(f"{BASE}/trades", headers=a["h"], json={
            "my_listing_id": la["listing_id"], "their_listing_id": lb["listing_id"], "to_user_id": b["user_id"],
            "message": "TEST"}, timeout=T).json()["trade_id"]
        requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"}, headers=b["h"], timeout=T)
        for u in (a, b):
            requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"}, headers=u["h"], timeout=T)
        base_a = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=T).json()["successful_trades"]
        r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"},
                          headers=a["h"], timeout=T)
        again_a = requests.get(f"{BASE}/auth/me", headers=a["h"], timeout=T).json()["successful_trades"]
        _del_listing(a, la["listing_id"])
        _del_listing(b, lb["listing_id"])
        assert again_a == base_a, (
            f"re-completing an already-completed trade re-incremented successful_trades "
            f"{base_a}->{again_a} (HTTP {r.status_code})")

    def test_complete_on_unaccepted_trade_should_be_rejected(self):
        """_handle_trade_complete has no state guard: a never-accepted (or declined) trade
        can be driven to 'completed' and inflate successful_trades."""
        a, b = _signup("stA"), _signup("stB")
        la = _listing(a, "have", f"TEST_st_a_{uuid.uuid4().hex[:6]}")
        lb = _listing(b, "have", f"TEST_st_b_{uuid.uuid4().hex[:6]}")
        tid = requests.post(f"{BASE}/trades", headers=a["h"], json={
            "my_listing_id": la["listing_id"], "their_listing_id": lb["listing_id"], "to_user_id": b["user_id"],
            "message": "TEST"}, timeout=T).json()["trade_id"]
        # decline, then try to complete from both sides
        requests.post(f"{BASE}/trades/{tid}/action", params={"action": "decline"}, headers=b["h"], timeout=T)
        codes = []
        for u in (a, b):
            r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"},
                              headers=u["h"], timeout=T)
            codes.append(r.status_code)
        final = requests.get(f"{BASE}/trades/{tid}", headers=a["h"], timeout=T).json()["status"]
        _del_listing(a, la["listing_id"])
        _del_listing(b, lb["listing_id"])
        assert final == "declined", (
            f"a DECLINED trade was driven to status={final} via action=complete (HTTP {codes})")

    def test_decline_flow(self):
        a, b = _signup("dcA"), _signup("dcB")
        la = _listing(a, "have", f"TEST_dec_a_{uuid.uuid4().hex[:6]}")
        lb = _listing(b, "have", f"TEST_dec_b_{uuid.uuid4().hex[:6]}")
        tid = requests.post(f"{BASE}/trades", headers=a["h"], json={
            "my_listing_id": la["listing_id"], "their_listing_id": lb["listing_id"], "to_user_id": b["user_id"],
            "message": "TEST"}, timeout=T).json()["trade_id"]
        r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "decline"},
                          headers=b["h"], timeout=T)
        assert r.status_code == 200 and r.json()["status"] == "declined"
        # accept after decline invalid
        r2 = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"},
                           headers=b["h"], timeout=T)
        assert r2.status_code == 400
        _del_listing(a, la["listing_id"])
        _del_listing(b, lb["listing_id"])

    def test_trade_action_requires_participant(self):
        a, b, c = _signup("pA"), _signup("pB"), _signup("pC")
        la = _listing(a, "have", f"TEST_par_a_{uuid.uuid4().hex[:6]}")
        lb = _listing(b, "have", f"TEST_par_b_{uuid.uuid4().hex[:6]}")
        tid = requests.post(f"{BASE}/trades", headers=a["h"], json={
            "my_listing_id": la["listing_id"], "their_listing_id": lb["listing_id"], "to_user_id": b["user_id"],
            "message": "TEST"}, timeout=T).json()["trade_id"]
        r = requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"},
                          headers=c["h"], timeout=T)
        assert r.status_code == 403, f"outsider got {r.status_code}"
        nf = requests.post(f"{BASE}/trades/nope-{uuid.uuid4().hex[:6]}/action",
                           params={"action": "accept"}, headers=c["h"], timeout=T)
        assert nf.status_code == 404
        _del_listing(a, la["listing_id"])
        _del_listing(b, lb["listing_id"])


# ---------------- Listings filters / sorting ----------------
class TestListingFilters:
    @pytest.fixture(scope="class")
    def owner(self):
        u = _signup("lsOwner")
        _set_profile(u)
        created = []
        tag = uuid.uuid4().hex[:6]
        created.append(_listing(u, "have", f"TEST_lf_have_{tag}", category="Tools"))
        created.append(_listing(u, "need", f"TEST_lf_need_{tag}", category="home"))
        created.append(_listing(u, "service", f"TEST_lf_service_{tag}", category="Services & Skills"))
        created.append(_listing(u, "need", f"TEST_lf_urgent_{tag}", category="Food & Water",
                                is_emergency=True))
        u["listings"] = created
        u["tag"] = tag
        yield u
        for c in created:
            _del_listing(u, c["listing_id"])

    @pytest.mark.parametrize("kind", ["have", "need", "service"])
    def test_kind_filter(self, owner, kind):
        r = requests.get(f"{BASE}/listings", headers=owner["h"],
                         params={"kind": kind, "mine": "true"}, timeout=T)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert all(d["kind"] == kind for d in data), {d["kind"] for d in data}
        assert any(owner["tag"] in d["title"] for d in data)

    def test_category_case_insensitive(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"],
                         params={"category": "home", "mine": "true"}, timeout=T)
        assert r.status_code == 200
        titles = [d["title"] for d in r.json()]
        assert f"TEST_lf_need_{owner['tag']}" in titles, titles
        assert all(d["category"] == "Home" for d in r.json())
        r2 = requests.get(f"{BASE}/listings", headers=owner["h"],
                          params={"category": "HOME", "mine": "true"}, timeout=T)
        assert r2.status_code == 200
        assert len(r2.json()) == len(r.json())

    def test_q_search(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"],
                         params={"q": f"lf_service_{owner['tag']}", "mine": "true"}, timeout=T)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1 and data[0]["kind"] == "service", data

    def test_mine_true_only_own(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"], params={"mine": "true"}, timeout=T)
        assert r.status_code == 200
        assert all(d["user_id"] == owner["user_id"] for d in r.json())

    def test_mine_requires_auth(self):
        r = requests.get(f"{BASE}/listings", params={"mine": "true"}, timeout=T)
        assert r.status_code == 401, r.status_code

    def test_public_listing_excludes_own(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"], timeout=T)
        assert r.status_code == 200
        assert all(d["user_id"] != owner["user_id"] for d in r.json())

    def test_has_photos_filter(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"],
                         params={"has_photos": "true", "mine": "true"}, timeout=T)
        assert r.status_code == 200
        assert r.json() == [], "own TEST listings have no photos"
        r2 = requests.get(f"{BASE}/listings", params={"has_photos": "true"}, timeout=T)
        assert r2.status_code == 200
        assert all(d.get("photos") for d in r2.json())

    def test_verified_only_filter(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"],
                         params={"verified_only": "true"}, timeout=T)
        assert r.status_code == 200
        assert all((d.get("user_reputation", 0) > 0 or d.get("user_trades", 0) > 0) for d in r.json())

    def test_radius_filter(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"], params={"radius": 25}, timeout=T)
        assert r.status_code == 200
        for d in r.json():
            if d.get("distance_miles") is not None:
                assert d["distance_miles"] <= 25, d

    @pytest.mark.parametrize("sort", ["recent", "closest", "reputation"])
    def test_sort_emergency_floats_top(self, owner, sort):
        r = requests.get(f"{BASE}/listings", params={"sort": sort}, timeout=T)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        flags = [bool(d.get("is_emergency")) for d in data]
        if True in flags:
            last_e = max(i for i, f in enumerate(flags) if f)
            assert all(flags[:last_e + 1]), f"emergency not contiguous at top for sort={sort}"

    def test_sort_reputation_descending(self, owner):
        r = requests.get(f"{BASE}/listings", params={"sort": "reputation"}, timeout=T)
        assert r.status_code == 200
        reps = [d.get("user_reputation") or 0 for d in r.json() if not d.get("is_emergency")]
        assert reps == sorted(reps, reverse=True), reps[:20]

    def test_sort_closest_ascending(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"],
                         params={"sort": "closest"}, timeout=T)
        assert r.status_code == 200
        dists = [d.get("distance_miles") if d.get("distance_miles") is not None else 9999
                 for d in r.json() if not d.get("is_emergency")]
        assert dists == sorted(dists), dists[:20]

    def test_no_mongo_id_leak(self, owner):
        r = requests.get(f"{BASE}/listings", headers=owner["h"], timeout=T)
        assert r.status_code == 200
        assert all("_id" not in d for d in r.json())


# ---------------- Matches / chains ----------------
class TestMatchesChains:
    def test_chains_schema_and_cycle(self):
        users = [_signup(f"ch{i}") for i in range(3)]
        for u in users:
            _set_profile(u)
        tag = uuid.uuid4().hex[:6]
        words = [f"alphaX{tag}", f"betaX{tag}", f"gammaX{tag}"]
        created = []
        # A has alpha, needs gamma ; B has beta, needs alpha ; C has gamma, needs beta
        pairs = [(0, words[0], words[2]), (1, words[1], words[0]), (2, words[2], words[1])]
        for idx, have_w, need_w in pairs:
            created.append((users[idx], _listing(users[idx], "have", f"TEST {have_w}")))
            created.append((users[idx], _listing(users[idx], "need", f"TEST {need_w}")))
        try:
            r = requests.get(f"{BASE}/matches/chains", headers=users[0]["h"], timeout=60)
            assert r.status_code == 200, r.text[:300]
            chains = r.json()
            assert isinstance(chains, list)
            mine = [c for c in chains if tag in c["you"]["listing"]["title"]]
            assert mine, f"expected a 3-way chain for tag {tag}, got {len(chains)} chains"
            c0 = mine[0]
            for key in ("you", "b", "c"):
                assert "listing" in c0[key]
                assert "listing_id" in c0[key]["listing"]
            for key in ("b", "c"):
                assert "user" in c0[key] and c0[key]["user"].get("display_name")
            assert c0["b"]["user"]["user_id"] != c0["c"]["user"]["user_id"]
            assert users[0]["user_id"] not in (c0["b"]["user"]["user_id"], c0["c"]["user"]["user_id"])
        finally:
            for u, l in created:
                _del_listing(u, l["listing_id"])

    def test_chains_empty_for_fresh_user(self):
        u = _signup("chEmpty")
        r = requests.get(f"{BASE}/matches/chains", headers=u["h"], timeout=T)
        assert r.status_code == 200
        assert r.json() == []

    def test_chains_requires_auth(self):
        r = requests.get(f"{BASE}/matches/chains", timeout=T)
        assert r.status_code in (401, 403), r.status_code


# ---------------- Dashboard stats ----------------
class TestDashboardStats:
    KEYS = ["my_haves", "my_needs", "my_services", "my_completed_trades", "my_active_trades",
            "nearby_haves", "nearby_needs", "nearby_services", "has_location", "radius_miles"]

    def test_stats_shape_no_location(self):
        u = _signup("dsNoLoc")
        r = requests.get(f"{BASE}/dashboard/stats", headers=u["h"], timeout=T)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert set(d.keys()) == set(self.KEYS), set(d.keys()) ^ set(self.KEYS)
        assert d["has_location"] is False
        assert d["nearby_haves"] == d["nearby_needs"] == d["nearby_services"] == 0
        assert d["radius_miles"] == 10

    def test_stats_reflect_my_listings_and_trades(self):
        u = _signup("dsLoc")
        _set_profile(u, radius=25)
        before = requests.get(f"{BASE}/dashboard/stats", headers=u["h"], timeout=T).json()
        assert before["has_location"] is True and before["radius_miles"] == 25
        ls = [_listing(u, "have", f"TEST_ds_h_{uuid.uuid4().hex[:6]}"),
              _listing(u, "need", f"TEST_ds_n_{uuid.uuid4().hex[:6]}"),
              _listing(u, "need", f"TEST_ds_n2_{uuid.uuid4().hex[:6]}"),
              _listing(u, "service", f"TEST_ds_s_{uuid.uuid4().hex[:6]}")]
        after = requests.get(f"{BASE}/dashboard/stats", headers=u["h"], timeout=T).json()
        assert after["my_haves"] == before["my_haves"] + 1
        assert after["my_needs"] == before["my_needs"] + 2
        assert after["my_services"] == before["my_services"] + 1
        assert isinstance(after["nearby_haves"], int)

        # active trade counter
        peer = _signup("dsPeer")
        pl = _listing(peer, "have", f"TEST_ds_peer_{uuid.uuid4().hex[:6]}")
        tid = requests.post(f"{BASE}/trades", headers=u["h"], json={
            "my_listing_id": ls[0]["listing_id"], "their_listing_id": pl["listing_id"], "to_user_id": peer["user_id"],
            "message": "TEST"}, timeout=T).json()["trade_id"]
        mid = requests.get(f"{BASE}/dashboard/stats", headers=u["h"], timeout=T).json()
        assert mid["my_active_trades"] == after["my_active_trades"] + 1
        requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"}, headers=peer["h"], timeout=T)
        for who in (u, peer):
            requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"},
                          headers=who["h"], timeout=T)
        end = requests.get(f"{BASE}/dashboard/stats", headers=u["h"], timeout=T).json()
        assert end["my_completed_trades"] == after["my_completed_trades"] + 1
        assert end["my_active_trades"] == after["my_active_trades"]
        for l in ls:
            _del_listing(u, l["listing_id"])
        _del_listing(peer, pl["listing_id"])

    def test_stats_requires_auth(self):
        r = requests.get(f"{BASE}/dashboard/stats", timeout=T)
        assert r.status_code in (401, 403)


# ---------------- Community dashboard ----------------
class TestCommunityDashboard:
    def test_public_rich_schema(self):
        r = requests.get(f"{BASE}/community/dashboard", timeout=T)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("by_kind", "by_category", "emergency", "emergency_count",
                  "completed_trades", "recent_completed_30d", "top_services"):
            assert k in d, f"missing {k}"
        assert isinstance(d["by_kind"], dict)
        assert isinstance(d["by_category"], list)
        assert isinstance(d["emergency"], list)
        assert isinstance(d["emergency_count"], int)
        assert d["emergency_count"] >= len(d["emergency"])
        assert all("_id" not in e for e in d["emergency"])

    def test_recent_completed_30d_increments(self):
        before = requests.get(f"{BASE}/community/dashboard", timeout=T).json()["recent_completed_30d"]
        a, b = _signup("cdA"), _signup("cdB")
        la = _listing(a, "have", f"TEST_cd_a_{uuid.uuid4().hex[:6]}")
        lb = _listing(b, "have", f"TEST_cd_b_{uuid.uuid4().hex[:6]}")
        tid = requests.post(f"{BASE}/trades", headers=a["h"], json={
            "my_listing_id": la["listing_id"], "their_listing_id": lb["listing_id"], "to_user_id": b["user_id"],
            "message": "TEST"}, timeout=T).json()["trade_id"]
        requests.post(f"{BASE}/trades/{tid}/action", params={"action": "accept"}, headers=b["h"], timeout=T)
        for u in (a, b):
            requests.post(f"{BASE}/trades/{tid}/action", params={"action": "complete"},
                          headers=u["h"], timeout=T)
        after = requests.get(f"{BASE}/community/dashboard", timeout=T).json()["recent_completed_30d"]
        _del_listing(a, la["listing_id"])
        _del_listing(b, lb["listing_id"])
        assert after >= before + 1, f"recent_completed_30d {before} -> {after}"


# ---------------- Auth paths ----------------
class TestAuthPaths:
    def test_bearer_and_cookie_both_work(self):
        u = _signup("auth")
        r_h = requests.get(f"{BASE}/auth/me", headers=u["h"], timeout=T)
        assert r_h.status_code == 200 and r_h.json()["email"] == u["email"]
        r_c = requests.get(f"{BASE}/auth/me", cookies=u["cookies"], timeout=T)
        assert r_c.status_code == 200 and r_c.json()["email"] == u["email"]
        r_n = requests.get(f"{BASE}/auth/me", timeout=T)
        assert r_n.status_code in (401, 403)
        r_bad = requests.get(f"{BASE}/auth/me", cookies={"session_token": "garbage"}, timeout=T)
        assert r_bad.status_code == 401

    def test_login_sets_cookie_and_token(self):
        u = _signup("login")
        r = requests.post(f"{BASE}/auth/login", json={"email": u["email"], "password": PW}, timeout=T)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("token")
        assert r.cookies.get("session_token")
        bad = requests.post(f"{BASE}/auth/login", json={"email": u["email"], "password": "wrong-pw"}, timeout=T)
        assert bad.status_code == 401
