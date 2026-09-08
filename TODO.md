TODO
====

Findings from a code review of the project. Ordered roughly by importance.


BUGS
----

[ ] _http drops the request body on the 401 retry
    spotify_api.py:117
        response = self._http(function, endpoint, params, retry=False)
    The data= argument is not forwarded. Every mutating call (add tracks,
    delete tracks, create playlist) that hits an expired token retries with
    no payload. Since the retry path is exactly the token-refresh path, this
    is a real intermittent data-loss bug.
    Fix: pass data through -> self._http(function, endpoint, params, data, retry=False)

[ ] filter_duplicates: the artist comparison is a no-op  (the existing FIXME)
    spotify_api.py:405
        for k in range(0, len(track_i["artists"])):
            if track_i["artists"][k]["id"] != track_j["artists"][k]["id"]:
                continue        # continues the k-loop, not the i/j comparison
    Mismatched artists fall through to the name comparison anyway, so any two
    tracks sharing a title and artist *count* are flagged as duplicates.
    Fix: use break/else, or compare sets of artist ids.
    Also: the trailing "continue" at line 417 is dead code, and the O(n^2)
    scan re-parses album release dates on every comparison.

[ ] get_playlist builds a malformed URL
    spotify_api.py:192
        self.get(f"/playlists/{playlist_id}?fields=id,name,owner(display_name)")
    The endpoint already contains a query string and _http appends another
    "?{urlencode(params)}", producing a trailing "?" inside the fields value.
    Fix: pass params={"fields": "..."} like the other call sites do.

[ ] get_user crashes on a stale session
    users.py:46
        res = self._execute_and_fetch_one(...)
        return User(res[0], res[1], res[2])
    fetchone() returns None when the row is gone, then res[0] raises. This is
    the @login_manager.user_loader, so a deleted DB row turns every request
    into a 500 instead of logging the user out.
    Fix: return None if res is None.

[ ] SQLite connections are never closed
    users.py:27, users.py:33
    "with sqlite3.Connection(...)" commits the transaction on exit but does
    NOT close the connection, unlike a file handle. One leaked connection per
    request.
    Fix: wrap in contextlib.closing, or close explicitly.

[ ] Missing None / empty checks on Spotify responses
    track_json["track"] is None for removed and local tracks; track.artists[0]
    assumes a non-empty artist list (get_latest_song_by_artist, spotify_api.py:246).
    Both raise on real-world playlists.


SECURITY
--------

[ ] OAuth "state" parameter is missing
    server.py:160-195
    The standard CSRF defense for the authorization code flow is absent, so
    /auth_callback accepts any "code" an attacker delivers to a victim's
    browser, binding the victim's session to the attacker's Spotify account.
    Fix: generate a random state, store it in the session, verify on callback.

[ ] All mutating actions are GET requests
    /add_artist_to_playlist, /subtract_playlist, /delivery/filter,
    /delivery/filter_duplicates all modify playlists via a link click, with
    remember=True session cookies. Any page can trigger them cross-site with
    an <img> tag. Small blast radius for a personal tool, but POST + CSRF
    tokens is the correct shape.


ROBUSTNESS
----------

[ ] Silent failure paths
    - _refresh_token (spotify_api.py:88) ignores a failed refresh and lets the
      caller proceed with a dead token.
    - auth_callback (server.py:185) redirects to / with no message if /me fails.
    - Every API error becomes a bare Exception(f"{status}: {text}") and lands
      on the Werkzeug 500 page.
    Fix: error templates + @app.errorhandler, and surface refresh failures.

[ ] No rate-limit handling
    get_new_releases_for_playlist issues one paginated album fetch per artist
    in the playlist - hundreds of sequential requests for a large playlist -
    with no 429 / Retry-After backoff and no caching. This will get throttled.


CLEANUP
-------

[ ] get_playlists hand-rolls pagination that get_paginated_items already does
    spotify_api.py:166-189 - leftover from the "Get all pages for playlists" commit.

[ ] Album.release_date: datetime annotates the module, not datetime.datetime
    spotify_api.py:33

[ ] filter_playlist keeps tracks MATCHING the keyword, but the UI calls it
    "filter out" - the naming inverts the behavior.
    spotify_api.py:347, templates/index.html

[ ] market: "FI" is hardcoded in three places - belongs in config.
    spotify_api.py:259, 289, 311

[ ] requirements.txt is unpinned (flask, flask-login, requests).

[ ] app.run(host="0.0.0.0") ships the Werkzeug dev server on all interfaces.
    server.py:199

[ ] /api/ping is unused.
    server.py:30

[ ] get_latest_song_by_artist keys off artists[0] and the track's album date,
    so a compilation or reissue inflates the "latest" date and suppresses
    genuine new releases.
    spotify_api.py:242-250

[ ] No tests, no README.
