# JailoApp backend (Django + DRF)

Early warning for mudflows, floods, avalanches and fires in Kyrgyzstan, plus a village marketplace (no online payments).

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill NASA_FIRMS_MAP_KEY and TELEGRAM_BOT_TOKEN
python manage.py migrate
python manage.py seed_demo      # villages, sensor nodes, demo users, listings (prints admin password once)
python manage.py runserver      # API on :8000, docs on /api/docs/
python manage.py run_worker     # weather + NASA FIRMS + risk engine loop (--once for a single pass)
python manage.py run_bot        # Telegram bot (long polling)
python manage.py test           # 66 tests
```

## Demo

```bash
python scripts/simulate_node.py mudflow --nodes ak-tash-n1,ak-tash-n2 --gap 20   # real HTTP, like a sensor
python manage.py simulate_mudflow --reset                                             # same, directly in the DB
python scripts/simulate_node.py fire --nodes ak-tash-fire
```

Two nodes shaking in sequence -> mudflow alert goes Critical with an arrival time (ETA) -> Telegram messages to people nearby -> siren command for the LoRa gateway.

## API (full docs at `/api/docs/`)

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/otp/request/`, `/otp/verify/`, `/token/refresh/`, `GET /me/`, `/watched-locations/` |
| Geo | `GET /api/geo/villages/`, `/evacuation-points/` |
| Sensors | `POST /api/sensors/ingest/` (header `X-Device-Key`), `GET /nodes/`, `/events/` |
| Risk | `GET /api/risk/overview/`, `/villages/<id>/`, `/villages/<id>/history/`, `/hotspots/`, `POST /refresh/` (rescuer) |
| Alerts | `GET /api/alerts/`, `/active/`, `POST /create/`, `/simulate/`, `/<id>/resolve/`, `/dismiss/`, `/safe/`; siren: `GET /siren/pending/`, `POST /siren/<id>/ack/` |
| Reports | `POST /api/reports/`, `POST /<id>/confirm/` or `/dismiss/` (rescuer) |
| Market | `/api/market/categories/`, `/listings/`, `/orders/`, `/threads/` |

Login: phone number -> one-time code sent by the Telegram bot (the user shares their number with the bot once). With `DEBUG=True` the code is also returned in the response for development.

## How it decides

- Sensor vibration is classified as noise / vehicle / earthquake / mudflow (FFT + persistence). Thresholds are in `apps/sensors/classifier.py` and must be calibrated with real field data.
- Mudflow ETA = distance to the village along the node order x 1.3, divided by speed measured between nodes (assumed 20 km/h with one node, flagged as assumed).
- Risk score 0-100 per hazard: Low <25, Medium <50, High <75, Critical >=75. High notifies people; Critical also triggers the siren. Avalanche is a weather index only (no sensor).
- Alerts from the engine clear themselves after 30 quiet minutes; manual, report and demo alerts stay until a rescuer resolves them.

## Notes

- Secrets live only in `.env` (gitignored). Rotate the bot token in @BotFather if it was ever shared.
- Kyrgyz (ky) texts need review by a native speaker before real use.
- Market orders have no payment; phone numbers are shared only after the seller accepts.
