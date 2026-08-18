"""
DummyBus.com — Fake bus-booking site for BusSlinger self-healing demo.

Endpoints:
  GET  /                               → Homepage (search form)
  GET  /results?from=...&to=...&date=... → HTML results page (Bright Data scrapes this)
  GET  /api/buses?from=...&to=...&date=... → JSON API (returns nested services array)
  GET  /bus/{operator}/{route}         → Booking detail page (catch-all so Bright Data
                                          next_stage() links never 404)
  GET  /admin                          → Admin panel (DOM break/restore controls)
  POST /admin/break                    → Break all or specific fields
  POST /admin/restore                  → Restore all fields to normal
  POST /admin/toggle/{field}           → Toggle a single field
  GET  /admin/status                   → Current DOM config (JSON)
"""

import json
import os
import copy
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "dom_config.json"

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="DummyBus.com", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_active_classes(config: dict) -> dict:
    """Return the currently active HTML class for each field (normal or broken)."""
    classes = {}
    for field, cfg in config["fields"].items():
        if cfg["is_broken"]:
            classes[field] = cfg["broken_html_class"]
        else:
            classes[field] = cfg["html_class"]
    return classes


def get_active_json_keys(config: dict) -> dict:
    """Return the currently active JSON key for each field (normal or broken)."""
    keys = {}
    for field, cfg in config["fields"].items():
        if cfg["is_broken"]:
            keys[field] = cfg["broken_json_key"]
        else:
            keys[field] = cfg["json_key"]
    return keys


# ── Dummy bus data ─────────────────────────────────────────────────────────────

DUMMY_BUSES = [
    {
        "operator_name": "SBM Transport",
        "bus_type": "Bharat Benz AC Sleeper (2+1)",
        "departure_time": "06:00",
        "arrival_time": "13:30",
        "duration": "7h 30m",
        "price": {"value": 1299, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1499, "currency": "INR", "symbol": "₹"},
        "available_seats": 24,
        "rating": 4.5,
        "product_page_url": "/bus/sbm-transport/chennai-bangalore",
    },
    {
        "operator_name": "VRL Travels",
        "bus_type": "Volvo AC Multi Axle (2+2)",
        "departure_time": "07:30",
        "arrival_time": "14:45",
        "duration": "7h 15m",
        "price": {"value": 999, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1199, "currency": "INR", "symbol": "₹"},
        "available_seats": 12,
        "rating": 4.2,
        "product_page_url": "/bus/vrl-travels/chennai-bangalore",
    },
    {
        "operator_name": "Orange Travels",
        "bus_type": "Scania AC Sleeper (2+1)",
        "departure_time": "08:45",
        "arrival_time": "17:00",
        "duration": "8h 15m",
        "price": {"value": 1599, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1799, "currency": "INR", "symbol": "₹"},
        "available_seats": 8,
        "rating": 4.7,
        "product_page_url": "/bus/orange-travels/chennai-bangalore",
    },
    {
        "operator_name": "Kallada Travels",
        "bus_type": "Volvo AC Semi Sleeper (2+2)",
        "departure_time": "10:00",
        "arrival_time": "17:30",
        "duration": "7h 30m",
        "price": {"value": 849, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 999, "currency": "INR", "symbol": "₹"},
        "available_seats": 32,
        "rating": 4.0,
        "product_page_url": "/bus/kallada-travels/chennai-bangalore",
    },
    {
        "operator_name": "KSRTC Karnataka",
        "bus_type": "Airavat Club Class AC (2+2)",
        "departure_time": "11:30",
        "arrival_time": "19:00",
        "duration": "7h 30m",
        "price": {"value": 750, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 750, "currency": "INR", "symbol": "₹"},
        "available_seats": 45,
        "rating": 4.3,
        "product_page_url": "/bus/ksrtc-karnataka/chennai-bangalore",
    },
    {
        "operator_name": "Parveen Travels",
        "bus_type": "Mercedes AC Sleeper (2+1)",
        "departure_time": "13:00",
        "arrival_time": "21:30",
        "duration": "8h 30m",
        "price": {"value": 1150, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1350, "currency": "INR", "symbol": "₹"},
        "available_seats": 18,
        "rating": 3.9,
        "product_page_url": "/bus/parveen-travels/chennai-bangalore",
    },
    {
        "operator_name": "SRM Travels",
        "bus_type": "Volvo AC Sleeper (2+1)",
        "departure_time": "15:30",
        "arrival_time": "23:00",
        "duration": "7h 30m",
        "price": {"value": 1099, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1299, "currency": "INR", "symbol": "₹"},
        "available_seats": 6,
        "rating": 4.1,
        "product_page_url": "/bus/srm-travels/chennai-bangalore",
    },
    {
        "operator_name": "Raj National Express",
        "bus_type": "Non-AC Seater (2+3)",
        "departure_time": "17:00",
        "arrival_time": "01:30",
        "duration": "8h 30m",
        "price": {"value": 450, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 550, "currency": "INR", "symbol": "₹"},
        "available_seats": 28,
        "rating": 3.5,
        "product_page_url": "/bus/raj-national/chennai-bangalore",
    },
    {
        "operator_name": "Greenline Travels",
        "bus_type": "Bharat Benz AC Seater (2+2)",
        "departure_time": "19:00",
        "arrival_time": "02:15",
        "duration": "7h 15m",
        "price": {"value": 799, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 949, "currency": "INR", "symbol": "₹"},
        "available_seats": 14,
        "rating": 4.4,
        "product_page_url": "/bus/greenline-travels/chennai-bangalore",
    },
    {
        "operator_name": "Chartered Bus",
        "bus_type": "Volvo AC Multi Axle Sleeper (2+1)",
        "departure_time": "21:00",
        "arrival_time": "04:30",
        "duration": "7h 30m",
        "price": {"value": 1399, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1599, "currency": "INR", "symbol": "₹"},
        "available_seats": 20,
        "rating": 4.6,
        "product_page_url": "/bus/chartered-bus/chennai-bangalore",
    },
    {
        "operator_name": "Aarvy Holidays",
        "bus_type": "Scania AC Sleeper (2+1)",
        "departure_time": "22:30",
        "arrival_time": "06:00",
        "duration": "7h 30m",
        "price": {"value": 1249, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1449, "currency": "INR", "symbol": "₹"},
        "available_seats": 3,
        "rating": 4.8,
        "product_page_url": "/bus/aarvy-holidays/chennai-bangalore",
    },
    {
        "operator_name": "Paulo Travels",
        "bus_type": "Volvo AC Sleeper (2+1)",
        "departure_time": "23:45",
        "arrival_time": "07:15",
        "duration": "7h 30m",
        "price": {"value": 1199, "currency": "INR", "symbol": "₹"},
        "original_price": {"value": 1399, "currency": "INR", "symbol": "₹"},
        "available_seats": 10,
        "rating": 4.3,
        "product_page_url": "/bus/paulo-travels/chennai-bangalore",
    },
]


def build_bus_record(bus: dict, json_keys: dict, base_url: str) -> dict:
    """
    Build a single bus record using the currently active JSON keys.
    This simulates the DOM/schema change — keys rename when broken.
    """
    record = {}

    record[json_keys["operator_name"]] = bus["operator_name"]
    record[json_keys["bus_type"]] = bus["bus_type"]
    record[json_keys["departure_time"]] = bus["departure_time"]
    record[json_keys["arrival_time"]] = bus["arrival_time"]
    record[json_keys["duration"]] = bus["duration"]
    record[json_keys["price"]] = bus["price"]
    record[json_keys["original_price"]] = bus["original_price"]
    record[json_keys["available_seats"]] = bus["available_seats"]
    record[json_keys["rating"]] = bus["rating"]
    record["product_page_url"] = base_url + bus["product_page_url"]

    return record


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    config = load_config()
    broken_count = sum(1 for f in config["fields"].values() if f["is_broken"])
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "broken_count": broken_count,
            "is_any_broken": config["broken"],
        },
    )


@app.get("/results", response_class=HTMLResponse)
async def results(
    request: Request,
    from_city: str = "Chennai",
    to_city: str = "Bengaluru",
    date: str = None,
):
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")

    config = load_config()
    classes = get_active_classes(config)
    json_keys = get_active_json_keys(config)

    base_url = str(request.base_url).rstrip("/")
    input_url = str(request.url)

    broken_fields = [f for f, cfg in config["fields"].items() if cfg["is_broken"]]
    broken_count = len(broken_fields)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "buses": DUMMY_BUSES,
            "classes": classes,
            "from_city": from_city,
            "to_city": to_city,
            "date": date,
            "base_url": base_url,
            "input_url": input_url,
            "broken_fields": broken_fields,
            "broken_count": broken_count,
            "is_any_broken": config["broken"],
        },
    )


@app.get("/api/buses")
async def api_buses(
    request: Request,
    from_city: str = "Chennai",
    to_city: str = "Bengaluru",
    date: str = None,
):
    """
    JSON endpoint — returns the nested `services` array format expected by
    BusSlinger's bright_data_client.run_scraper() → bright_data_client flattens this.

    When DOM is broken, JSON keys are renamed to simulate a schema change.
    """
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")

    config = load_config()
    json_keys = get_active_json_keys(config)
    base_url = str(request.base_url).rstrip("/")
    input_url = str(request.url)

    services = [build_bus_record(bus, json_keys, base_url) for bus in DUMMY_BUSES]

    # Wrap in the exact format bright_data_client expects
    return JSONResponse(
        content=[
            {
                "services": services,
                "product_page_url": base_url + "/results",
                "input": {"url": input_url},
            }
        ]
    )


# ── Admin Panel ───────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    config = load_config()
    broken_count = sum(1 for f in config["fields"].values() if f["is_broken"])
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "config": config,
            "broken_count": broken_count,
        },
    )


@app.post("/admin/break")
async def break_all(fields: Optional[str] = Form(default=None)):
    """Break all fields or a comma-separated list of specific fields."""
    config = load_config()

    if fields:
        field_list = [f.strip() for f in fields.split(",") if f.strip() in config["fields"]]
    else:
        field_list = list(config["fields"].keys())

    for field in field_list:
        config["fields"][field]["is_broken"] = True

    config["broken"] = any(f["is_broken"] for f in config["fields"].values())
    save_config(config)

    return JSONResponse(
        content={
            "status": "broken",
            "broken_fields": [f for f, cfg in config["fields"].items() if cfg["is_broken"]],
            "message": f"Broke {len(field_list)} field(s): {', '.join(field_list)}",
        }
    )


@app.post("/admin/restore")
async def restore_all():
    """Restore all fields to original class/key names."""
    config = load_config()

    for field in config["fields"]:
        config["fields"][field]["is_broken"] = False

    config["broken"] = False
    save_config(config)

    return JSONResponse(
        content={
            "status": "healthy",
            "message": "All fields restored to original selectors.",
        }
    )


@app.post("/admin/toggle/{field}")
async def toggle_field(field: str):
    """Toggle a single field between broken and healthy."""
    config = load_config()

    if field not in config["fields"]:
        return JSONResponse(
            status_code=404,
            content={"error": f"Field '{field}' not found."},
        )

    current = config["fields"][field]["is_broken"]
    config["fields"][field]["is_broken"] = not current
    config["broken"] = any(f["is_broken"] for f in config["fields"].values())
    save_config(config)

    new_state = "broken" if config["fields"][field]["is_broken"] else "healthy"
    return JSONResponse(
        content={
            "field": field,
            "status": new_state,
            "active_html_class": (
                config["fields"][field]["broken_html_class"]
                if config["fields"][field]["is_broken"]
                else config["fields"][field]["html_class"]
            ),
            "active_json_key": (
                config["fields"][field]["broken_json_key"]
                if config["fields"][field]["is_broken"]
                else config["fields"][field]["json_key"]
            ),
        }
    )


@app.get("/admin/status")
async def admin_status():
    """Return the current DOM configuration as JSON."""
    config = load_config()
    active = {}
    for field, cfg in config["fields"].items():
        active[field] = {
            "is_broken": cfg["is_broken"],
            "active_html_class": cfg["broken_html_class"] if cfg["is_broken"] else cfg["html_class"],
            "active_json_key": cfg["broken_json_key"] if cfg["is_broken"] else cfg["json_key"],
        }
    broken_fields = [f for f, cfg in config["fields"].items() if cfg["is_broken"]]
    return JSONResponse(
        content={
            "overall_broken": config["broken"],
            "broken_count": len(broken_fields),
            "broken_fields": broken_fields,
            "fields": active,
        }
    )


# ── Bus Detail / Booking Page (catch-all for Bright Data link-following) ──────

@app.get("/bus/{operator}/{route}", response_class=HTMLResponse)
async def bus_detail(request: Request, operator: str, route: str):
    """
    Catch-all booking page for /bus/{operator}/{route} URLs.
    These are the 'Book Now' deep-links that Bright Data follows when it
    encounters next_stage() calls. Without this route the scraper gets 404s.
    Returns a minimal HTML booking confirmation page so the scraper can
    complete gracefully instead of hitting dead_page errors.
    """
    operator_display = operator.replace("-", " ").title()
    route_display = route.replace("-", " ").title()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Book – {operator_display} | DummyBus</title>
  <link rel="stylesheet" href="/static/style.css" />
  <style>
    .booking-box {{
      max-width: 540px;
      margin: 80px auto;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,.10);
      padding: 40px 36px;
      text-align: center;
    }}
    .booking-box h1 {{ color: #2563eb; margin-bottom: 8px; }}
    .booking-box p  {{ color: #555; margin: 6px 0; }}
    .badge {{
      display: inline-block;
      background: #dcfce7;
      color: #16a34a;
      border-radius: 20px;
      padding: 4px 16px;
      font-weight: 600;
      margin-top: 18px;
    }}
    .back-link {{
      display: inline-block;
      margin-top: 28px;
      color: #2563eb;
      text-decoration: none;
      font-weight: 500;
    }}
  </style>
</head>
<body>
  <div class="booking-box">
    <h1>🚌 Booking Page</h1>
    <p><strong>Operator:</strong> {operator_display}</p>
    <p><strong>Route:</strong> {route_display}</p>
    <p><strong>URL:</strong> /bus/{operator}/{route}</p>
    <div class="badge">✅ Demo Booking Page — No 404!</div>
    <br/>
    <a class="back-link" href="/results?from_city=Chennai&to_city=Bengaluru">← Back to Results</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
