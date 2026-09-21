from dataclasses import dataclass

import sqlite3


@dataclass
class User:
    user_id: str
    access_token: str
    refresh_token: str


class UsersDb:
    def __init__(self):
        self.db_filename = "users.sqlite"
        self._execute('CREATE TABLE IF NOT EXISTS users ('
                      'id TEXT PRIMARY KEY, '
                      'access_token TEXT, '
                      'refresh_token TEXT)')

    def _execute(self, *args, **kwargs):
        with sqlite3.Connection(self.db_filename) as connection:
            cursor = connection.cursor()
            cursor.execute(*args, **kwargs)
            connection.commit()

    def _execute_and_fetch_one(self, *args, **kwargs):
        with sqlite3.Connection(self.db_filename) as connection:
            cursor = connection.cursor()
            cursor.execute(*args, **kwargs)
            return cursor.fetchone()

    def set_user(self, user):
        self._execute(
            'INSERT OR REPLACE INTO users (id, access_token, refresh_token) VALUES (?, ?, ?)',
            (user.user_id, user.access_token, user.refresh_token)
        )

    def get_user(self, user_id):
        res = self._execute_and_fetch_one('SELECT id, access_token, refresh_token FROM users WHERE id = ?', (user_id,))
        if res is None:
            return None
        return User(res[0], res[1], res[2])

    def delete_user(self, user_id):
        self._execute('DELETE FROM users WHERE id = ?', (user_id,))
