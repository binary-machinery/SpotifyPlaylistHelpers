class SpotifyApiError(Exception):
    """Generic Spotify API error"""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Spotify API Error: {status_code}: {body}")

    def __str__(self):
        return f"Spotify API Error: {self.status_code}: {self.body}"


class SpotifyAuthError(SpotifyApiError):
    """Token exchange or refresh failed; the user must re-authenticate."""

    def __str__(self):
        return f"Spotify Auth Error: {self.status_code}: {self.body}"


class SpotifyRateLimitError(SpotifyApiError):
    """Too many requests to Spotify API"""

    def __init__(self, status_code: int, body: str, retry_after: str | None = None):
        self.retry_after = retry_after
        super().__init__(status_code, body)

    def __str__(self):
        return f"Spotify Rate Limit Error: {self.status_code}: {self.body}: RetryAfter={self.retry_after}"
