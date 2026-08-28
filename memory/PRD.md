# BarterGrid — Product Requirements

## Problem statement (original)
Build a local barter and community exchange network where users trade goods, skills, and resources without money. Core loop: I HAVE → I NEED → FIND MATCH → PROPOSE TRADE → AGREE → MEET SAFELY → COMPLETE → BUILD REPUTATION. Works on mobile and desktop. Free to use. Dark mode, aiwebtools.app branding, payment/crypto handles, Emergency Mode, Community Resource Dashboard, Resend email notifications, and public discoverability.

## User personas
- **Neighborhood trader** — trades tools, home goods, produce with people within 1–25 miles
- **Skill sharer** — offers services (repair, tutoring, gardening) in exchange for items or other services
- **Community organizer** — wants an aggregate view of local resources
- **Emergency responder** — surfaces urgent food/water/shelter needs to nearby helpers

## Core requirements
- Auth: JWT email/password (httpOnly cookie session) + Emergent Google OAuth
- Listings: HAVE, NEED, CAN DO (service) with category, photos, tags, wants, urgency
- Matching engine: token overlap + reciprocal want match + distance + 3-way trade chains
- Trades: proposal → accept/decline → meetup → bilateral completion → mutual rating
- Reputation: aggregate stars, successful_trades, verification badges
- Safety: public meetup guidance, reporting, blocking, prohibited item rules
- Direct messaging (user↔user inbox) + trade chats
- Emergency Mode: is_emergency + emergency_type on needs; floats to top of every list
- Community Resource Dashboard: public aggregate view (traders, haves/needs/skills, category table, top skills)
- Referrals with verified-referral badges
- Resend email notifications (matches, messages, trades)

## What's been implemented

### 2026-08-25 — v1
- Backend: 25+ endpoints, MongoDB, custom user_id UUIDs
- JWT signup/login + Emergent Google OAuth session exchange
- Emergent Object Storage integration for listing photos
- Full trade lifecycle, matching, reputation, notifications
- React frontend: Landing, Login/Signup, Onboarding, Dashboard, Discover, NewListing, MyListings, ListingDetail, Matches, Trades, Profile, Safety
- Dark theme, Outfit + Inter fonts, phosphor duotone icons, pill CTAs
- Mobile bottom nav + desktop top nav

### 2026-08-27 — v2
- Tags on listings, Smart search, public Discover page
- Trade chains (3-person A→B→C→A swaps)
- Direct messaging inbox
- Resend email notifications
- Payment/crypto wallet handles (CashApp, Venmo, PayPal, BTC, SOL, ETH) + accept-donations toggle
- Public share buttons (Facebook, Twitter, SMS)
- aiwebtools.app branding + FREE AI TOOLS cross-promo
- Referral system with verified badges

### 2026-08-28 — v3 (this session)
- **New `/api/community/dashboard` endpoint** — public aggregate view: total_users, by_kind, by_category (normalized), emergency listings, completed_trades, recent_completed_30d, top_services. Parallel query + parallel enrichment for perf.
- **Community page (`/community`)** — publicly viewable (GuestOrAppShell), added to top nav
- **Emergency Mode surfaces** — emergency listings float to top of every listing view + dedicated banner on Community
- **Security: JWT moved out of localStorage** — backend sets httpOnly + Secure + SameSite=None cookie (`session_token`) on signup/login/OAuth; frontend uses `withCredentials: true` and no longer touches localStorage for the token. Bearer-token backward-compat preserved for curl/tests.
- **Trade completion timestamp** — `completed_at` now set when both parties complete; 95 historical trades backfilled from `updated_at`
- **Category normalization** — free-form category input coerced to canonical casing (fixes 'home' vs 'Home' duplicate rows); backfilled all existing listings
- **`emergency_count` now uses count_documents** instead of len() of capped-12 list
- **Community.jsx error state** — retry button on API failure
- **Code review pass (from user-supplied report)**:
  - Moved test PASSWORD out of source code into env var (`BG_TEST_PASSWORD`)
  - Refactored high-complexity Python functions: `trade_action` now dispatches through `_TRADE_ACTIONS` map + small handlers (`_handle_trade_accept/decline/cancel/complete`) with `_finalize_completed_trade` and `_mark_referral_verified` extracted; `list_listings` split into `_build_listing_query` + `_apply_listing_filters` + `_sort_listings`; `get_trade_chains` split into `_listing_tokens` + `_collect_need_terms` + `_build_chain_participant` with cached `wants_of()`; `dashboard_stats` split into 3 parallel helpers running via `asyncio.gather`
  - Converted one-shot mount `useEffect`s to `useCallback` + `useEffect([load])` pattern in Dashboard, Trades, Referral so hook deps are explicit and complete
  - Replaced nested ternaries with lookup maps: `KIND_LABEL`/`KIND_STYLE`/`KIND_SHARE_VERB` in Listings.jsx, `getSubmitLabel(loading, mode)` in Login.jsx, expanded `A ? B : C ? null : D` into separate `&&` gates in Matches.jsx
  - Replaced `key={i}` array-index keys with stable data-derived keys in Landing.jsx (howItWorks `s.id`, examples composite `a->b`, trust `f.id`, faqs `f.q`)
- **Trade-complete state guard** (found by testing agent) — reject `action=complete` unless trade status is `accepted` or `meetup_planned`. Fixes: (a) completing a declined/proposed trade, (b) double-complete on already-completed trade re-incrementing `successful_trades` and re-firing rating notifications.
- **Chain dedup** — `/api/matches/chains` now keys on the unordered set of participant listing IDs so one loop isn't returned in multiple orderings.
- **Profile location fix** — `[city, state].filter(Boolean).join(", ")` replaces `${city}, ${state}` so no dangling `— ,` when state is empty.
- **Community page min-height** — no more floating footer mid-page on sparse data.
- **Test data cleanup** — purged 1505 leftover ephemeral TEST_* user accounts and their associated listings/trades/messages/notifications; community counters now reflect real data (~148 traders, 9 haves, 4 needs, 17 completed trades).
- Backend: **191/191 tests passing** (159 legacy + 32 new iteration12 regression tests)

## Prioritized backlog

### P1 (next feature work)
- Identity verification beyond email/phone (phone, ID upload)
- Community groups + mutual-aid style exchanges
- Priority notifications + expanded radius as premium tier
- Real-time WebSocket chat (currently 4s polling)

### P2
- LLM semantic matching (EMERGENT_LLM_KEY available)
- Interactive map view on Community dashboard
- Push notifications
- Neighborhood-scoped subgroups

### Technical debt
- Split server.py (~1500 lines) into routers: auth, listings, trades, community, admin, messaging
- Add optional TTL cache on `/community/dashboard` (public endpoint)
- Derive cookie `secure`/`samesite` from env for local http:// dev

## Integrations
- **Resend** (transactional email) — RESEND_API_KEY in .env. Test mode delivers only to kgmasterbic@gmail.com.
- **Emergent LLM Key** — used for auto-categorization
- **Emergent Object Storage** — listing photos
- **Emergent Google OAuth** — social sign-in
