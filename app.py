import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return "AlexaMusic is running", 200


@app.route("/healthz")
def health():
    return jsonify(status="ok", service="AlexaMusic"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
