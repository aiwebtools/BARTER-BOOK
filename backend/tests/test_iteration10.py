"""Iteration 10 - secrets-based _generate_username regression + AI suggest-category sanity."""
import os
import re
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "Passw0rd!23"
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _signup(client, display_name):
    email = f"TEST_iter10_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(f"{API}/auth/signup", json={
        "email": email, "password": PASSWORD, "display_name": display_name
    })
    assert r.status_code == 200, f"signup failed {r.status_code}: {r.text[:300]}"
    data = r.json()
    token = data.get("token") or data.get("access_token") or (data.get("session") or {}).get("token")
    assert token, f"no token in signup response: {data}"
    return email, token


# ---- Username generation: same display_name x3 must yield unique valid usernames ----
def test_same_display_name_unique_usernames(client):
    usernames = []
    for _ in range(3):
        _, token = _signup(client, "Common Name")
        me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text[:300]
        u = me.json().get("username")
        assert u, "username empty on /auth/me"
        assert USERNAME_RE.match(u), f"username '{u}' does not match pattern"
        assert u.startswith("commonname"), f"unexpected base for '{u}'"
        assert u[len("commonname"):].isdigit(), f"suffix not numeric: {u}"
        assert 100 <= int(u[len("commonname"):]) <= 9999
        usernames.append(u)
    assert len(set(usernames)) == 3, f"usernames collided: {usernames}"


# ---- Username generated from email local-part when display_name is minimal ----
def test_username_present_for_email_seed(client):
    _, token = _signup(client, "Zz")
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    u = me.json().get("username")
    assert u and USERNAME_RE.match(u), f"invalid username: {u}"


# ---- AI category suggestion ----
def test_ai_suggest_category(client):
    _, token = _signup(client, "AI Tester")
    r = client.post(f"{API}/ai/suggest-category", json={"title": "Bicycle helmet"},
                    headers={"Authorization": f"Bearer {token}"}, timeout=60)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    data = r.json()
    assert "category" in data, data
    assert isinstance(data["category"], str) and data["category"].strip()
