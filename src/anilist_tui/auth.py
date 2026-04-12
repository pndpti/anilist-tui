import json
import os
from pathlib import Path

import httpx


CONFIG_DIR = Path.home() / ".config" / "anilist-tui"
TOKEN_FILE = CONFIG_DIR / "auth.json"
URL = "https://graphql.anilist.co"


def _load_auth_data() -> dict:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_auth_data(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(data))

def load_token() -> str | None:
    """load the saved access token"""
    data = _load_auth_data()
    return data.get("access_token")

def save_token(access_token: str) -> None:
    """Persist the access token to disk."""
    data = _load_auth_data()
    data["access_token"] = access_token
    _save_auth_data(data)


def load_client_id() -> str | None:
    """Load saved AniList client ID from disk."""
    data = _load_auth_data()
    client_id = data.get("client_id")
    if isinstance(client_id, str) and client_id.strip():
        return client_id.strip()
    return None


def save_client_id(client_id: str) -> None:
    """Persist AniList client ID to disk."""
    data = _load_auth_data()
    data["client_id"] = client_id.strip()
    _save_auth_data(data)


def get_client_id() -> str | None:
    """Resolve client ID from env, then saved value."""
    env_client_id = os.getenv("ANILIST_CLIENT_ID", "").strip()
    if env_client_id:
        return env_client_id

    saved_client_id = load_client_id()
    if saved_client_id:
        return saved_client_id

    return None

def clear_token() -> None:
    """Remove only auth session fields while keeping user preferences."""
    data = _load_auth_data()
    data.pop("access_token", None)
    data.pop("username", None)

    if data:
        _save_auth_data(data)
        return

    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()

def get_oauth_url(client_id: str | None = None) -> str:
    resolved_client_id = (client_id or "").strip() or get_client_id()
    if not resolved_client_id:
        raise ValueError("Client ID is required")
    return (
        f"https://anilist.co/api/v2/oauth/authorize"
        f"?client_id={resolved_client_id}&response_type=token"
    )


async def save_username(token: str) -> str | None:
    """Fetch the username using the access token and save it to disk."""
    query = """
    query {
        Viewer {
            name
        }
    }
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": query},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
        )
        if response.status_code == 200:
            data = response.json()
            username = data["data"]["Viewer"]["name"]
            auth_data = _load_auth_data()
            auth_data["username"] = username
            auth_data["access_token"] = token
            _save_auth_data(auth_data)
            return username
        else:
            return None

def get_username() -> str | None:
    """Retrieve the saved username."""
    data = _load_auth_data()
    return data.get("username")