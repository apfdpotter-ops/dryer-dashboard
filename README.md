# dryer-dashboard

Minimal scaffold for an appliance kiosk dashboard that shows dryer sensors.

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app:create_app
flask run --host=0.0.0.0 --port=5000
```

Visit http://localhost:5000 to see the kiosk UI and http://localhost:5000/api/sensors for the JSON API.

Next steps:
- Replace `app/sensors.py` with real sensor code.
- Add authentication/SSL for production.
- Build a nicer kiosk UI in `static/index.html`.
