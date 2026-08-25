# BarterGrid — Product Requirements

## Problem statement (original)
Build a local barter and community exchange network where users trade goods, skills, and resources without money. Core loop: I HAVE → I NEED → FIND MATCH → PROPOSE TRADE → AGREE → MEET SAFELY → COMPLETE → BUILD REPUTATION. Works on mobile and desktop. Free to use.

## User personas
- **Neighborhood trader** — trades tools, home goods, produce with people within 1–25 miles
- **Skill sharer** — offers services (repair, tutoring, gardening) in exchange for items or other services
- **Community organizer** — wants an aggregate view of local resources

## Core requirements (static)
- Auth: JWT email/password + Emergent Google OAuth
- Listings: HAVE, NEED, CAN DO (service) with category, photos, wants
- Matching engine: token-overlap + reciprocal want match + distance
- Trades: proposal → accept/decline → meetup → bilateral completion → mutual rating
- Reputation: aggregate stars, successful_trades, verification badges
- Safety: public meetup guidance, reporting, blocking, prohibited item rules
- Location: city + coordinates + radius (no interactive map in MVP)

## What's been implemented (2026-08-25 — v1)
- ✅ FastAPI backend with 25+ endpoints, MongoDB, custom user_id UUIDs
- ✅ JWT signup/login + Emergent Google OAuth session exchange
- ✅ Emergent Object Storage integration for listing photos
- ✅ Full trade lifecycle: propose → accept → chat → meetup → bilateral complete → rate
- ✅ Matching engine with token overlap + reciprocal want detection + distance
- ✅ Reputation aggregation on rating submission
- ✅ Reports, blocks (bidirectional filtering in discover), notifications
- ✅ Community stats endpoint
- ✅ React frontend: Landing, Login/Signup, Onboarding, Dashboard, Discover, NewListing, MyListings, ListingDetail, Matches, TradesList, TradeDetail (with chat + meetup + rating), Profile, Safety Center
- ✅ Design system: Outfit + Inter fonts, Organic & Earthy palette, phosphor duotone icons, dot-grid + mesh backgrounds, pill CTAs
- ✅ Mobile bottom nav + desktop top nav
- ✅ Backend tested: 25/25 tests passing (retest confirmed)

## Prioritized backlog

### P0 (nice-to-have next)
- Persistent "My Needs" page with priority colors (backend supports it via kind=need listings)
- Notifications dropdown in nav (backend endpoints exist)
- Admin dashboard UI (backend routes exist)

### P1
- Trade chains (A→B→C→A) UI surfacing — backend architecture ready
- Counteroffers on trade proposals
- "Share Meetup" with a trusted contact (link generation)
- Reporting UI on listing/profile pages

### P2
- Semantic matching via LLM (EMERGENT_LLM_KEY available)
- Community view / neighborhood dashboards
- Realtime chat via WebSocket (polling for MVP)
- Phone verification integration
- Push notifications
