import base64
from typing import Any

import httpx

from sph_backend.settings import Settings


class SpotifyAuth:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings):
        self._http_client = http_client
        self._api_url = "https://accounts.spotify.com/api"
        self._server_host = settings.server_host

        client_id = settings.spotify_client_id
        client_secret = settings.spotify_client_secret.get_secret_value()
        basic_auth = "Basic " + base64.b64encode(bytes(f"{client_id}:{client_secret}", "utf-8")).decode("utf-8")
        self._headers = {
            "Authorization": basic_auth
        }

    async def token(self, code: str) -> dict[str, Any]:
        response = await self._http_client.post(
            self._api_url + "/token",
            headers=self._headers,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._server_host + "/auth_callback"
            }
        )
        if not response.is_success:
            raise Exception(f"{response.status_code}: {response.text}")
        return response.json()

    async def refresh_user_token(self, refresh_token: str) -> dict[str, Any]:
        response = await self._http_client.post(
            self._api_url + "/token",
            headers=self._headers,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )
        if not response.is_success:
            raise Exception(f"{response.status_code}: {response.text}")
        return response.json()
