"""Flask app factory for the dryer-dashboard project.

This package exposes create_app() so you can run the app with the Flask CLI:

  FLASK_APP=app:create_app flask run

The app serves a small API at /api/sensors (returns JSON) and serves
the static `index.html` at the root.
"""
from flask import Flask, jsonify
import os
from pathlib import Path
from datetime import datetime

from . import sensors as sensors_module

# Simple in-memory auger state. This is deliberately minimal: it keeps the
# current discharge auger percentage (0..100). For persistence across reboots
# or multiple processes you should move this to a small database or expose it
# via a hardware controller. Kept here for quick UI control during testing.
_AUGER_PCT = 50


def create_app():
    # Serve static files from the top-level `static/` directory so the
    # kiosk UI (located at ../static/index.html) is available at '/'. Using
    # an absolute path avoids issues when the working directory changes.
    project_root = Path(__file__).resolve().parent.parent
    static_dir = str(project_root / 'static')
    app = Flask(__name__, static_folder=static_dir, static_url_path="/")

    @app.route("/api/sensors")
    def api_sensors():
        """Return the latest sensor readings as JSON.

        Prefer a sensors.read_all() helper when the module provides it. If not
        available we call get_temps()/get_moisture() and build a small JSON
        payload so the endpoint remains usable across different sensor modules.
        """
        if hasattr(sensors_module, "read_all"):
            try:
                return jsonify(sensors_module.read_all())
            except Exception:
                # Fall through to a safer fallback below and return whatever we can
                pass

        # Fallback: build a minimal response from available getters
        try:
            inlet_c, outlet_c = sensors_module.get_temps(return_fahrenheit=False)
        except Exception:
            inlet_c = outlet_c = None

        try:
            inlet_v, outlet_v = sensors_module.get_moisture()
        except Exception:
            inlet_v = outlet_v = None

        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "inlet_c": inlet_c,
            "outlet_c": outlet_c,
            "inlet_v": inlet_v,
            "outlet_v": outlet_v,
        }

        return jsonify(data)


    @app.route("/data")
    def data_for_ui():
        """Return transformed sensor data tailored to the kiosk UI.

        Fields returned (example):
          - temp_in_c, temp_out_c (floats or null)
          - temp_in_f, temp_out_f (floats or null)
          - moisture_in (0-100 %), moisture_out (0-100 %)
          - bushels_per_hr (float) -- crude estimate for now
          - timestamp
        """
        try:
            payload = sensors_module.read_all() if hasattr(sensors_module, 'read_all') else {}
        except Exception:
            payload = {}

        inlet_c = payload.get('inlet_c')
        outlet_c = payload.get('outlet_c')
        inlet_v = payload.get('inlet_v')
        outlet_v = payload.get('outlet_v')

        def c_to_f(c):
            if c is None:
                return None
            return (c * 9 / 5) + 32

        # Convert voltage (0..3.3) to percent (0..100). Clamp defensively.
        def v_to_pct(v):
            try:
                pct = (float(v) / 3.3) * 100.0
                if pct < 0:
                    pct = 0.0
                if pct > 100:
                    pct = 100.0
                return pct
            except Exception:
                return None

        moisture_in = v_to_pct(inlet_v)
        moisture_out = v_to_pct(outlet_v)

        # Very rough bushels/hr estimate: linear scale from dry -> full rate.
        # This is a placeholder and should be replaced with real calibration.
        if moisture_in is None:
            bushels = None
        else:
            bushels = max(0.0, (1.0 - (moisture_in / 100.0)) * 100.0)

        # Determine per-sensor health flags from the sensors payload. If the
        # sensors module provides an `errors` list we use that to mark inlet
        # and outlet as healthy/unhealthy. Otherwise we default to True when
        # readings look present.
        errs = payload.get('errors') if isinstance(payload, dict) else None
        simulated = bool(payload.get('simulated')) if isinstance(payload, dict) else False

        if isinstance(errs, list) and errs:
            inlet_ok = not any('inlet' in str(e).lower() for e in errs)
            outlet_ok = not any('outlet' in str(e).lower() for e in errs)
        else:
            # If no explicit errors, consider a sensor OK when we have a value
            inlet_ok = inlet_c is not None or inlet_v is not None
            outlet_ok = outlet_c is not None or outlet_v is not None

        data = {
            'timestamp': payload.get('timestamp'),
            'temp_in_c': inlet_c,
            'temp_out_c': outlet_c,
            'temp_in_f': None if inlet_c is None else c_to_f(inlet_c),
            'temp_out_f': None if outlet_c is None else c_to_f(outlet_c),
            'moisture_in': moisture_in,
            'moisture_out': moisture_out,
            'bushels_per_hr': bushels,
            'auger_pct': globals().get('_AUGER_PCT', None),
            'inlet_ok': bool(inlet_ok),
            'outlet_ok': bool(outlet_ok),
            'simulated': simulated,
        }
        return jsonify(data)


    @app.route('/status')
    def ui_status():
        """Return a minimal status object for the UI (e.g. recording state).

        We mark `recording` True when sensors returned no errors in read_all().
        """
        recording = True
        try:
            payload = sensors_module.read_all() if hasattr(sensors_module, 'read_all') else {}
            errs = payload.get('errors') if isinstance(payload, dict) else None
            if errs:
                recording = False
        except Exception:
            recording = False

        return jsonify({'recording': recording})

    @app.route('/auger', methods=['GET', 'POST'])
    def auger_control():
        """Simple endpoint to get/set the discharge auger percentage.

        GET  -> {'auger_pct': number}
        POST -> accepts JSON {delta: number} to change current value by delta
                (positive or negative). Returns {'auger_pct': new_value}.
        """
        nonlocal_vars = globals()
        try:
            cur = int(nonlocal_vars.get('_AUGER_PCT', 50))
        except Exception:
            cur = 50

        from flask import request
        if request.method == 'POST':
            try:
                j = request.get_json(force=True)
                delta = int(j.get('delta', 0))
            except Exception:
                delta = 0

            new = max(0, min(100, cur + delta))
            nonlocal_vars['_AUGER_PCT'] = new
            return jsonify({'auger_pct': new})

        # GET
        return jsonify({'auger_pct': cur})

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app
