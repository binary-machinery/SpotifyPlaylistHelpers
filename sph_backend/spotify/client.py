from typing import Any

import httpx

from sph_backend.settings import Settings
from sph_backend.spotify.auth import SpotifyAuth
from sph_backend.users import User, UsersDb


class SpotifyClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings, users_db: UsersDb,
                 access_token: str, refresh_token: str):
        self._http_client = http_client
        self._api_url = "https://api.spotify.com/v1"
        self._settings = settings
        self._users_db = users_db
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def _update_token(self):
        auth_response = await SpotifyAuth(self._http_client, self._settings).update_token(self._refresh_token)
        if auth_response.is_success:
            auth_response_json = auth_response.json()
            self._access_token = auth_response_json.get("access_token")
            self._refresh_token = auth_response_json.get("refresh_token", self._refresh_token)
            user_data_json = await self.get("/me")
            user = User(
                user_id=user_data_json["id"],
                access_token=self._access_token,
                refresh_token=self._refresh_token
            )
            self._users_db.set_user(user)

    async def get(self, endpoint, params=None, retry=True) -> Any:
        return await self._http(method="GET", endpoint=endpoint, params=params, retry=retry)

    async def post(self, endpoint, params=None, data=None, json=None, retry=True) -> Any:
        return await self._http(method="POST", endpoint=endpoint, params=params, data=data, json=json, retry=retry)

    async def put(self, endpoint, params=None, data=None, json=None, retry=True) -> Any:
        return await self._http(method="PUT", endpoint=endpoint, params=params, data=data, json=json, retry=retry)

    async def delete(self, endpoint, params=None, data=None, json=None, retry=True) -> Any:
        return await self._http(method="DELETE", endpoint=endpoint, params=params, data=data, json=json, retry=retry)

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
            if response.status_code == 401 and retry:
                await self._update_token()
                response = await self._http(method=method, endpoint=endpoint, params=params,
                                            data=data, json=json, retry=False)
            else:
                raise Exception(f"{response.status_code}: {response.text}")

        if not response.content:
            return None
        return response.json()

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
