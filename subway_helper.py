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
        for tag in soup.select("li"):
            t = tag.get_text(strip=True)
            if "|" in t:  # skip "Pick Station"
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
