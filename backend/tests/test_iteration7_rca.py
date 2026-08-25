"""RCA probe for the iteration-7 notification regression (kept as a regression test).

Default (freshly signed-up) users have NO notify_* fields on their user doc, so
_should_notify's projection returns an empty dict and `if not u: return False`
suppresses EVERY in-app notification until the user PATCHes a pref.
"""
import os
import uuid

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")
PW = "Passw0rd!23"


def _signup(name):
    email = f"TEST_i7rca_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE}/auth/signup", json={"email": email, "password": PW, "display_name": name}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    return {"user_id": d["user"]["user_id"], "h": {"Authorization": f"Bearer {d['token']}"}}


def test_default_user_receives_inapp_notification():
    """A brand-new user with NO notify_* fields must still get in-app notifications."""
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    a = _signup("TEST_i7rca Sender")
    b = _signup("TEST_i7rca Default")
    doc = db.users.find_one({"user_id": b["user_id"]}, {"_id": 0})
    missing = [k for k in ("notify_messages", "notify_trades", "notify_matches") if k not in doc]
    r = requests.post(f"{BASE}/conversations/{b['user_id']}/messages", headers=a["h"],
                      json={"text": "TEST_i7rca default dm"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    ns = requests.get(f"{BASE}/notifications", headers=b["h"], timeout=30).json()
    c.close()
    assert any("TEST_i7rca default dm" in n["text"] for n in ns), (
        f"DEFAULT user got NO in-app notification. Missing pref fields on user doc: {missing}. "
        f"_should_notify projection returns an empty dict -> `if not u: return False`."
    )
