"""Flask app factory for the dryer-dashboard project.

This package exposes create_app() so you can run the app with the Flask CLI:

  FLASK_APP=app:create_app flask run

The app serves a small API at /api/sensors (returns JSON) and serves
the static `index.html` at the root.
"""
from flask import Flask, jsonify

from . import sensors as sensors_module


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/")

    @app.route("/api/sensors")
    def api_sensors():
        """Return the latest sensor readings as JSON."""
        data = sensors_module.read_all()
        return jsonify(data)

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app
