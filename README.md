# 🎟️ MuseBot — AI Ticketing & Visitor Experience Platform

An AI-powered, multi-tenant conversational ticketing platform for museums, national parks, heritage sites, and science centers. Visitors book tickets end-to-end — chat, pay, get a QR ticket — without human intervention. Venues get their own branded chatbot and a real admin analytics dashboard.

## Problem Statement

Museums and cultural venues face long queues, manual ticketing errors, double bookings, no visitor data, and poor accessibility for non-English speakers. MuseBot eliminates human intervention from the entire ticketing flow — browsing, booking, payment, and entry.

## Core Features

- **Conversational booking** — natural language ("2 adults 1 kid tomorrow for tiger safari") or an inline guided form
- **NLP intent parsing** — powered by an LLM (Groq/Llama 3.3) to extract headcount, exhibit, and date from free text
- **Real-time slot availability** with live crowd status (Quiet/Moderate/Busy)
- **Dynamic off-peak pricing** — automatic discounts to nudge visitors toward quieter slots
- **Real payments** — Razorpay integration (sandbox), idempotent verification, signature validation
- **QR e-tickets** — generated on payment, single-use gate verification endpoint (`/verify-qr`) to prevent reuse
- **AI-personalized itinerary** — LLM-generated visit plan based on visitor interest and exhibit
- **Post-visit digital souvenir** — shareable visit badge generated on checkout
- **Group & school booking** — tiered bulk discounts (8%/15%/25%/30% for schools), consolidated pass
- **Multilingual support** — 8 languages, auto-detection + manual switcher, full conversation translation
- **Email delivery** — tickets and OTP codes sent via SMTP with embedded QR
- **Cancellation & refunds** — time-based policy (100% / 50% / 0% refund tiers), real Razorpay refunds
- **Multi-tenant architecture** — one deployment serves unlimited venues, each with isolated data, dynamically loaded via URL slug (`/venue/:slug`)
- **Admin analytics dashboard** — venue-scoped login (username/password), revenue breakdown, popular exhibits, peak hours, footfall trends, CSV export
- **Smart bundle recommendations** — suggests complementary exhibits at the same venue
- **Visitor feedback** — post-purchase star ratings feed into analytics

## Tech Stack

**Backend:** FastAPI (Python), MongoDB (Motor async driver), JWT auth
**Frontend:** React (Vite), Tailwind CSS v4, Recharts, React Router
**AI/LLM:** Groq API (Llama 3.3) for intent parsing and itinerary generation
**Payments:** Razorpay (sandbox/test mode)
**Email:** SMTP (Gmail)
**Other:** `qrcode` for ticket generation, `deep-translator` + `langdetect` for multilingual support, `passlib`/`bcrypt` for admin password hashing

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Visitor Widget  │     │  Admin Dashboard  │     │   Venue Sites   │
│ /venue/:slug     │     │  /admin/:slug     │     │  (embed target) │
└────────┬─────────┘     └────────┬──────────┘     └─────────────────┘
         │                        │
         └───────────┬────────────┘
                      ▼
            ┌───────────────────┐
            │   FastAPI Backend  │
            │  (single deploy)   │
            ├────────────────────┤
            │ NLP · Conversation │
            │ Crowd Meter        │
            │ Payments · QR      │
            │ Analytics          │
            └─────────┬──────────┘
                       ▼
            ┌───────────────────┐
            │      MongoDB       │
            │ venues · exhibits  │
            │ slots · bookings   │
            │ users · admins     │
            └────────────────────┘
```

One backend, one database — every venue's data is isolated by `venueId`, so the same codebase scales to any number of venues without duplication.

## Project Structure

```
musebot/
├── backend/
│   ├── models/          # Pydantic models (Venue, Exhibit, Slot, Booking, User, Admin, Payment)
│   ├── routes/           # API endpoints (venues, exhibits, slots, bookings, chat, payment, auth, admin_auth, analytics)
│   ├── services/          # Business logic (NLP, conversation flow, crowd meter, pricing, QR, email, translation, auth)
│   ├── seed_data.py       # Seeds demo venues, exhibits, and slots
│   ├── seed_bookings.py   # Seeds realistic historical bookings for dashboard demo data
│   └── main.py
└── frontend/
    └── src/
        ├── components/
        │   ├── ChatWidget.jsx      # Visitor-facing chatbot widget
        │   ├── VenuePage.jsx        # Loads venue by URL slug
        │   └── AdminDashboard.jsx   # Venue admin analytics
        └── App.jsx                 # React Router setup
```

## Getting Started

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate       
pip install -r requirements.txt
```

Create `backend/.env`:
```
MONGO_URI=mongodb://localhost:27017
GROQ_API_KEY=your_groq_key
RAZORPAY_KEY_ID=your_razorpay_test_key
RAZORPAY_KEY_SECRET=your_razorpay_test_secret
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
JWT_SECRET=a_long_random_string
```

Seed demo data, then run:
```bash
python seed_data.py
python seed_bookings.py
uvicorn main:app --reload --port 5000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit a venue's chatbot:
```
http://localhost:5173/venue/greenwood-national-park
```

Visit the admin dashboard:
```
http://localhost:5173/admin/greenwood-national-park
```

## Demo Venues (seeded)

| Venue | Type | Exhibits |
|---|---|---|
| City Heritage Museum | Museum | Dinosaur Discovery Zone, Ancient Egypt Gallery, Modern Art Wing |
| Greenwood National Park | National Park | Tiger Safari Trail, Bird Watching Trek |
| Fort Ravalgiri Heritage Site | Heritage Site | Fort Ramparts Walk, Sound & Light Show |
| Stardome Science Centre | Science Center | Planetarium Show, Robotics Lab |

## What This Doesn't Include (Honest Scope Notes)

- No RAG / vector search — NLP and itinerary generation use direct LLM prompt calls, not retrieval-augmented generation
- No automated test suite — verified manually through Swagger UI (`/docs`) and the live UI
- Not deployed — runs locally; would need a host (Render/Railway/Vercel) and MongoDB Atlas for production
- No true embeddable widget script yet — venues are loaded via URL routing (`/venue/:slug`), not a drop-in `<script>` tag
- Age-band pricing (e.g. child under 5 free) not implemented — currently a flat adult/child two-tier system
