import asyncio
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import Any


@dataclass
class User:
    user_id: str
    access_token: str
    refresh_token: str


class UsersDb:
    def __init__(self, users_db_path: str):
        self._users_db_path = users_db_path

    async def create_schema(self):
        await asyncio.to_thread(
            self._execute,
            'CREATE TABLE IF NOT EXISTS users ('
            'id TEXT PRIMARY KEY, '
            'access_token TEXT, '
            'refresh_token TEXT)'
        )

    async def set_user(self, user: User):
        await asyncio.to_thread(
            self._execute,
            'INSERT OR REPLACE INTO users (id, access_token, refresh_token) VALUES (?, ?, ?)',
            (user.user_id, user.access_token, user.refresh_token)
        )

    async def get_user(self, user_id: str) -> User | None:
        res = await asyncio.to_thread(
            self._execute_and_fetch_one,
            'SELECT id, access_token, refresh_token FROM users WHERE id = ?',
            (user_id,)
        )
        if res is None:
            return None
        return User(*res)

    async def delete_user(self, user_id: str):
        await asyncio.to_thread(
            self._execute,
            'DELETE FROM users WHERE id = ?',
            (user_id,)
        )

    def _execute(self, sql: str, parameters: tuple[Any, ...] = ()):
        with closing(sqlite3.connect(self._users_db_path)) as connection:  # closes connection
            with connection:  # commits transaction
                connection.execute(sql, parameters)

    def _execute_and_fetch_one(self, sql: str, parameters: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
        with closing(sqlite3.connect(self._users_db_path)) as connection:  # closes connection
            # no transaction for SELECT
            cursor = connection.execute(sql, parameters)
            return cursor.fetchone()
