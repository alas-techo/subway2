from flask import Flask, jsonify, request
import json
import time
from datetime import datetime, timezone

from nyct_gtfs import NYCTFeed  # pip install nyct-gtfs

app = Flask(__name__)

with open("stations_rt.json", "r") as f:
    STATIONS = json.load(f)

# Cache feeds so we don't hammer the MTA endpoints
FEED_CACHE = {}  # feed_id -> {"ts": unix, "feed": NYCTFeed}
CACHE_TTL_SEC = 8  # keep short; your ESP polls ~15s


def now_utc() -> int:
    return int(time.time())


def get_feed(feed_id: str) -> NYCTFeed:
    entry = FEED_CACHE.get(feed_id)
    t = now_utc()
    if entry and (t - entry["ts"] <= CACHE_TTL_SEC):
        return entry["feed"]

    # NYCTFeed pulls the official GTFS-RT feed for that line group (e.g. "1", "7")
    feed = NYCTFeed(feed_id)
    FEED_CACHE[feed_id] = {"ts": t, "feed": feed}
    return feed


def next_two_arrivals(feed: NYCTFeed, stop_id: str, route_filter: str | None = None):
    """
    Returns a sorted list of (arrival_epoch_sec, route_id) for the next arrivals at stop_id.
    """
    tnow = now_utc()
    arrivals = []

    # nyct-gtfs gives you "trips" with stop time updates
    for trip in feed.trips:
        # Optional: only keep a specific route, e.g. "7" or "1"
        if route_filter and trip.route_id != route_filter:
            continue

        # trip.stop_time_updates is a dict keyed by stop_id (like "721N")
        stu = trip.stop_time_updates.get(stop_id)
        if not stu:
            continue

        # arrival time can be None; fallback to departure
        arr = stu.arrival or stu.departure
        if not arr:
            continue

        # keep only future-ish arrivals
        if arr >= tnow - 5:
            arrivals.append((arr, trip.route_id))

    arrivals.sort(key=lambda x: x[0])
    return arrivals[:2]


def format_minutes(epoch_sec: int) -> str:
    # Convert to "Due"/minutes like your old API vibe
    tnow = now_utc()
    delta = max(0, epoch_sec - tnow)
    mins = int(round(delta / 60.0))
    if mins <= 0:
        return "Due"
    return str(mins)


@app.route("/arrivals")
def arrivals():
    station_key = request.args.get("station", "").strip()
    if not station_key or station_key not in STATIONS:
        return jsonify({"error": "Invalid or missing station"}), 400

    # Direction comes from your ESP/app later, but we can accept it now:
    # dir=N or dir=S (optional). If omitted, default to S (downtown-ish).
    direction = request.args.get("dir", "S").strip().upper()
    if direction not in ("N", "S"):
        direction = "S"

    cfg = STATIONS[station_key]
    feed_id = str(cfg["feed"])
    stop_id = cfg["stop_id_n"] if direction == "N" else cfg["stop_id_s"]
    route_filter = str(cfg.get("line") or "").strip() or None

    try:
        feed = get_feed(feed_id)
        arrs = next_two_arrivals(feed, stop_id, route_filter=route_filter)

        if len(arrs) == 0:
            return jsonify({
                "station": station_key,
                "dir": direction,
                "next": "-",
                "following": "-"
            })

        next_txt = format_minutes(arrs[0][0])
        foll_txt = format_minutes(arrs[1][0]) if len(arrs) > 1 else "-"

        return jsonify({
            "station": station_key,
            "dir": direction,
            "next": next_txt,
            "following": foll_txt
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def root():
    return jsonify({"ok": True, "endpoints": ["/arrivals?station=...&dir=N|S"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
