import urllib.parse

from flask import Flask
from flask import Response
from flask import redirect
from flask import render_template
from flask import request

from config_loader import ConfigLoader
from spotify_api import SpotifyAuth, SpotifyApi

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
        response = SpotifyApi(access_token).get("/me")
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
        "redirect_uri": config["server"]["host"] + "/auth_callback"
    }
    return redirect(auth_url + urllib.parse.urlencode(params))


@app.route("/auth_callback", methods=["GET"])
def auth_callback():
    code = request.args.get("code")
    if not code:
        return Response(request.args.get("error"), status=400)

    response = SpotifyAuth(config).token(code)
    if not response.ok:
        return Response(response.text, status=response.status_code)

    global access_token
    access_token = response.json().get("access_token")
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["server"]["port"])
