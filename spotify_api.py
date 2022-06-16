import base64
import urllib.parse

import requests


class SpotifyAuth:
    def __init__(self, config):
        self.api_url = "https://accounts.spotify.com/api"
        self.host = config["server"]["host"]

        client_id = config["spotify"]["client_id"]
        client_secret = config["spotify"]["client_secret"]
        basic_auth = "Basic " + base64.b64encode(bytes(f"{client_id}:{client_secret}", "utf-8")).decode("utf-8")
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": basic_auth
        }

    def token(self, code):
        return requests.post(
            self.api_url + "/token",
            headers=self.headers,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.host + "/auth_callback"
            }
        )


class SpotifyApi:
    def __init__(self, access_token):
        self.api_url = "https://api.spotify.com/v1"
        self.access_token = access_token

    def get(self, endpoint, params=None):
        if params is None:
            params = {}
        return requests.get(f"{self.api_url}{endpoint}?{urllib.parse.urlencode(params)}", headers={
            "Authorization": f"Bearer {self.access_token}"
        })
