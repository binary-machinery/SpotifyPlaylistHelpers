import base64
import urllib.parse

import requests
from flask import Flask
from flask import Response
from flask import redirect
from flask import render_template
from flask import request

from config_loader import ConfigLoader

config = ConfigLoader.load()

app = Flask(__name__)
app.secret_key = config["server"]["secret_key"]

access_token = None
user = None


@app.route("/api/ping", methods=["GET", "POST"])
def handle_ping():
    return Response("Pong", status=200)


@app.route("/", methods=["GET"])
def index():
    global user
    if access_token:
        response = requests.get("https://api.spotify.com/v1/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        if response.ok:
            user = response.json()["display_name"]
    return render_template("index.html", user=user)


@app.route("/auth", methods=["GET"])
def auth():
    auth_url = "https://accounts.spotify.com/authorize?"
    params = {
        "client_id": config["spotify"]["client_id"],
        "response_type": "code",
        "scope": "playlist-modify-public playlist-read-private playlist-modify-private",
        "redirect_uri": config["server"]["host"] + "/api/auth_callback"
    }
    return redirect(auth_url + urllib.parse.urlencode(params))


@app.route("/api/auth_callback", methods=["GET"])
def handle_user_auth_callback():
    code = request.args.get("code")
    if not code:
        return Response(request.args.get("error"), status=400)

    client_id = config["spotify"]["client_id"]
    client_secret = config["spotify"]["client_secret"]
    basic_auth = "Basic " + base64.b64encode(bytes(f"{client_id}:{client_secret}", "utf-8")).decode("utf-8")
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": basic_auth
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["server"]["host"] + "/api/auth_callback"
        }
    )
    if not response.ok:
        return Response(response.text, status=response.status_code)

    global access_token
    access_token = response.json().get("access_token")
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["server"]["port"])
