
# dryer-dashboard

Minimal scaffold for an appliance kiosk dashboard that shows dryer sensors.

Run locally (FastAPI + Uvicorn):

```bash
# create and activate a virtualenv (if you haven't already)
python -m venv .venv
source .venv/bin/activate

# install dependencies listed in requirements.txt
pip install -r requirements.txt

# start the FastAPI server with uvicorn (module:path:app)
# the app object is at `app.main:app`
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit http://localhost:8000 to see the kiosk UI (served at `/`) and the JSON API at:

- GET /status  -> health check
- GET /data    -> processed dryer data (temps, moisture, bushels/hr)

Quick test with curl:

```bash
curl http://localhost:8000/status
curl http://localhost:8000/data
```

Next steps:
- Replace `app/sensors.py` with real sensor code.
- Add authentication/SSL for production.
- Build a nicer kiosk UI in `static/index.html`.
