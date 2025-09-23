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

        times = []
        for tag in soup.select("li.timeList"):
            t = tag.get_text(strip=True)
            if t:
                times.append(t)
            if len(times) >= 2:
                break

        return jsonify({
            "station": station_key,
            "next": times[0] if len(times) > 0 else "-",
            "following": times[1] if len(times) > 1 else "-"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
