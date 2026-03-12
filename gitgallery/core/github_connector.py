"""
GitHub API and OAuth integration.
"""

import webbrowser
from typing import Any, Callable, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from authlib.integrations.requests_client import OAuth2Session

from gitgallery.app.config import (
    CONFIG_DIR,
    GITHUB_OAUTH_CLIENT_ID,
    GITHUB_OAUTH_CLIENT_SECRET,
    GITHUB_OAUTH_SCOPES,
)
from gitgallery.utils.logger import get_logger

logger = get_logger()

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"

REDIRECT_URI = "http://127.0.0.1:8765/callback"
LOCAL_CALLBACK_PORT = 8765

TOKEN_FILE = CONFIG_DIR / "github_token.json"


class GitHubAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class GitHubConnector:
    def __init__(self) -> None:
        self._access_token: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return bool(self._access_token)

    def set_access_token(self, token: str) -> None:
        self._access_token = token
        logger.info("GitHub access token set")

    def clear_token(self) -> None:
        self._access_token = None
        logger.info("GitHub token cleared")

    def get_authorization_url(self) -> str:
        params = {
            "client_id": GITHUB_OAUTH_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(GITHUB_OAUTH_SCOPES),
            "state": "gitgallery_v1",
        }
        return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> str:
        """
        Exchange authorization code for access token.
        """

        session = OAuth2Session(
            GITHUB_OAUTH_CLIENT_ID,
            redirect_uri=REDIRECT_URI,
        )

        token = session.fetch_token(
            GITHUB_TOKEN_URL,
            code=code,
            client_secret=GITHUB_OAUTH_CLIENT_SECRET,
            method="POST",
            headers={"Accept": "application/json"},
        )

        access = token.get("access_token")

        if not access:
            raise GitHubAPIError("OAuth failed: no access_token returned")

        self._access_token = access

        logger.info("GitHub OAuth successful")

        return access

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:

        if not self._access_token:
            raise GitHubAPIError("Not authenticated")

        url = f"{GITHUB_API_BASE}{path}"

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        resp = requests.request(
            method,
            url,
            headers=headers,
            json=json_data,
            params=params,
            timeout=30,
        )

        if resp.status_code >= 400:
            msg = resp.text or resp.reason
            logger.error("GitHub API error %s: %s", resp.status_code, msg)
            raise GitHubAPIError(msg, status_code=resp.status_code)

        if resp.status_code == 204 or not resp.content:
            return None

        return resp.json()

    def get_user(self) -> dict:
        return self._request("GET", "/user")

    def list_repositories(self) -> List[dict]:

        repos: List[dict] = []
        page = 1

        while True:
            data = self._request(
                "GET",
                "/user/repos",
                params={"per_page": 100, "page": page, "sort": "updated"},
            )

            if not data:
                break

            repos.extend(data)

            if len(data) < 100:
                break

            page += 1

        return repos

    def create_repository(
        self,
        name: str,
        private: bool = True,
        description: str = "GitGallery photo storage",
    ) -> dict:

        return self._request(
            "POST",
            "/user/repos",
            json_data={
                "name": name,
                "private": private,
                "description": description,
                "auto_init": True,
            },
        )


def start_local_callback_server(
    on_code: Callable[[str], None],
    port: int = LOCAL_CALLBACK_PORT,
) -> None:

    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:

            parsed = urlparse(self.path)

            if parsed.path == "/callback":

                qs = parse_qs(parsed.query)

                code_list = qs.get("code")

                if code_list:
                    on_code(code_list[0])

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()

                self.wfile.write(
                    b"<html><body><p>Authorization successful. You can close this tab and return to GitGallery.</p></body></html>"
                )

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("OAuth callback: %s", args)

    server = HTTPServer(("127.0.0.1", port), Handler)

    server.handle_request()