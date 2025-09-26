from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Map station keys -> URLs (loaded from your stations.json normally)
station_map = {
    "go_train_go_vernon_blvd_jackson_av_station_7": "https://gotraingo.com/station/721",
    "go_train_go_van_cortlandt_park_242_st_station_1": "https://gotraingo.com/station/101",
    # ... add the rest of your stations.json here or load dynamically
}

@app.route("/arrivals")
def arrivals():
    station_key = request.args.get("station")
    if not station_key or station_key not in station_map:
        return jsonify({"error": "Invalid or missing station"}), 400

    url = station_map[station_key]
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Grab next 2 arrivals regardless of line (any li.timeList.*)
        times = []
        for tag in soup.select("li.timeList"):
            t = tag.get_text(strip=True)
            if t:
                times.append(t)
            if len(times) >= 2:
                break

        return jsonify({
            "station": station_key,
            "next": times[0] if len(times) > 0 else "--",
            "following": times[1] if len(times) > 1 else "--"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
