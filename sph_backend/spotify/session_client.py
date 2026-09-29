import asyncio
import logging
import random
from asyncio import Lock
from collections.abc import Callable, Awaitable, Iterable
from functools import partial
from itertools import batched
from typing import Any

from sph_backend.spotify.auth_api import SpotifyAuthApi
from sph_backend.spotify.errors import SpotifyAuthError, SpotifyApiError, SpotifyRateLimitError
from sph_backend.spotify.web_api import SpotifyWebApi
from sph_backend.utils.concurrency import run_in_parallel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SpotifySessionClient:
    def __init__(self, spotify_web_api: SpotifyWebApi, spotify_auth_api: SpotifyAuthApi,
                 access_token: str, refresh_token: str, on_token_refreshed: Callable[[str, str], Awaitable[None]]):
        self._web_api = spotify_web_api
        self._auth_api = spotify_auth_api
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._on_token_refreshed = on_token_refreshed
        self._token_refresh_lock = Lock()

    async def get(self, endpoint: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._request_web_api(method="GET", endpoint=endpoint, params=params)

    async def post(self, endpoint: str, *, params: dict[str, Any] | None = None,
                   json: dict[str, Any] | None = None) -> Any:
        return await self._request_web_api(method="POST", endpoint=endpoint, params=params, json=json)

    async def put(self, endpoint: str, *, params: dict[str, Any] | None = None,
                  json: dict[str, Any] | None = None) -> Any:
        return await self._request_web_api(method="PUT", endpoint=endpoint, params=params, json=json)

    async def delete(self, endpoint: str, *, params: dict[str, Any] | None = None,
                     json: dict[str, Any] | None = None) -> Any:
        return await self._request_web_api(method="DELETE", endpoint=endpoint, params=params, json=json)

    async def get_paginated_items(
            self,
            endpoint: str,
            *,
            params: dict[str, Any] | None = None,
            limit: int = 20,  # max limit is 50
            max_parallel_requests: int = 10
    ) -> list[dict[str, Any]]:
        if params is None:
            params = {}
        else:
            params = params.copy()

        params["limit"] = limit
        params["offset"] = 0
        response_json = await self.get(endpoint, params=params)

        items = [*response_json["items"]]

        if response_json["total"] > limit:
            jobs = []
            for offset in range(limit, response_json["total"], limit):
                jobs.append(
                    partial(self.get, endpoint=endpoint, params={**params, "offset": offset})
                )
            results = await run_in_parallel(jobs, max_parallel=max_parallel_requests)

            for res in results:
                items.extend(res["items"])

        return items

    async def post_in_chunks(
            self,
            endpoint: str,
            *,
            items: Iterable,
            chunk_field_name: str,
            chunk_size: int = 100,
            params: dict[str, Any] | None = None
    ) -> None:
        # run in sequence to keep the correct order and avoid concurrent playlist modifications
        for chunk in batched(items, chunk_size):
            await self.post(
                endpoint=endpoint,
                params=params,
                json={chunk_field_name: chunk}
            )

    async def delete_in_chunks(
            self,
            endpoint: str,
            *,
            items: Iterable,
            chunk_field_name: str,
            chunk_size: int = 100,
            params: dict[str, Any] | None = None,
            max_parallel_requests: int = 5
    ) -> None:
        # Spotify might respond with 502 on concurrent playlist updates.
        # Limit requests and repeat if failed. Deletion is idempotent.

        async def delete_chunk(chunk_, chunk_index_) -> None:
            max_retries = 2
            attempt = 0
            while True:
                try:
                    await self.delete(
                        endpoint=endpoint,
                        params=params,
                        json={chunk_field_name: chunk_}
                    )
                    break
                except SpotifyApiError as e:
                    if e.status_code < 500:
                        raise

                    logger.debug("Spotify API error for concurrent deletion, chunk: %i,  attempt: %i, %s",
                                 chunk_index_, attempt, e)
                    if attempt >= max_retries:
                        logger.warning("Failed to delete a chunk after retries, chunk: %i,  attempt: %i, %s",
                                       chunk_index_, attempt, e)
                        raise

                    # wait for random time from 0 to max delay
                    # exponential backoff for max delay: 50ms, 100ms, 200ms
                    await asyncio.sleep(random.uniform(0, 0.05 * pow(2, attempt)))
                    attempt += 1

        jobs = []
        for chunk_index, chunk in enumerate(batched(items, chunk_size)):
            jobs.append(
                partial(delete_chunk, chunk, chunk_index)
            )
        await run_in_parallel(jobs, max_parallel=max_parallel_requests)

    async def _request_web_api(
            self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None
    ) -> Any:
        auth_retry_attempt = 0
        max_auth_retry_attempts = 1
        rate_limit_retry_attempt = 0
        max_rate_limit_retry_attempts = 3
        while True:
            try:
                return await self._web_api.request(
                    method=method,
                    endpoint=endpoint,
                    access_token=self._access_token,
                    params=params,
                    json=json
                )

            except SpotifyAuthError:
                if auth_retry_attempt < max_auth_retry_attempts:
                    logger.info("Token expired, refresh and retry (%i attempts left)",
                                max_auth_retry_attempts - auth_retry_attempt)
                    auth_retry_attempt += 1
                    await self._refresh_user_token()
                    continue
                else:
                    logger.warning("Auth error after token refresh, no retries left")
                    raise

            except SpotifyRateLimitError as e:
                if rate_limit_retry_attempt < max_rate_limit_retry_attempts:
                    if e.retry_after is not None:
                        retry_after = float(e.retry_after)
                    else:
                        retry_after = 1.0 * pow(2, rate_limit_retry_attempt)
                    retry_after += random.uniform(0, 1)  # jitter
                    logger.info("Hit rate limit, wait for %.2f and retry (%i attempts left)",
                                retry_after, max_rate_limit_retry_attempts - rate_limit_retry_attempt)
                    rate_limit_retry_attempt += 1
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.warning("Hit rate limit, no retries left")
                    raise

    async def _refresh_user_token(self):
        cur_token = self._access_token
        async with self._token_refresh_lock:
            if cur_token != self._access_token:
                logger.debug("Token has been refreshed in a different concurrent call")
                return

            logger.debug("Refreshing user token")
            auth_response_json = await self._auth_api.refresh_user_token(self._refresh_token)
            self._access_token = auth_response_json["access_token"]
            self._refresh_token = auth_response_json.get("refresh_token", self._refresh_token)
            await self._on_token_refreshed(self._access_token, self._refresh_token)
