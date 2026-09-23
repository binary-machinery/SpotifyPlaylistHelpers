from typing import Any

import httpx

from sph_backend.spotify.errors import SpotifyAuthError, SpotifyApiError, SpotifyRateLimitError


class SpotifyWebApi:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client
        self._api_url = "https://api.spotify.com/v1"

    async def request(self, method: str, endpoint: str, *, access_token: str, params: dict[str, Any] | None = None,
                      json: dict[str, Any] | None = None) -> Any:
        response = await self._http_client.request(
            method=method,
            url=f"{self._api_url}{endpoint}",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            params=params,
            json=json
        )

        if not response.is_success:
            match response.status_code:
                case 401:
                    raise SpotifyAuthError(status_code=response.status_code, body=response.text)
                case 429:
                    raise SpotifyRateLimitError(
                        status_code=response.status_code,
                        body=response.text,
                        retry_after=response.headers.get("Retry-After")
                    )
                case _:
                    raise SpotifyApiError(status_code=response.status_code, body=response.text)

        if not response.content:
            return None
        return response.json()
