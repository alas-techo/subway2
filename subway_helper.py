from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

URL = "https://gotraingo.com/station/721"  # Vernon–Jackson

@app.route("/arrivals")
def arrivals():
    try:
        r = requests.get(URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Grab next 2 arrivals for 7 and 7X
        times = []
        for tag in soup.select("li.timeList.line_7, li.timeList.line_7X"):
            t = tag.get_text(strip=True)
            if t:
                times.append(t)
            if len(times) >= 2:
                break

        return jsonify({
            "next": times[0] if len(times) > 0 else "-",
            "following": times[1] if len(times) > 1 else "-"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
