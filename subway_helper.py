from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import json

app = Flask(__name__)

with open("stations.json") as f:
    STATIONS = json.load(f)

@app.route("/arrivals")
def arrivals():
    station_key = request.args.get("station")
    if not station_key or station_key not in STATIONS:
        return jsonify({"error": "Invalid or missing station"}), 400

    station_url = STATIONS[station_key]

    try:
        r = requests.get(station_url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Debug: grab the first 10 <li> items so we can see what’s inside
        debug_items = [li.get_text(strip=True) for li in soup.select("li")[:10]]

        return jsonify({
            "station": station_key,
            "debug_items": debug_items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
