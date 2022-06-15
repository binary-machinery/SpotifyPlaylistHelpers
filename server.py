import urllib.parse

from flask import Flask
from flask import Response
from flask import redirect
from flask import render_template
from flask import request
from flask_login import LoginManager, login_user, current_user

from config_loader import ConfigLoader
from spotify_api import SpotifyAuth, SpotifyApi
from users import User, UsersDb

config = ConfigLoader.load()

app = Flask(__name__)
app.secret_key = config["server"]["secret_key"]

login_manager = LoginManager()
login_manager.init_app(app)

users_db = UsersDb()


@login_manager.user_loader
def load_user(user_id):
    return users_db.get_user(user_id)


@app.route("/api/ping", methods=["GET", "POST"])
def handle_ping():
    return Response("Pong", status=200)


@app.route("/", methods=["GET"])
def index():
    user = None
    if current_user.is_authenticated:
        response = SpotifyApi(current_user.access_token).get("/me")
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

    access_token = response.json().get("access_token")
    refresh_token = response.json().get("refresh_token")

    response = SpotifyApi(access_token).get("/me")
    if response.ok:
        user = User(
            response.json()["id"],
            access_token,
            refresh_token
        )
        users_db.set_user(user)
        login_user(user, remember=True)

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["server"]["port"])
