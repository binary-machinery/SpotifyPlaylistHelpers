from typing import Any, Callable

import httpx

from sph_backend.settings import Settings
from sph_backend.spotify.auth import SpotifyAuth
from sph_backend.spotify.errors import SpotifyRateLimitError, SpotifyApiError, SpotifyAuthError


class SpotifyClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings,
                 access_token: str, refresh_token: str, on_token_refreshed: Callable[[str, str], None] | None = None):
        self._http_client = http_client
        self._api_url = "https://api.spotify.com/v1"
        self._settings = settings
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._on_token_refreshed = on_token_refreshed

    async def get(self, endpoint, params=None, retry=True) -> Any:
        return await self._http(method="GET", endpoint=endpoint, params=params, retry=retry)

    async def post(self, endpoint, params=None, data=None, json=None, retry=True) -> Any:
        return await self._http(method="POST", endpoint=endpoint, params=params, data=data, json=json, retry=retry)

    async def put(self, endpoint, params=None, data=None, json=None, retry=True) -> Any:
        return await self._http(method="PUT", endpoint=endpoint, params=params, data=data, json=json, retry=retry)

    async def delete(self, endpoint, params=None, data=None, json=None, retry=True) -> Any:
        return await self._http(method="DELETE", endpoint=endpoint, params=params, data=data, json=json, retry=retry)

    async def get_paginated_items(self, endpoint: str, params: dict[str, Any] | None = None, limit: int = 20) \
            -> list[dict[str, Any]]:
        if params is None:
            params = {}
        params["limit"] = limit
        has_data = True
        offset = 0
        items = []
        while has_data:
            params["offset"] = offset
            json = await self.get(endpoint, params)
            items.extend(json["items"])
            has_data = False
            if json["total"] > offset + limit:
                has_data = True
                offset += limit

        return items

    async def _http(self, method: str, endpoint: str, params=None, data=None, json=None, retry=True) -> Any:
        response = await self._http_client.request(
            method=method,
            url=f"{self._api_url}{endpoint}",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json"
            },
            params=params,
            data=data,
            json=json
        )

        if not response.is_success:
            if response.status_code == 429:
                raise SpotifyRateLimitError(
                    status_code=response.status_code,
                    body=response.text,
                    retry_after=response.headers.get("Retry-After")
                )

            if response.status_code == 401 and retry:
                await self._refresh_user_token()
                return await self._http(method=method, endpoint=endpoint, params=params,
                                        data=data, json=json, retry=False)
            elif response.status_code == 401:
                raise SpotifyAuthError(status_code=response.status_code, body=response.text)
            else:
                raise SpotifyApiError(status_code=response.status_code, body=response.text)

        if not response.content:
            return None
        return response.json()

    async def _refresh_user_token(self):
        auth_response_json = await SpotifyAuth(self._http_client, self._settings).refresh_user_token(
            self._refresh_token)
        self._access_token = auth_response_json["access_token"]
        self._refresh_token = auth_response_json.get("refresh_token", self._refresh_token)
        if self._on_token_refreshed is not None:
            self._on_token_refreshed(self._access_token, self._refresh_token)
