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

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    approx_lat: Optional[float] = None
    approx_lng: Optional[float] = None
    search_radius_miles: Optional[int] = None
    picture: Optional[str] = None

class ListingIn(BaseModel):
    kind: str  # 'have' | 'need' | 'service' (case-insensitive, normalized server-side)
    title: str
    description: str = ""
    category: str
    condition: Optional[str] = None
    quantity: Optional[str] = None
    photos: List[str] = []
    wants: List[str] = []  # For HAVE: what they want in exchange
    tags: List[str] = []
    urgency: Optional[str] = "normal"
    is_active: bool = True

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
    text: str

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
            return user
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
                return user
    raise HTTPException(401, "Invalid or expired session")

async def get_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return user

# ---- Auth Routes ----
@api.post("/auth/signup")
async def signup(inp: SignupIn):
    existing = await db.users.find_one({"email": inp.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id,
        "email": inp.email.lower(),
        "display_name": inp.display_name,
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
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "display_name": data.get("name", email.split("@")[0]),
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
    if update:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return u

@api.get("/users/{user_id}")
async def get_user(user_id: str, _: dict = Depends(get_current_user)):
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0, "email": 0, "approx_lat": 0, "approx_lng": 0})
    if not u:
        raise HTTPException(404, "User not found")
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
                        radius: Optional[int] = None, mine: bool = False, user: dict = Depends(get_current_user)):
    query = {"is_active": True}
    if kind:
        query["kind"] = kind.lower()
    if category:
        query["category"] = category
    if mine:
        query["user_id"] = user["user_id"]
    else:
        # exclude own listings + blocked users
        blocked = await db.blocks.find({"$or": [{"blocker": user["user_id"]}, {"blocked": user["user_id"]}]}).to_list(1000)
        blocked_ids = set()
        for b in blocked:
            blocked_ids.add(b["blocker"] if b["blocked"] == user["user_id"] else b["blocked"])
        query["user_id"] = {"$nin": list(blocked_ids) + [user["user_id"]]} if blocked_ids else {"$ne": user["user_id"]}
    if q:
        query["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"description": {"$regex": q, "$options": "i"}}, {"tags": {"$regex": q, "$options": "i"}}]
    docs = await db.listings.find(query, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    enriched = [await enrich_listing(d, user) for d in docs]
    # radius filter
    if radius and user.get("approx_lat"):
        enriched = [e for e in enriched if e.get("distance_miles") is None or e["distance_miles"] <= radius]
    return enriched

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
    await db.notifications.insert_one({
        "id": new_id(), "user_id": inp.to_user_id, "type": "trade_proposal", "trade_id": tid,
        "text": f"{user['display_name']} proposed a trade", "read": False, "created_at": now_iso()
    })
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
    updates = {"updated_at": now_iso()}
    if action == "accept" and user["user_id"] == t["recipient_id"] and t["status"] == "proposed":
        updates["status"] = "accepted"
    elif action == "decline" and user["user_id"] == t["recipient_id"] and t["status"] == "proposed":
        updates["status"] = "declined"
    elif action == "cancel":
        updates["status"] = "cancelled"
    elif action == "complete":
        role = "proposer" if user["user_id"] == t["proposer_id"] else "recipient"
        updates[f"{role}_completed"] = True
        both = t.get("proposer_completed") or t.get("recipient_completed")
        p_done = updates.get("proposer_completed", t.get("proposer_completed", False))
        r_done = updates.get("recipient_completed", t.get("recipient_completed", False))
        if p_done and r_done:
            updates["status"] = "completed"
            # bump successful_trades for both
            await db.users.update_one({"user_id": t["proposer_id"]}, {"$inc": {"successful_trades": 1}})
            await db.users.update_one({"user_id": t["recipient_id"]}, {"$inc": {"successful_trades": 1}})
    else:
        raise HTTPException(400, f"Invalid action or state: {action}")
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
    msg = {"id": new_id(), "trade_id": trade_id, "user_id": user["user_id"], "user_name": user["display_name"], "text": inp.text, "created_at": now_iso()}
    await db.trade_messages.insert_one(msg)
    other = t["recipient_id"] if t["proposer_id"] == user["user_id"] else t["proposer_id"]
    await db.notifications.insert_one({"id": new_id(), "user_id": other, "type": "message", "trade_id": trade_id, "text": f"{user['display_name']}: {inp.text[:60]}", "read": False, "created_at": now_iso()})
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

# ---- Community stats ----
@api.get("/community/stats")
async def community_stats(user: dict = Depends(get_current_user)):
    total_users = await db.users.count_documents({})
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

@app.on_event("shutdown")
async def shutdown():
    client.close()
