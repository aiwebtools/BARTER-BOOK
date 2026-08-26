"""BarterGrid API — local barter/exchange network."""
import os
import uuid
import math
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Literal

import bcrypt
import jwt
import requests
import resend
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Query, UploadFile, File, Response, Cookie
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---- Config ----
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALG = "HS256"
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "BarterGrid <onboarding@resend.dev>")
APP_PUBLIC_URL = os.environ.get("APP_PUBLIC_URL", "").rstrip("/")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "bartergrid"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="BarterGrid API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bartergrid")

# ---- Storage ----
_storage_key: Optional[str] = None
def init_storage(force: bool = False) -> Optional[str]:
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    if not EMERGENT_LLM_KEY:
        return None
    try:
        r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
        r.raise_for_status()
        _storage_key = r.json()["storage_key"]
        return _storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(500, "Storage not configured")
    r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if r.status_code == 404:
        key = init_storage(force=True)
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    r.raise_for_status()
    return r.json()

def get_object(path: str):
    key = init_storage()
    if not key:
        raise HTTPException(500, "Storage not configured")
    r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if r.status_code == 404:
        key = init_storage(force=True)
        r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")

# ---- Helpers ----
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}" if prefix else uuid.uuid4().hex[:16]

def make_jwt(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALG)

def haversine_miles(lat1, lng1, lat2, lng2) -> float:
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

async def _queue_email(user_id: str, kind: str, subject: str, data: dict = None):
    """Queue an email and (if RESEND_API_KEY is set) actually deliver it via Resend, non-blocking."""
    try:
        u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1, "display_name": 1, "email_notifications": 1, "notify_matches": 1, "notify_messages": 1, "notify_trades": 1})
        if not u or not u.get("email") or u["email"].endswith("@bartergrid.local"):
            return
        if u.get("email_notifications") is False:
            return
        cat_map = {
            "match": "notify_matches",
            "direct_message": "notify_messages", "trade_message": "notify_messages",
            "trade_proposal": "notify_trades", "trade_update": "notify_trades",
            "trade_completed": "notify_trades", "meetup_planned": "notify_trades",
        }
        pref_key = cat_map.get(kind)
        if pref_key and u.get(pref_key) is False:
            return
        qid = new_id()
        await db.email_queue.insert_one({
            "id": qid,
            "user_id": user_id,
            "to_email": u["email"],
            "to_name": u.get("display_name", ""),
            "kind": kind,
            "subject": subject,
            "data": data or {},
            "status": "pending",
            "created_at": now_iso(),
        })
        # Fire real email via Resend if configured
        if RESEND_API_KEY:
            asyncio.create_task(_deliver_email(qid, u["email"], u.get("display_name", ""), kind, subject, data or {}))
    except Exception as e:
        logger.error(f"queue_email failed: {e}")

def _render_email_html(kind: str, name: str, subject: str, data: dict) -> str:
    action_label, action_path = "Open BarterGrid", "/dashboard"
    if kind in ("trade_proposal", "trade_update", "trade_completed", "meetup_planned", "trade_message") and data.get("trade_id"):
        action_label, action_path = "View trade", f"/trades/{data['trade_id']}"
    elif kind == "direct_message" and data.get("from_user"):
        action_label, action_path = "Reply", f"/messages/{data['from_user']}"
    action_url = (APP_PUBLIC_URL + action_path) if APP_PUBLIC_URL else action_path
    preview = data.get("preview") or subject
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0f1512;padding:32px 16px;font-family:Inter,Arial,sans-serif;">
  <tr><td align="center">
    <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#151b18;border:1px solid #23302a;border-radius:20px;overflow:hidden;">
      <tr><td style="padding:28px 32px 8px 32px;">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td style="width:36px;"><div style="width:32px;height:32px;background:#4de0a8;border-radius:8px;color:#0e1a15;text-align:center;line-height:32px;font-weight:800;font-family:Arial,sans-serif;">B</div></td>
          <td style="padding-left:10px;color:#e7ecea;font-weight:700;font-size:16px;">BarterGrid</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:8px 32px 4px 32px;color:#e7ecea;font-size:22px;font-weight:700;line-height:1.25;">{subject}</td></tr>
      <tr><td style="padding:8px 32px 24px 32px;color:#a7b0ac;font-size:14px;line-height:1.5;">Hi {name or 'there'}, {preview}</td></tr>
      <tr><td style="padding:0 32px 28px 32px;">
        <a href="{action_url}" style="display:inline-block;background:#4de0a8;color:#0e1a15;padding:12px 22px;border-radius:999px;font-weight:700;text-decoration:none;font-size:14px;">{action_label} →</a>
      </td></tr>
      <tr><td style="padding:0 32px 28px 32px;border-top:1px solid #23302a;">
        <p style="color:#7d867f;font-size:12px;line-height:1.6;margin:16px 0 0 0;">You're getting this because you're on BarterGrid — a free bartering service for the people, by the people. Manage or turn off email alerts anytime in Settings.</p>
        <p style="color:#7d867f;font-size:12px;margin:8px 0 0 0;">Made with ♥ by <a href="https://aiwebtools.app" style="color:#4de0a8;text-decoration:none;">aiwebtools.app</a></p>
      </td></tr>
    </table>
  </td></tr>
</table>
""".strip()

async def _deliver_email(qid: str, to_email: str, to_name: str, kind: str, subject: str, data: dict):
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": f"[BarterGrid] {subject}",
            "html": _render_email_html(kind, to_name, subject, data),
        }
        r = await asyncio.to_thread(resend.Emails.send, params)
        await db.email_queue.update_one({"id": qid}, {"$set": {"status": "sent", "provider_id": r.get("id"), "sent_at": now_iso()}})
    except Exception as e:
        logger.error(f"resend send failed for {to_email}: {e}")
        await db.email_queue.update_one({"id": qid}, {"$set": {"status": "failed", "error": str(e), "failed_at": now_iso()}})

async def _should_notify(user_id: str, kind: str) -> bool:
    """Check user's in-app notification preferences. Defaults to True when field is unset."""
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1, "notify_matches": 1, "notify_messages": 1, "notify_trades": 1})
    if u is None:
        return False
    cat_map = {
        "match": "notify_matches",
        "message": "notify_messages",
        "trade_proposal": "notify_trades", "trade": "notify_trades",
        "meetup": "notify_trades", "rating_request": "notify_trades",
        "referral_verified": None,  # always notify
    }
    pref_key = cat_map.get(kind)
    if pref_key is not None and u.get(pref_key) is False:
        return False
    return True

async def _add_notification(user_id: str, ntype: str, text: str, **extra):
    """Insert an in-app notification only if user preferences allow."""
    if not await _should_notify(user_id, ntype):
        return
    doc = {"id": new_id(), "user_id": user_id, "type": ntype, "text": text, "read": False, "created_at": now_iso(), **extra}
    await db.notifications.insert_one(doc)

# ---- Models ----
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    display_name: str
    picture: Optional[str] = None
    bio: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    country: Optional[str] = ""
    approx_lat: Optional[float] = None
    approx_lng: Optional[float] = None
    search_radius_miles: int = 10
    auth_provider: str = "email"
    email_verified: bool = False
    phone_verified: bool = False
    reputation_score: float = 0.0
    successful_trades: int = 0
    ratings_count: int = 0
    role: str = "user"
    created_at: str

class SignupIn(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    referral_code: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    approx_lat: Optional[float] = None
    approx_lng: Optional[float] = None
    search_radius_miles: Optional[int] = None
    picture: Optional[str] = None
    # Storefront customization
    store_name: Optional[str] = None
    store_tagline: Optional[str] = None
    banner_photo: Optional[str] = None
    accent_color: Optional[str] = None
    # Payment / send-money handles
    cashapp_tag: Optional[str] = None
    venmo_tag: Optional[str] = None
    paypal_link: Optional[str] = None
    bitcoin_address: Optional[str] = None
    solana_address: Optional[str] = None
    ethereum_address: Optional[str] = None
    accepts_donations: Optional[bool] = None
    # Notification preferences
    email_notifications: Optional[bool] = None
    notify_matches: Optional[bool] = None
    notify_messages: Optional[bool] = None
    notify_trades: Optional[bool] = None

class ListingIn(BaseModel):
    kind: str  # 'have' | 'need' | 'service' (case-insensitive, normalized server-side)
    title: str = Field(min_length=1, max_length=120)
    description: str = ""
    category: str
    condition: Optional[str] = None
    quantity: Optional[str] = None
    photos: List[str] = []
    wants: List[str] = []
    tags: List[str] = []
    urgency: Optional[str] = "normal"
    is_active: bool = True
    # Shipping
    ships: bool = False
    shipping_fee: Optional[str] = None
    shipping_notes: Optional[str] = None

class ListingOut(ListingIn):
    listing_id: str
    user_id: str
    user_display_name: str
    user_city: str
    user_reputation: float
    user_trades: int
    approx_lat: Optional[float] = None
    approx_lng: Optional[float] = None
    distance_miles: Optional[float] = None
    created_at: str

class TradeProposalIn(BaseModel):
    to_user_id: str
    my_listing_id: str
    their_listing_id: str
    message: Optional[str] = ""

class TradeMessageIn(BaseModel):
    text: str = Field(min_length=1)

class MeetupIn(BaseModel):
    location_name: str
    date: str  # ISO
    time: str  # HH:MM
    location_type: str = "public"  # library, police_station, community_center, public

class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5)
    tags: List[str] = []
    comment: Optional[str] = ""

class ReportIn(BaseModel):
    target_type: Literal["listing", "user", "trade"]
    target_id: str
    reason: str
    description: Optional[str] = ""

# ---- Auth Dependency ----
async def get_current_user(authorization: Optional[str] = Header(None), session_token: Optional[str] = Cookie(None)) -> dict:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token
    if not token:
        raise HTTPException(401, "Not authenticated")

    # Try JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload.get("sub")
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        if user:
            if user.get("role") in ("deleted", "suspended"):
                raise HTTPException(401, "Account disabled")
            return user
    except HTTPException:
        raise
    except Exception:
        pass

    # Try session_token (Emergent OAuth)
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if sess:
        expires_at = sess.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at > datetime.now(timezone.utc):
            user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
            if user:
                if user.get("role") in ("deleted", "suspended"):
                    raise HTTPException(401, "Account disabled")
                return user
    raise HTTPException(401, "Invalid or expired session")

async def get_optional_user(authorization: Optional[str] = Header(None), session_token: Optional[str] = Cookie(None)) -> Optional[dict]:
    """Same as get_current_user but returns None instead of raising when unauthenticated."""
    try:
        return await get_current_user(authorization, session_token)
    except HTTPException:
        return None

async def get_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return user

async def _generate_username(seed: str) -> str:
    """Generate a unique, anon-friendly username from a seed (email/name)."""
    import re, random
    base = re.sub(r"[^a-z0-9]", "", (seed or "trader").lower())[:12] or "trader"
    for _ in range(10):
        candidate = f"{base}{random.randint(100, 9999)}"
        if not await db.users.find_one({"username": candidate}):
            return candidate
    return f"trader{uuid.uuid4().hex[:6]}"

# ---- Auth Routes ----
@api.post("/auth/signup")
async def signup(inp: SignupIn):
    existing = await db.users.find_one({"email": inp.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    referral_code = uuid.uuid4().hex[:8].upper()
    # Auto-generate unique @username from the display name or email local-part
    username = await _generate_username(inp.display_name or inp.email.split("@")[0])
    # link referrer if provided
    referred_by = None
    if inp.referral_code:
        ref = await db.users.find_one({"referral_code": inp.referral_code.upper()}, {"_id": 0})
        if ref:
            referred_by = ref["user_id"]
    doc = {
        "user_id": user_id,
        "email": inp.email.lower(),
        "display_name": inp.display_name,
        "username": username,
        "first_name": (inp.display_name or "").split(" ")[0][:40] or None,
        "password_hash": bcrypt.hashpw(inp.password.encode(), bcrypt.gensalt()).decode(),
        "auth_provider": "email",
        "email_verified": False,
        "phone_verified": False,
        "picture": None,
        "bio": "",
        "city": "", "state": "", "country": "",
        "approx_lat": None, "approx_lng": None,
        "search_radius_miles": 10,
        "reputation_score": 0.0,
        "successful_trades": 0,
        "ratings_count": 0,
        "role": "user",
        "referral_code": referral_code,
        "referred_by": referred_by,
        "verified_referral": False,
        "email_notifications": True,
        "notify_matches": True,
        "notify_messages": True,
        "notify_trades": True,
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    token = make_jwt(user_id)
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return {"token": token, "user": doc}

@api.post("/auth/login")
async def login(inp: LoginIn):
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user or not user.get("password_hash"):
        raise HTTPException(401, "Invalid credentials")
    if not bcrypt.checkpw(inp.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Invalid credentials")
    token = make_jwt(user["user_id"])
    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"token": token, "user": user}

@api.post("/auth/google/session")
async def google_session(response: Response, x_session_id: str = Header(..., alias="X-Session-ID")):
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    r = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": x_session_id}, timeout=10)
    if r.status_code != 200:
        raise HTTPException(401, "Invalid session")
    data = r.json()
    email = data["email"].lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {"picture": data.get("picture"), "display_name": data.get("name") or existing.get("display_name")}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        username = await _generate_username(data.get("name") or email.split("@")[0])
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "display_name": data.get("name", email.split("@")[0]),
            "username": username,
            "first_name": (data.get("name") or "").split(" ")[0][:40] or None,
            "picture": data.get("picture"),
            "auth_provider": "google",
            "email_verified": True,
            "phone_verified": False,
            "bio": "",
            "city": "", "state": "", "country": "",
            "approx_lat": None, "approx_lng": None,
            "search_radius_miles": 10,
            "reputation_score": 0.0,
            "successful_trades": 0,
            "ratings_count": 0,
            "role": "user",
            "referral_code": uuid.uuid4().hex[:8].upper(),
            "referred_by": None,
            "verified_referral": False,
            "email_notifications": True,
            "notify_matches": True,
            "notify_messages": True,
            "notify_trades": True,
            "created_at": now_iso(),
        })
    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": now_iso(),
    })
    response.set_cookie("session_token", session_token, max_age=7*24*3600, httponly=True, secure=True, samesite="none", path="/")
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"user": user, "token": session_token}

@api.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("session_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---- Profile ----
@api.patch("/profile")
async def update_profile(inp: ProfileUpdate, user: dict = Depends(get_current_user)):
    update = {k: v for k, v in inp.model_dump().items() if v is not None}
    # Username validation + uniqueness
    if "username" in update:
        import re
        uname = update["username"].lower().strip()
        if not re.match(r"^[a-z0-9_]{3,20}$", uname):
            raise HTTPException(422, "Username must be 3-20 chars: lowercase, numbers, underscore")
        clash = await db.users.find_one({"username": uname, "user_id": {"$ne": user["user_id"]}}, {"_id": 0, "user_id": 1})
        if clash:
            raise HTTPException(409, "Username already taken")
        update["username"] = uname
    if update:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return u

@api.get("/users/{user_id}")
async def get_user(user_id: str, viewer: Optional[dict] = Depends(get_optional_user)):
    # Whitelist public fields to avoid leaking referral_code, referred_by, role, email etc.
    projection = {
        "_id": 0,
        "user_id": 1, "display_name": 1, "first_name": 1, "username": 1,
        "picture": 1, "bio": 1, "city": 1, "state": 1, "country": 1,
        "reputation_score": 1, "successful_trades": 1, "ratings_count": 1,
        "verified_referral": 1, "email_verified": 1, "phone_verified": 1,
        "store_name": 1, "store_tagline": 1, "banner_photo": 1, "accent_color": 1,
        "cashapp_tag": 1, "venmo_tag": 1, "paypal_link": 1,
        "bitcoin_address": 1, "solana_address": 1, "ethereum_address": 1,
        "accepts_donations": 1, "created_at": 1,
    }
    u = await db.users.find_one({"user_id": user_id}, projection)
    if not u:
        raise HTTPException(404, "User not found")
    listings = await db.listings.find({"user_id": user_id, "is_active": True}, {"_id": 0}).sort("created_at", -1).limit(60).to_list(60)
    u["listings"] = listings
    return u

# ---- Uploads ----
@api.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = (file.filename or "bin").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        raise HTTPException(400, "Only images allowed")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 8MB)")
    file_id = uuid.uuid4().hex
    path = f"{APP_NAME}/uploads/{user['user_id']}/{file_id}.{ext}"
    result = put_object(path, data, file.content_type or f"image/{ext}")
    await db.files.insert_one({
        "id": file_id,
        "storage_path": result["path"],
        "user_id": user["user_id"],
        "content_type": file.content_type or f"image/{ext}",
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": now_iso(),
    })
    return {"file_id": file_id, "path": result["path"]}

@api.get("/files/{file_id}")
async def download_file(file_id: str):
    rec = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Not found")
    data, ct = get_object(rec["storage_path"])
    return Response(content=data, media_type=rec.get("content_type", ct))

# ---- Listings ----
async def enrich_listing(doc: dict, viewer: Optional[dict] = None) -> dict:
    owner = await db.users.find_one({"user_id": doc["user_id"]}, {"_id": 0})
    if not owner:
        return doc
    dist = None
    if viewer and viewer.get("approx_lat") and owner.get("approx_lat"):
        dist = round(haversine_miles(viewer["approx_lat"], viewer["approx_lng"], owner["approx_lat"], owner["approx_lng"]), 1)
    return {
        **doc,
        "user_display_name": owner.get("display_name", ""),
        "user_city": owner.get("city", ""),
        "user_reputation": owner.get("reputation_score", 0.0),
        "user_trades": owner.get("successful_trades", 0),
        "approx_lat": owner.get("approx_lat"),
        "approx_lng": owner.get("approx_lng"),
        "distance_miles": dist,
    }

@api.post("/listings")
async def create_listing(inp: ListingIn, user: dict = Depends(get_current_user)):
    # Anti-spam rate limit: max 20 listings per user per rolling 24h
    yesterday_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_count = await db.listings.count_documents({
        "user_id": user["user_id"],
        "created_at": {"$gte": yesterday_iso},
    })
    if recent_count >= 20:
        raise HTTPException(429, "Daily listing limit reached (20/day). Please try again tomorrow.")
    data = inp.model_dump()
    data["kind"] = (data.get("kind") or "have").lower()
    if data["kind"] not in ("have", "need", "service"):
        raise HTTPException(422, "kind must be have|need|service")
    lid = new_id("lst_")
    doc = {"listing_id": lid, "user_id": user["user_id"], **data, "created_at": now_iso()}
    await db.listings.insert_one(doc)
    doc.pop("_id", None)
    return await enrich_listing(doc, user)

@api.get("/listings")
async def list_listings(kind: Optional[str] = None, category: Optional[str] = None, q: Optional[str] = None,
                        radius: Optional[int] = None, mine: bool = False,
                        verified_only: bool = False, has_photos: bool = False,
                        sort: str = "recent",
                        user: Optional[dict] = Depends(get_optional_user)):
    query = {"is_active": True}
    if kind:
        query["kind"] = kind.lower()
    if category:
        query["category"] = category
    if mine:
        if not user:
            raise HTTPException(401, "Login required to view your listings")
        query["user_id"] = user["user_id"]
    elif user:
        # exclude own listings + blocked users
        blocked = await db.blocks.find({"$or": [{"blocker": user["user_id"]}, {"blocked": user["user_id"]}]}).to_list(1000)
        blocked_ids = set()
        for b in blocked:
            blocked_ids.add(b["blocker"] if b["blocked"] == user["user_id"] else b["blocked"])
        query["user_id"] = {"$nin": list(blocked_ids) + [user["user_id"]]} if blocked_ids else {"$ne": user["user_id"]}
    if q:
        query["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"description": {"$regex": q, "$options": "i"}}, {"tags": {"$regex": q, "$options": "i"}}]
    if has_photos:
        query["photos.0"] = {"$exists": True}
    docs = await db.listings.find(query, {"_id": 0}).sort("created_at", -1).limit(400).to_list(400)
    enriched = [await enrich_listing(d, user) for d in docs]
    if verified_only:
        enriched = [e for e in enriched if e.get("user_reputation", 0) > 0 or e.get("user_trades", 0) > 0]
    if radius and user and user.get("approx_lat"):
        enriched = [e for e in enriched if e.get("distance_miles") is None or e["distance_miles"] <= radius]
    # sorting
    if sort == "closest":
        enriched.sort(key=lambda e: (e.get("distance_miles") if e.get("distance_miles") is not None else 9999))
    elif sort == "reputation":
        enriched.sort(key=lambda e: -(e.get("user_reputation") or 0))
    # else 'recent' — already sorted by created_at desc
    return enriched[:200]

@api.get("/listings/{listing_id}")
async def get_listing(listing_id: str, user: dict = Depends(get_current_user)):
    doc = await db.listings.find_one({"listing_id": listing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    return await enrich_listing(doc, user)

@api.patch("/listings/{listing_id}")
async def update_listing(listing_id: str, inp: ListingIn, user: dict = Depends(get_current_user)):
    doc = await db.listings.find_one({"listing_id": listing_id})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(403, "Not your listing")
    data = inp.model_dump()
    data["kind"] = (data.get("kind") or "have").lower()
    await db.listings.update_one({"listing_id": listing_id}, {"$set": data})
    doc = await db.listings.find_one({"listing_id": listing_id}, {"_id": 0})
    return await enrich_listing(doc, user)

@api.delete("/listings/{listing_id}")
async def delete_listing(listing_id: str, user: dict = Depends(get_current_user)):
    doc = await db.listings.find_one({"listing_id": listing_id})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["user_id"] and user.get("role") != "admin":
        raise HTTPException(403, "Not allowed")
    await db.listings.delete_one({"listing_id": listing_id})
    return {"ok": True}

# ---- Matching Engine ----
def _tokens(text: str) -> set:
    return {t.strip().lower() for t in text.replace(",", " ").split() if len(t.strip()) > 2}

def _match_score(my_have: dict, their_need_terms: set, their_have: dict, my_need_terms: set) -> tuple[int, str]:
    """Score how well my_have satisfies their needs, and their_have satisfies mine."""
    score = 0
    # my_have title tokens vs their need terms
    my_have_tokens = _tokens(my_have["title"] + " " + " ".join(my_have.get("tags", [])))
    their_have_tokens = _tokens(their_have["title"] + " " + " ".join(their_have.get("tags", [])))
    if my_have_tokens & their_need_terms:
        score += 3
    if their_have_tokens & my_need_terms:
        score += 3
    if my_have["category"] == their_have.get("category"):
        score += 1
    label = "Possible Match"
    if score >= 6:
        label = "Excellent Match"
    elif score >= 4:
        label = "Strong Match"
    return score, label

@api.get("/matches")
async def get_matches(user: dict = Depends(get_current_user)):
    """Find potential 2-way barter matches."""
    my_haves = await db.listings.find({"user_id": user["user_id"], "kind": "have", "is_active": True}, {"_id": 0}).to_list(100)
    my_needs = await db.listings.find({"user_id": user["user_id"], "kind": "need", "is_active": True}, {"_id": 0}).to_list(100)
    my_services = await db.listings.find({"user_id": user["user_id"], "kind": "service", "is_active": True}, {"_id": 0}).to_list(100)

    my_have_all = my_haves + my_services
    my_need_terms = set()
    for n in my_needs:
        my_need_terms |= _tokens(n["title"] + " " + " ".join(n.get("tags", [])))
        # also add wants from haves as additional needs
    for h in my_haves:
        for w in h.get("wants", []):
            my_need_terms |= _tokens(w)

    matches = []
    # find other users' listings
    others_haves = await db.listings.find({"user_id": {"$ne": user["user_id"]}, "kind": {"$in": ["have", "service"]}, "is_active": True}, {"_id": 0}).to_list(500)
    others_needs = await db.listings.find({"user_id": {"$ne": user["user_id"]}, "kind": "need", "is_active": True}, {"_id": 0}).to_list(500)

    # group other users' needs
    needs_by_user = {}
    for n in others_needs:
        needs_by_user.setdefault(n["user_id"], []).append(n)
    haves_by_user = {}
    for h in others_haves:
        haves_by_user.setdefault(h["user_id"], []).append(h)

    seen_pairs = set()
    for my_have in my_have_all:
        for other_have in others_haves:
            other_uid = other_have["user_id"]
            # what does other need
            their_need_terms = set()
            for n in needs_by_user.get(other_uid, []):
                their_need_terms |= _tokens(n["title"] + " " + " ".join(n.get("tags", [])))
            for h in haves_by_user.get(other_uid, []):
                for w in h.get("wants", []):
                    their_need_terms |= _tokens(w)
            score, label = _match_score(my_have, their_need_terms, other_have, my_need_terms)
            if score >= 3:
                pair_key = (my_have["listing_id"], other_have["listing_id"])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                enriched_other = await enrich_listing(other_have, user)
                matches.append({
                    "my_listing": my_have,
                    "their_listing": enriched_other,
                    "score": score,
                    "label": label,
                })
    matches.sort(key=lambda m: -m["score"])
    return matches[:50]

# ---- Trades ----
@api.post("/trades")
async def propose_trade(inp: TradeProposalIn, user: dict = Depends(get_current_user)):
    my_l = await db.listings.find_one({"listing_id": inp.my_listing_id, "user_id": user["user_id"]}, {"_id": 0})
    their_l = await db.listings.find_one({"listing_id": inp.their_listing_id, "user_id": inp.to_user_id}, {"_id": 0})
    if not my_l or not their_l:
        raise HTTPException(400, "Invalid listings")
    tid = new_id("trd_")
    doc = {
        "trade_id": tid,
        "proposer_id": user["user_id"],
        "recipient_id": inp.to_user_id,
        "my_listing": my_l,
        "their_listing": their_l,
        "status": "proposed",
        "meetup": None,
        "proposer_completed": False,
        "recipient_completed": False,
        "proposer_rated": False,
        "recipient_rated": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.trades.insert_one(doc)
    if inp.message:
        await db.trade_messages.insert_one({
            "id": new_id(), "trade_id": tid, "user_id": user["user_id"], "text": inp.message, "created_at": now_iso()
        })
    await _add_notification(inp.to_user_id, "trade_proposal", f"{user['display_name']} proposed a trade: {my_l['title']} ↔ {their_l['title']}", trade_id=tid)
    await _queue_email(inp.to_user_id, "trade_proposal", f"{user['display_name']} sent you a trade proposal", {"trade_id": tid, "my_title": my_l['title'], "their_title": their_l['title']})
    doc.pop("_id", None)
    return doc

@api.get("/trades")
async def list_trades(user: dict = Depends(get_current_user)):
    trades = await db.trades.find({"$or": [{"proposer_id": user["user_id"]}, {"recipient_id": user["user_id"]}]}, {"_id": 0}).sort("updated_at", -1).to_list(200)
    for t in trades:
        other_id = t["recipient_id"] if t["proposer_id"] == user["user_id"] else t["proposer_id"]
        other = await db.users.find_one({"user_id": other_id}, {"_id": 0, "password_hash": 0})
        t["other_user"] = other
        t["role"] = "proposer" if t["proposer_id"] == user["user_id"] else "recipient"
    return trades

@api.get("/trades/{trade_id}")
async def get_trade(trade_id: str, user: dict = Depends(get_current_user)):
    t = await db.trades.find_one({"trade_id": trade_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Not found")
    if user["user_id"] not in (t["proposer_id"], t["recipient_id"]):
        raise HTTPException(403, "Not your trade")
    other_id = t["recipient_id"] if t["proposer_id"] == user["user_id"] else t["proposer_id"]
    t["other_user"] = await db.users.find_one({"user_id": other_id}, {"_id": 0, "password_hash": 0})
    t["role"] = "proposer" if t["proposer_id"] == user["user_id"] else "recipient"
    return t

@api.post("/trades/{trade_id}/action")
async def trade_action(trade_id: str, action: str = Query(...), user: dict = Depends(get_current_user)):
    t = await db.trades.find_one({"trade_id": trade_id})
    if not t:
        raise HTTPException(404, "Not found")
    if user["user_id"] not in (t["proposer_id"], t["recipient_id"]):
        raise HTTPException(403)
    other_id = t["recipient_id"] if user["user_id"] == t["proposer_id"] else t["proposer_id"]
    updates = {"updated_at": now_iso()}
    notif_text = None
    notif_type = "trade"
    if action == "accept" and user["user_id"] == t["recipient_id"] and t["status"] == "proposed":
        updates["status"] = "accepted"
        notif_text = f"{user['display_name']} accepted your trade proposal!"
    elif action == "decline" and user["user_id"] == t["recipient_id"] and t["status"] == "proposed":
        updates["status"] = "declined"
        notif_text = f"{user['display_name']} declined your trade proposal."
    elif action == "cancel":
        updates["status"] = "cancelled"
        notif_text = f"{user['display_name']} cancelled the trade."
    elif action == "complete":
        role = "proposer" if user["user_id"] == t["proposer_id"] else "recipient"
        updates[f"{role}_completed"] = True
        p_done = updates.get("proposer_completed", t.get("proposer_completed", False))
        r_done = updates.get("recipient_completed", t.get("recipient_completed", False))
        if p_done and r_done:
            updates["status"] = "completed"
            await db.users.update_one({"user_id": t["proposer_id"]}, {"$inc": {"successful_trades": 1}})
            await db.users.update_one({"user_id": t["recipient_id"]}, {"$inc": {"successful_trades": 1}})
            # notify both to rate + trade_completed email
            for uid in (t["proposer_id"], t["recipient_id"]):
                other_uid = t["recipient_id"] if uid == t["proposer_id"] else t["proposer_id"]
                other_u = await db.users.find_one({"user_id": other_uid}, {"_id": 0})
                await _add_notification(uid, "rating_request", f"Trade complete! How did it go with {other_u['display_name']}?", trade_id=trade_id)
                await _queue_email(uid, "trade_completed", f"Your trade with {other_u['display_name']} is complete", {"trade_id": trade_id})
            # Referral verification: first trade for a referred user
            for uid in (t["proposer_id"], t["recipient_id"]):
                u = await db.users.find_one({"user_id": uid}, {"_id": 0})
                if u and u.get("referred_by") and not u.get("verified_referral"):
                    await db.users.update_one({"user_id": uid}, {"$set": {"verified_referral": True}})
                    await db.users.update_one({"user_id": u["referred_by"]}, {"$set": {"verified_referral": True}})
                    await db.notifications.insert_one({
                        "id": new_id(), "user_id": u["referred_by"], "type": "referral_verified",
                        "text": f"{u['display_name']} completed their first trade — you both earned a Verified badge!",
                        "read": False, "created_at": now_iso()
                    })
                    await db.notifications.insert_one({
                        "id": new_id(), "user_id": uid, "type": "referral_verified",
                        "text": "You completed your first trade! You've earned a Verified badge.",
                        "read": False, "created_at": now_iso()
                    })
        else:
            notif_text = f"{user['display_name']} marked the trade complete on their side — confirm from your side to finish."
    else:
        raise HTTPException(400, f"Invalid action or state: {action}")
    if notif_text:
        await _add_notification(other_id, notif_type, notif_text, trade_id=trade_id)
        # queue email (fire-and-forget; actual delivery requires provider key)
        await _queue_email(other_id, "trade_update", notif_text, {"trade_id": trade_id})
    await db.trades.update_one({"trade_id": trade_id}, {"$set": updates})
    return await get_trade(trade_id, user)

@api.post("/trades/{trade_id}/meetup")
async def set_meetup(trade_id: str, inp: MeetupIn, user: dict = Depends(get_current_user)):
    t = await db.trades.find_one({"trade_id": trade_id})
    if not t:
        raise HTTPException(404)
    if user["user_id"] not in (t["proposer_id"], t["recipient_id"]):
        raise HTTPException(403)
    if t["status"] not in ("accepted", "meetup_planned"):
        raise HTTPException(400, "Trade must be accepted first")
    await db.trades.update_one({"trade_id": trade_id}, {"$set": {"meetup": inp.model_dump(), "status": "meetup_planned", "updated_at": now_iso()}})
    other_id = t["recipient_id"] if user["user_id"] == t["proposer_id"] else t["proposer_id"]
    await _add_notification(other_id, "meetup", f"Meetup planned: {inp.location_name} on {inp.date} at {inp.time}", trade_id=trade_id)
    await _queue_email(other_id, "meetup_planned", f"Meetup scheduled with {user['display_name']}", {"trade_id": trade_id, "location": inp.location_name, "date": inp.date, "time": inp.time})
    return await get_trade(trade_id, user)

# ---- Messages ----
@api.get("/trades/{trade_id}/messages")
async def get_messages(trade_id: str, user: dict = Depends(get_current_user)):
    t = await db.trades.find_one({"trade_id": trade_id})
    if not t or user["user_id"] not in (t["proposer_id"], t["recipient_id"]):
        raise HTTPException(403)
    msgs = await db.trade_messages.find({"trade_id": trade_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return msgs

@api.post("/trades/{trade_id}/messages")
async def post_message(trade_id: str, inp: TradeMessageIn, user: dict = Depends(get_current_user)):
    t = await db.trades.find_one({"trade_id": trade_id})
    if not t or user["user_id"] not in (t["proposer_id"], t["recipient_id"]):
        raise HTTPException(403)
    if not inp.text.strip():
        raise HTTPException(422, "Message cannot be blank")
    msg = {"id": new_id(), "trade_id": trade_id, "user_id": user["user_id"], "user_name": user["display_name"], "text": inp.text.strip(), "created_at": now_iso()}
    await db.trade_messages.insert_one(msg)
    other = t["recipient_id"] if t["proposer_id"] == user["user_id"] else t["proposer_id"]
    await _add_notification(other, "message", f"{user['display_name']}: {inp.text[:60]}", trade_id=trade_id)
    await _queue_email(other, "trade_message", f"New message from {user['display_name']}", {"trade_id": trade_id, "preview": inp.text[:140]})
    msg.pop("_id", None)
    return msg

# ---- Ratings ----
@api.post("/trades/{trade_id}/rate")
async def rate_trade(trade_id: str, inp: RatingIn, user: dict = Depends(get_current_user)):
    t = await db.trades.find_one({"trade_id": trade_id})
    if not t or user["user_id"] not in (t["proposer_id"], t["recipient_id"]):
        raise HTTPException(403)
    if t["status"] != "completed":
        raise HTTPException(400, "Trade must be completed")
    role = "proposer" if user["user_id"] == t["proposer_id"] else "recipient"
    if t.get(f"{role}_rated"):
        raise HTTPException(400, "Already rated")
    other = t["recipient_id"] if role == "proposer" else t["proposer_id"]
    rating = {
        "id": new_id(),
        "trade_id": trade_id,
        "rater_id": user["user_id"],
        "rated_id": other,
        "stars": inp.stars,
        "tags": inp.tags,
        "comment": inp.comment,
        "created_at": now_iso(),
    }
    await db.ratings.insert_one(rating)
    await db.trades.update_one({"trade_id": trade_id}, {"$set": {f"{role}_rated": True}})
    # recompute rated user reputation
    ratings = await db.ratings.find({"rated_id": other}).to_list(1000)
    avg = sum(r["stars"] for r in ratings) / len(ratings)
    await db.users.update_one({"user_id": other}, {"$set": {"reputation_score": round(avg, 2), "ratings_count": len(ratings)}})
    return {"ok": True}

@api.get("/users/{user_id}/ratings")
async def user_ratings(user_id: str, _: dict = Depends(get_current_user)):
    rs = await db.ratings.find({"rated_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return rs

# ---- Reports / Blocks ----
@api.post("/reports")
async def report(inp: ReportIn, user: dict = Depends(get_current_user)):
    rid = new_id("rep_")
    await db.reports.insert_one({"id": rid, "reporter_id": user["user_id"], **inp.model_dump(), "status": "open", "created_at": now_iso()})
    return {"ok": True, "report_id": rid}

@api.post("/blocks/{other_user_id}")
async def block_user(other_user_id: str, user: dict = Depends(get_current_user)):
    await db.blocks.update_one({"blocker": user["user_id"], "blocked": other_user_id}, {"$set": {"blocker": user["user_id"], "blocked": other_user_id, "created_at": now_iso()}}, upsert=True)
    return {"ok": True}

@api.delete("/blocks/{other_user_id}")
async def unblock_user(other_user_id: str, user: dict = Depends(get_current_user)):
    await db.blocks.delete_one({"blocker": user["user_id"], "blocked": other_user_id})
    return {"ok": True}

# ---- Notifications ----
@api.get("/notifications")
async def list_notifs(user: dict = Depends(get_current_user)):
    ns = await db.notifications.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return ns

@api.post("/notifications/read")
async def mark_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["user_id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}

@api.delete("/notifications")
async def clear_notifs(user: dict = Depends(get_current_user)):
    r = await db.notifications.delete_many({"user_id": user["user_id"]})
    return {"ok": True, "deleted": r.deleted_count}

@api.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    # Soft: mark listings inactive; remove personal data; keep trade history for other party integrity
    await db.listings.update_many({"user_id": uid}, {"$set": {"is_active": False}})
    await db.notifications.delete_many({"user_id": uid})
    await db.user_sessions.delete_many({"user_id": uid})
    await db.users.update_one({"user_id": uid}, {"$set": {
        "email": f"deleted-{uid}@bartergrid.local",
        "password_hash": "",
        "display_name": "[deleted]",
        "picture": None, "bio": "",
        "cashapp_tag": None, "venmo_tag": None, "paypal_link": None,
        "bitcoin_address": None, "solana_address": None, "ethereum_address": None,
        "role": "deleted",
    }})
    return {"ok": True}

# ---- Community stats ----
@api.get("/community/stats")
async def community_stats(user: Optional[dict] = Depends(get_optional_user)):
    total_users = await db.users.count_documents({"role": {"$ne": "deleted"}})
    total_listings = await db.listings.count_documents({"is_active": True})
    total_haves = await db.listings.count_documents({"kind": "have", "is_active": True})
    total_needs = await db.listings.count_documents({"kind": "need", "is_active": True})
    total_services = await db.listings.count_documents({"kind": "service", "is_active": True})
    completed_trades = await db.trades.count_documents({"status": "completed"})
    return {
        "total_users": total_users,
        "active_listings": total_listings,
        "haves": total_haves,
        "needs": total_needs,
        "services": total_services,
        "completed_trades": completed_trades,
    }

@api.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    """Personal dashboard stats — accurate to THIS user's own listings + nearby counts within their radius."""
    uid = user["user_id"]
    mine_haves = await db.listings.count_documents({"user_id": uid, "kind": "have", "is_active": True})
    mine_needs = await db.listings.count_documents({"user_id": uid, "kind": "need", "is_active": True})
    mine_services = await db.listings.count_documents({"user_id": uid, "kind": "service", "is_active": True})
    my_trades = await db.trades.count_documents({"$or": [{"proposer_id": uid}, {"recipient_id": uid}], "status": "completed"})
    active_trades = await db.trades.count_documents({"$or": [{"proposer_id": uid}, {"recipient_id": uid}], "status": {"$nin": ["completed", "cancelled", "declined"]}})

    # nearby counts — only meaningful if user has coordinates
    nearby_haves = nearby_needs = nearby_services = 0
    if user.get("approx_lat") is not None and user.get("approx_lng") is not None:
        radius = user.get("search_radius_miles") or 10
        cursor = db.listings.find({"user_id": {"$ne": uid}, "is_active": True}, {"_id": 0, "kind": 1, "user_id": 1}).limit(2000)
        others = await cursor.to_list(2000)
        # bulk fetch owner coords
        owner_ids = list({d["user_id"] for d in others})
        owners = {u["user_id"]: u async for u in db.users.find({"user_id": {"$in": owner_ids}}, {"_id": 0, "user_id": 1, "approx_lat": 1, "approx_lng": 1})}
        for d in others:
            o = owners.get(d["user_id"])
            if not o or o.get("approx_lat") is None:
                continue
            dist = haversine_miles(user["approx_lat"], user["approx_lng"], o["approx_lat"], o["approx_lng"])
            if dist <= radius:
                if d["kind"] == "have": nearby_haves += 1
                elif d["kind"] == "need": nearby_needs += 1
                elif d["kind"] == "service": nearby_services += 1

    return {
        "my_haves": mine_haves,
        "my_needs": mine_needs,
        "my_services": mine_services,
        "my_completed_trades": my_trades,
        "my_active_trades": active_trades,
        "nearby_haves": nearby_haves,
        "nearby_needs": nearby_needs,
        "nearby_services": nearby_services,
        "has_location": user.get("approx_lat") is not None,
        "radius_miles": user.get("search_radius_miles") or 10,
    }

@api.get("/search/suggest")
async def search_suggest(q: str = Query(min_length=1, max_length=64), user: dict = Depends(get_current_user)):
    """Intelligent lightweight autocomplete: match listing titles/tags (excluding own listings) for the current user's radius."""
    import re
    safe_q = re.escape(q)
    query = {"is_active": True, "user_id": {"$ne": user["user_id"]}, "$or": [
        {"title": {"$regex": safe_q, "$options": "i"}},
        {"tags": {"$regex": safe_q, "$options": "i"}},
    ]}
    docs = await db.listings.find(query, {"_id": 0, "listing_id": 1, "title": 1, "kind": 1, "category": 1, "user_id": 1, "photos": 1}).limit(60).to_list(60)
    # enrich with distance for viewer
    out = []
    if user.get("approx_lat") is not None:
        owner_ids = list({d["user_id"] for d in docs})
        owners = {u["user_id"]: u async for u in db.users.find({"user_id": {"$in": owner_ids}}, {"_id": 0, "user_id": 1, "approx_lat": 1, "approx_lng": 1})}
        for d in docs:
            o = owners.get(d["user_id"])
            dist = None
            if o and o.get("approx_lat") is not None:
                dist = round(haversine_miles(user["approx_lat"], user["approx_lng"], o["approx_lat"], o["approx_lng"]), 1)
            out.append({**d, "distance_miles": dist})
        out.sort(key=lambda x: (x["distance_miles"] if x["distance_miles"] is not None else 9999))
    else:
        out = docs
    return out[:10]

# ---- Admin ----
@api.get("/admin/reports")
async def admin_reports(_: dict = Depends(get_admin)):
    return await db.reports.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.get("/admin/users")
async def admin_users(_: dict = Depends(get_admin)):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).limit(500).to_list(500)

@api.post("/admin/users/{user_id}/suspend")
async def admin_suspend(user_id: str, _: dict = Depends(get_admin)):
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": "suspended"}})
    return {"ok": True}

@api.delete("/admin/listings/{listing_id}")
async def admin_del_listing(listing_id: str, _: dict = Depends(get_admin)):
    await db.listings.delete_one({"listing_id": listing_id})
    return {"ok": True}

# ---- Referrals ----
@api.get("/referrals/mine")
async def my_referrals(user: dict = Depends(get_current_user)):
    # ensure user has a referral_code
    code = user.get("referral_code")
    if not code:
        code = uuid.uuid4().hex[:8].upper()
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"referral_code": code}})
    referred = await db.users.find({"referred_by": user["user_id"]}, {"_id": 0, "password_hash": 0, "email": 0}).to_list(200)
    return {
        "referral_code": code,
        "verified_referral": user.get("verified_referral", False),
        "referred_count": len(referred),
        "verified_count": sum(1 for r in referred if r.get("verified_referral")),
        "referred_users": [{"display_name": r.get("display_name"), "city": r.get("city"), "successful_trades": r.get("successful_trades", 0), "verified": r.get("verified_referral", False)} for r in referred],
    }

@api.get("/referrals/lookup/{code}")
async def lookup_referral(code: str):
    """Public endpoint (no auth) for /invite/{code} landing page to show who invited them."""
    u = await db.users.find_one({"referral_code": code.upper()}, {"_id": 0, "display_name": 1, "city": 1, "picture": 1, "reputation_score": 1, "successful_trades": 1})
    if not u:
        raise HTTPException(404, "Invalid invite code")
    return u

# ---- Direct Messages (user-to-user, independent of trades) ----
def _conv_id_for(a: str, b: str) -> str:
    return "conv_" + "_".join(sorted([a, b]))

class DMSendIn(BaseModel):
    to_user_id: Optional[str] = None
    text: str = Field(min_length=1)
    listing_id: Optional[str] = None

@api.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    convs = await db.conversations.find({"participants": user["user_id"]}, {"_id": 0}).sort("last_message_at", -1).to_list(200)
    out = []
    for c in convs:
        other_id = next((p for p in c["participants"] if p != user["user_id"]), None)
        other = await db.users.find_one({"user_id": other_id}, {"_id": 0, "password_hash": 0, "email": 0}) if other_id else None
        unread = await db.dm_messages.count_documents({
            "conversation_id": c["conversation_id"],
            "user_id": {"$ne": user["user_id"]},
            "read_by": {"$ne": user["user_id"]}
        })
        out.append({**c, "other_user": other, "unread": unread})
    return out

@api.get("/conversations/{other_user_id}")
async def get_or_create_conversation(other_user_id: str, user: dict = Depends(get_current_user)):
    if other_user_id == user["user_id"]:
        raise HTTPException(400, "Can't message yourself")
    # verify not blocked
    blocked = await db.blocks.find_one({"$or": [
        {"blocker": user["user_id"], "blocked": other_user_id},
        {"blocker": other_user_id, "blocked": user["user_id"]},
    ]})
    if blocked:
        raise HTTPException(403, "This user is unavailable")
    other = await db.users.find_one({"user_id": other_user_id}, {"_id": 0, "password_hash": 0, "email": 0})
    if not other:
        raise HTTPException(404, "User not found")
    cid = _conv_id_for(user["user_id"], other_user_id)
    existing = await db.conversations.find_one({"conversation_id": cid}, {"_id": 0})
    if not existing:
        existing = {
            "conversation_id": cid,
            "participants": sorted([user["user_id"], other_user_id]),
            "created_at": now_iso(),
            "last_message_at": now_iso(),
            "last_message": "",
        }
        await db.conversations.insert_one(existing)
        existing.pop("_id", None)
    msgs = await db.dm_messages.find({"conversation_id": cid}, {"_id": 0}).sort("created_at", 1).to_list(500)
    # mark as read for current user
    await db.dm_messages.update_many(
        {"conversation_id": cid, "user_id": {"$ne": user["user_id"]}, "read_by": {"$ne": user["user_id"]}},
        {"$addToSet": {"read_by": user["user_id"]}}
    )
    return {"conversation": existing, "other_user": other, "messages": msgs}

@api.post("/conversations/{other_user_id}/messages")
async def send_dm(other_user_id: str, inp: DMSendIn, user: dict = Depends(get_current_user)):
    if other_user_id == user["user_id"]:
        raise HTTPException(400, "Can't message yourself")
    other = await db.users.find_one({"user_id": other_user_id}, {"_id": 0, "user_id": 1})
    if not other:
        raise HTTPException(404, "User not found")
    blocked = await db.blocks.find_one({"$or": [
        {"blocker": user["user_id"], "blocked": other_user_id},
        {"blocker": other_user_id, "blocked": user["user_id"]},
    ]})
    if blocked:
        raise HTTPException(403, "This user is unavailable")
    # Validate text BEFORE upserting the conversation so a 422 does not leave a dirty write
    text = (inp.text or "").strip()
    if not text:
        raise HTTPException(422, "Message cannot be blank")
    cid = _conv_id_for(user["user_id"], other_user_id)
    await db.conversations.update_one(
        {"conversation_id": cid},
        {"$set": {
            "conversation_id": cid,
            "participants": sorted([user["user_id"], other_user_id]),
            "last_message_at": now_iso(),
            "last_message": text[:140],
        }, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )
    msg = {
        "id": new_id(),
        "conversation_id": cid,
        "user_id": user["user_id"],
        "user_name": user["display_name"],
        "text": text,
        "listing_id": inp.listing_id,
        "read_by": [user["user_id"]],
        "created_at": now_iso(),
    }
    await db.dm_messages.insert_one(msg)
    await _add_notification(other_user_id, "message", f"{user['display_name']}: {text[:60]}", conversation_with=user["user_id"])
    await _queue_email(other_user_id, "direct_message", f"New message from {user['display_name']}", {"preview": text[:140], "from_user": user["user_id"]})
    msg.pop("_id", None)
    return msg

# ---- AI Category Suggestion ----
class AISuggestIn(BaseModel):
    title: str
    description: Optional[str] = ""

@api.post("/ai/suggest-category")
async def suggest_category(inp: AISuggestIn, user: dict = Depends(get_current_user)):
    if not EMERGENT_LLM_KEY:
        return {"category": "Other"}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        cats = [
            "Food & Water", "Tools", "Home", "Garden", "Transportation",
            "Clothing", "Electronics", "Outdoor & Camping", "Baby & Family",
            "Books & Education", "Building Materials", "Services & Skills",
            "Household", "Recreation", "Other"
        ]
        sys = (
            "You classify barter listings into ONE of these categories. "
            "Respond with ONLY the exact category name, no punctuation, no explanation.\n"
            "Categories: " + ", ".join(cats)
        )
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"cat_{user['user_id']}", system_message=sys).with_model("openai", "gpt-5.4")
        prompt = f"Title: {inp.title}\nDescription: {inp.description or '(none)'}\n\nBest category:"
        reply = await chat.send_message(UserMessage(text=prompt))
        # Extract clean category
        text = (reply or "").strip().strip('"').strip("'")
        chosen = next((c for c in cats if c.lower() == text.lower()), None)
        if not chosen:
            chosen = next((c for c in cats if c.lower() in text.lower()), "Other")
        return {"category": chosen}
    except Exception as e:
        logger.error(f"AI suggest failed: {e}")
        return {"category": "Other"}

# ---- Root ----
@api.get("/")
async def root():
    return {"app": "BarterGrid", "status": "ok"}

app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage ready")
    except Exception as e:
        logger.error(f"Startup storage init failed: {e}")
    # Indexes for scale
    try:
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("referral_code")
        await db.users.create_index("username", unique=True, sparse=True)
        await db.listings.create_index("listing_id", unique=True)
        await db.listings.create_index([("user_id", 1), ("kind", 1), ("is_active", 1)])
        await db.listings.create_index("created_at")
        await db.listings.create_index("category")
        await db.trades.create_index("trade_id", unique=True)
        await db.trades.create_index([("proposer_id", 1), ("recipient_id", 1)])
        await db.trades.create_index("updated_at")
        await db.trade_messages.create_index([("trade_id", 1), ("created_at", 1)])
        await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        await db.blocks.create_index([("blocker", 1), ("blocked", 1)], unique=True)
        await db.conversations.create_index("conversation_id", unique=True)
        await db.conversations.create_index("participants")
        await db.dm_messages.create_index([("conversation_id", 1), ("created_at", 1)])
        logger.info("Indexes ready")
    except Exception as e:
        logger.error(f"Index creation issue: {e}")

@app.on_event("shutdown")
async def shutdown():
    client.close()
