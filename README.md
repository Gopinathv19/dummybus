# 🚌 DummyBus.com

> **Fake bus-booking site for BusSlinger's self-healing demo**  
> Into the Scrape-Verse Hackathon — Bright Data

---

## What is this?

DummyBus.com is a controlled, fake AbhiBus-style bus booking website.  
It lets you **simulate DOM/schema changes on demand** so that BusSlinger's  
self-healing engine can detect, adapt, and recover — all in a live demo.

---

## Endpoints

| URL | Purpose |
|-----|---------|
| `GET /` | Homepage with search form |
| `GET /results?from_city=Chennai&to_city=Bengaluru&date=18-08-2026` | **HTML results page — what Bright Data scrapes** |
| `GET /api/buses?from_city=Chennai&to_city=Bengaluru` | **JSON API — returns nested `services` array** |
| `GET /admin` | Admin panel — break/restore DOM selectors |
| `POST /admin/break` | Break all (or specific) fields |
| `POST /admin/restore` | Restore all fields |
| `POST /admin/toggle/{field}` | Toggle a single field |
| `GET /admin/status` | Current DOM state as JSON |

---

## The Healing Demo Flow

```
1. Bright Data scrapes /results → all 12 buses extracted cleanly
   (health_score ≈ 0.95, status = "healthy")

2. You open /admin → click "💥 Break ALL Fields"
   → CSS classes and JSON keys are instantly renamed

3. Bright Data scrapes again → scraper finds wrong class names
   (health_score ≈ 0.20, status = "degraded")

4. BusSlinger HealEngine fires Level 1 healing
   → tries fallback selectors from selector_map
   → recovers fields via alternate key names

5. health_score recovers to ≈ 0.85+
   (status = "healed")

6. Judges see the full heal cycle in BusSlinger's UI ✅
```

---

## Field Mapping (Normal → Broken)

| Field | Normal HTML class | Broken HTML class | Normal JSON key | Broken JSON key |
|-------|-------------------|-------------------|-----------------|-----------------|
| operator_name | `.service-name` | `.provider-name` | `operator_name` | `provider` |
| bus_type | `.bus-type` | `.coach-type` | `bus_type` | `coach_type` |
| departure_time | `.departure-time` | `.dep-time` | `departure_time` | `dep_time` |
| arrival_time | `.arrival-time` | `.arr-time` | `arrival_time` | `arr_time` |
| duration | `.duration` | `.travel-time` | `duration` | `travel_time` |
| price | `.fare-amount` | `.ticket-cost` | `price` | `fare` |
| original_price | `.original-price` | `.strike-price` | `original_price` | `mrp` |
| available_seats | `.seats` | `.seats-left` | `available_seats` | `seats_remaining` |
| rating | `.rating` | `.star-score` | `rating` | `score` |

---

## Run Locally

```bash
cd dummybus
pip install -r requirements.txt
python main.py
# → http://localhost:8001
```

---

## Deploy to Railway (Recommended)

1. Create a new Railway project
2. Connect your GitHub repo
3. Set **Root Directory** to `dummybus`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy → get your public URL (e.g. `https://dummybus-production.up.railway.app`)

### Procfile (already included)
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Deploy to Render

1. New Web Service → connect repo
2. Root Directory: `dummybus`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Point Bright Data Collector at DummyBus

Once deployed, set your Bright Data Scraper Studio collector input URL to:

```
https://your-dummybus-url.railway.app/results?from_city=Chennai&to_city=Bengaluru&date=18-08-2026
```

Or the JSON API (if using API-mode collection):
```
https://your-dummybus-url.railway.app/api/buses?from_city=Chennai&to_city=Bengaluru
```

---

## Demo Presets (Admin Panel)

| Preset | What breaks | Expected heal |
|--------|-------------|---------------|
| 💰 Break Price + Operator | `price`, `operator_name` | Level 1: tries `fare`, `bus_operator` fallbacks |
| 🕐 Break All Time Fields | `departure_time`, `arrival_time`, `duration` | Level 1: tries `dep_time`, `arr_time`, `travel_time` |
| 💣 Break 4 Key Fields | `price`, `operator_name`, `available_seats`, `rating` | Level 1 → Level 2 if still failing |
| 💥 Break ALL | All 9 fields | Full DOM drift detected, fingerprint changes |

---

## Project Structure

```
dummybus/
├── main.py              # FastAPI app (all routes)
├── dom_config.json      # Live DOM state (modified by admin API)
├── templates/
│   ├── index.html       # Homepage
│   ├── results.html     # Bus results (scraped by Bright Data)
│   └── admin.html       # Demo control panel
├── static/
│   └── style.css        # AbhiBus-inspired styling
├── requirements.txt
└── README.md
```

---

*Built for BusSlinger — Into the Scrape-Verse Hackathon 2026*
