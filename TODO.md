TODO
====

Findings from a code review of the project. Ordered roughly by importance.


BUGS
----

[ ] find_duplicates: the artist comparison is a no-op
    sph_backend/spotify/service.py:232
        for k in range(0, len(track_i["artists"])):
            if track_i["artists"][k]["id"] != track_j["artists"][k]["id"]:
                continue        # continues the k-loop, not the i/j comparison
    Mismatched artists fall through to the name comparison anyway, so any two
    tracks sharing a title and artist *count* are flagged as duplicates.
    Fix: use break/else, or compare sets of artist ids.
    Also: the trailing "continue" at line 244 is dead code, and the O(n^2)
    scan re-parses album release dates on every comparison.

[ ] Missing None / empty checks on Spotify responses
    item["track"] is None for removed and local tracks. get_playlist handles
    it, but subtract_playlist (service.py:162), find_tracks_in_playlist
    (service.py:192) and find_duplicates (service.py:227) do not.
    track.artists[0] assumes a non-empty artist list
    (_get_latest_song_by_artist_for_playlist, service.py:277).
    Both raise on real-world playlists.


ROBUSTNESS
----------

[ ] No rate-limit handling
    get_new_releases_for_playlist issues one paginated album fetch per artist
    in the playlist - hundreds of sequential requests for a large playlist -
    with no 429 / Retry-After backoff and no caching. This will get throttled.
    Partially mitigated: a 429 is now surfaced to the client as a 429 with
    the Retry-After header (web_api.py:29, main.py:47), but nothing retries.


CLEANUP
-------

[ ] market: "FI" is hardcoded in three places - belongs in settings.
    sph_backend/spotify/service.py:87, 116, 138

[ ] _get_latest_song_by_artist_for_playlist keys off artists[0] and the
    track's album date, so a compilation or reissue inflates the "latest"
    date and suppresses genuine new releases.
    sph_backend/spotify/service.py:273-281

[ ] Almost no tests - only tests/test_settings.py. Service, session client
    and routes are untested.
