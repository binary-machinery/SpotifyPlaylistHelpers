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
