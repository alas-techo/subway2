from flask import Flask, jsonify, request
import json
import time
from datetime import datetime, timezone

from nyct_gtfs import NYCTFeed  # pip install nyct-gtfs

app = Flask(__name__)

with open("stations_rt.json", "r") as f:
    STATIONS = json.load(f)

FEED_CACHE = {}  # feed_id -> {"ts": unix, "feed": NYCTFeed}
CACHE_TTL_SEC = 6  # a bit tighter since you're polling every 10s


def now_utc() -> int:
    return int(time.time())


def dt_to_epoch_seconds(dt: datetime | None) -> int | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def get_feed(feed_id: str) -> NYCTFeed:
    t = now_utc()
    entry = FEED_CACHE.get(feed_id)
    if entry and (t - entry["ts"] <= CACHE_TTL_SEC):
        return entry["feed"]

    feed = NYCTFeed(feed_id)
    FEED_CACHE[feed_id] = {"ts": t, "feed": feed}
    return feed


def next_two_arrivals(feed: NYCTFeed, stop_id: str, route_filter: str | None = None):
    tnow = now_utc()
    arrivals: list[int] = []

    for train in feed.trips:
        if route_filter and train.route_id != route_filter:
            continue

        for stu in train.stop_time_updates:
            if getattr(stu, "stop_id", None) != stop_id:
                continue

            arr_dt = getattr(stu, "arrival", None) or getattr(stu, "departure", None)
            arr_epoch = dt_to_epoch_seconds(arr_dt)
            if arr_epoch is None:
                break

            if arr_epoch >= tnow - 5:
                arrivals.append(arr_epoch)
            break

    arrivals.sort()
    return arrivals[:2]


def format_minutes(arrival_epoch: int) -> str:
    delta = max(0, arrival_epoch - now_utc())
    mins = int(round(delta / 60.0))
    if mins <= 0:
        return "Due"
    return str(mins)


@app.route("/arrivals")
def arrivals():
    station_key = request.args.get("station", "").strip()
    if not station_key or station_key not in STATIONS:
        return jsonify({"error": "Invalid or missing station"}), 400

    direction = request.args.get("dir", "S").strip().upper()
    if direction not in ("N", "S"):
        direction = "S"

    cfg = STATIONS[station_key]
    feed_id = str(cfg["feed"])
    stop_id = cfg["stop_id_n"] if direction == "N" else cfg["stop_id_s"]
    route_filter = (str(cfg.get("line") or "").strip() or None)

    try:
        feed = get_feed(feed_id)
        arrs = next_two_arrivals(feed, stop_id, route_filter=route_filter)

        next_txt = "-"
        foll_txt = "-"
        if len(arrs) >= 1:
            next_txt = format_minutes(arrs[0])
        if len(arrs) >= 2:
            foll_txt = format_minutes(arrs[1])

        return jsonify({
            "station": station_key,
            "dir": direction,
            "label": cfg.get("label", ""),
            "line": cfg.get("line", ""),
            "dir_label": cfg.get("label_n", "N") if direction == "N" else cfg.get("label_s", "S"),
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
