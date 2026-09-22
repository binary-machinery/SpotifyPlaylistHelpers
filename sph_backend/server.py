from flask import Flask
from flask import Flask
from flask import Response
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask_login import LoginManager, login_user, current_user, login_required
from sph_backend.config_loader import ConfigLoader

from sph_backend.spotify.client import SpotifyClient

config = ConfigLoader.load()

app = Flask(__name__)
app.secret_key = config["server"]["secret_key"]


@app.route("/subtract_playlist/select_playlist1", methods=["GET"])
@login_required
def subtract_playlist_select_playlist1():
    playlists = SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           header="Select playlist 1",
                           callback="/subtract_playlist/select_playlist2?")


@app.route("/subtract_playlist/select_playlist2", methods=["GET"])
@login_required
def subtract_playlist_select_playlist2():
    playlist_id1 = request.args.get("playlist_id")
    playlists = SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           header="Select playlist 2",
                           callback=f"/subtract_playlist?playlist_id1={playlist_id1}&")


@app.route("/subtract_playlist", methods=["GET"])
@login_required
def subtract_playlist():
    playlist_id1 = request.args.get("playlist_id1")
    playlist_id2 = request.args.get("playlist_id")
    SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token) \
        .subtract_playlist(playlist_id1, playlist_id2)
    return render_template("result.html",
                           callback="/")


@app.route("/delivery/filter/select_playlist", methods=["GET"])
@login_required
def delivery_filter_select_playlist():
    keyword = request.args.get("keyword")
    playlists = SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           callback=f"/delivery/filter?keyword={keyword}&")


@app.route("/delivery/filter", methods=["GET"])
@login_required
def delivery_filter():
    playlist_id = request.args.get("playlist_id")
    keyword = request.args.get("keyword")
    SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token) \
        .filter_playlist(current_user.user_id, playlist_id, keyword)
    return render_template("result.html",
                           callback="/")


@app.route("/delivery/filter_duplicates/select_playlist", methods=["GET"])
@login_required
def delivery_filter_duplicates_select_playlist():
    playlists = SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token).get_playlists()
    return render_template("playlist_selector.html",
                           playlists=playlists,
                           callback="/delivery/filter_duplicates?")


@app.route("/delivery/filter_duplicates", methods=["GET"])
@login_required
def delivery_filter_duplicates():
    playlist_id = request.args.get("playlist_id")
    SpotifyClient(config, users_db, current_user.access_token, current_user.refresh_token) \
        .filter_duplicates(current_user.user_id, playlist_id)
    return render_template("result.html",
                           callback="/")
