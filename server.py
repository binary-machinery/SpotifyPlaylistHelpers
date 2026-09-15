import secrets
import urllib.parse
from flask import Flask
from flask import Response
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask_login import LoginManager, login_user, current_user, login_required

from config_loader import ConfigLoader
from spotify_api import SpotifyAuth, SpotifyApi
from users import User, UsersDb

config = ConfigLoader.load()

app = Flask(__name__)
app.secret_key = config["server"]["secret_key"]

# Lax keeps the session and "remember me" cookies off cross-site subresource requests,
# so a third-party page cannot trigger a mutating endpoint with an <img> tag.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

login_manager = LoginManager()
login_manager.init_app(app)

users_db = UsersDb()


@login_manager.user_loader
def load_user(user_id):
    return users_db.get_user(user_id)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Healthy"}), 200


@app.route("/", methods=["GET"])
def index():
    user = None
    if current_user.is_authenticated:
        response = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get("/me")
        if response.ok:
            user = response.json()["display_name"]
    return render_template("index.html", user=user)


@app.route("/playlist_new_releases/select_playlist", methods=["GET"])
@login_required
def playlist_new_releases_select_playlist():
    playlists = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html", playlists=playlists, callback="/playlist_new_releases?")


@app.route("/playlist_new_releases", methods=["GET"])
@login_required
def playlist_new_releases():
    playlist_id = request.args.get("playlist_id")
    latest_dates, releases = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token) \
        .get_new_releases_for_playlist(playlist_id)
    return render_template("playlist_new_releases.html", latest_dates=latest_dates, releases=releases)


@app.route("/add_artist_to_playlist/select_playlist", methods=["GET"])
@login_required
def add_artist_to_playlist_select_playlist():
    playlists = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists, callback="/add_artist_to_playlist/select_artist?")


@app.route("/add_artist_to_playlist/select_artist", methods=["GET"])
@login_required
def add_artist_to_playlist_select_artist():
    playlist_id = request.args.get("playlist_id")
    return render_template("add_artist_to_playlist_select_artist.html",
                           playlist_id=playlist_id)


@app.route("/add_artist_to_playlist", methods=["GET"])
@login_required
def add_artist_to_playlist():
    playlist_id = request.args.get("playlist_id")
    artist_id = request.args.get("artist_id")
    SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token) \
        .add_artist_to_playlist(playlist_id, artist_id)
    return render_template("result.html",
                           callback=f"/add_artist_to_playlist/select_artist?playlist_id={playlist_id}")


@app.route("/subtract_playlist/select_playlist1", methods=["GET"])
@login_required
def subtract_playlist_select_playlist1():
    playlists = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           header="Select playlist 1",
                           callback="/subtract_playlist/select_playlist2?")


@app.route("/subtract_playlist/select_playlist2", methods=["GET"])
@login_required
def subtract_playlist_select_playlist2():
    playlist_id1 = request.args.get("playlist_id")
    playlists = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           header="Select playlist 2",
                           callback=f"/subtract_playlist?playlist_id1={playlist_id1}&")


@app.route("/subtract_playlist", methods=["GET"])
@login_required
def subtract_playlist():
    playlist_id1 = request.args.get("playlist_id1")
    playlist_id2 = request.args.get("playlist_id")
    SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token) \
        .subtract_playlist(playlist_id1, playlist_id2)
    return render_template("result.html",
                           callback="/")


@app.route("/delivery/filter/select_playlist", methods=["GET"])
@login_required
def delivery_filter_select_playlist():
    keyword = request.args.get("keyword")
    playlists = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           callback=f"/delivery/filter?keyword={keyword}&")


@app.route("/delivery/filter", methods=["GET"])
@login_required
def delivery_filter():
    playlist_id = request.args.get("playlist_id")
    keyword = request.args.get("keyword")
    SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token) \
        .filter_playlist(current_user.user_id, playlist_id, keyword)
    return render_template("result.html",
                           callback="/")


@app.route("/delivery/filter_duplicates/select_playlist", methods=["GET"])
@login_required
def delivery_filter_duplicates_select_playlist():
    playlists = SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           callback="/delivery/filter_duplicates?")


@app.route("/delivery/filter_duplicates", methods=["GET"])
@login_required
def delivery_filter_duplicates():
    playlist_id = request.args.get("playlist_id")
    SpotifyApi(config, users_db, current_user.access_token, current_user.refresh_token) \
        .filter_duplicates(current_user.user_id, playlist_id)
    return render_template("result.html",
                           callback="/")


@app.route("/auth", methods=["GET"])
def auth():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    auth_url = "https://accounts.spotify.com/authorize?"
    params = {
        "client_id": config["spotify"]["client_id"],
        "response_type": "code",
        "scope": "playlist-modify-public playlist-read-private playlist-modify-private",
        "redirect_uri": config["server"]["host"] + "/auth_callback",
        "state": state
    }
    return redirect(auth_url + urllib.parse.urlencode(params))


@app.route("/auth_callback", methods=["GET"])
def auth_callback():
    expected_state = session.pop("oauth_state", None)
    if not expected_state or not secrets.compare_digest(request.args.get("state", ""), expected_state):
        return Response("Invalid OAuth state", status=400)

    code = request.args.get("code")
    if not code:
        return Response(request.args.get("error"), status=400)

    response = SpotifyAuth(config).token(code)
    if not response.ok:
        return Response(response.text, status=response.status_code)

    access_token = response.json().get("access_token")
    refresh_token = response.json().get("refresh_token")

    response = SpotifyApi(config, users_db, access_token, refresh_token).get("/me")
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
