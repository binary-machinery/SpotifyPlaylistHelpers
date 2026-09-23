TODO
====

Findings from a code review of the project. Ordered roughly by importance.


BUGS
----

[ ] Missing None / empty checks on Spotify responses
    item["track"] is None for removed and local tracks. get_playlist handles
    it, but subtract_playlist, find_tracks_in_playlist and find_duplicates
    (all in sph_backend/spotify/service.py) do not.
    track.artists[0] assumes a non-empty artist list
    (_get_latest_song_by_artist_for_playlist).
    Both raise on real-world playlists.
    Related: local-file artists have id None, so find_duplicates treats two
    same-titled local tracks as duplicates whenever their artist counts
    match. Fall back to comparing artist names when the id is None.


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
