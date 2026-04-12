import httpx
import datetime
from .auth import load_token, get_username

URL = "https://graphql.anilist.co"

TRENDING_ANIME_QUERY = """
query {
  Page(perPage: 50) {
    media(type: ANIME, sort: TRENDING_DESC) {
      id
      title { romaji english }
            siteUrl
      coverImage { large medium }
      episodes
      description(asHtml: true)
      status
      averageScore
      genres
      recommendations(perPage: 5) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            english
                            romaji
                        }
                        averageScore
                    }
                }
            }
    }
  }
}
"""

SEASONAL_ANIME_QUERY = """
query ($season: MediaSeason, $year: Int) {
        Page(perPage: 50) {
            media(season: $season, seasonYear: $year, type: ANIME, sort: POPULARITY_DESC) {
                id
                title {
                    english
                    romaji
                }
                siteUrl
                episodes
                description(asHtml: true)
                status
                averageScore
                genres
                coverImage {
                    medium
                    large
                }
                recommendations(perPage: 5) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            english
                            romaji
                        }
                        averageScore
                    }
                }
            }
            }
        }
    }
"""

POPULAR_ANIME_QUERY = """
query {
        Page(perPage: 50) {
            media(type: ANIME, sort: POPULARITY_DESC) {
                id
                title {
                    english
                    romaji
                }
                siteUrl
                episodes
                description(asHtml: true)
                status
                averageScore
                popularity
                genres
                coverImage {
                    medium
                    large
                }
                recommendations(perPage: 5) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            english
                            romaji
                        }
                        averageScore
                    }
                }
            }
            }
        }
    }
"""

TOP_RATED_ANIME_QUERY = """
query {
        Page(perPage: 50) {
            media(type: ANIME, sort: SCORE_DESC) {
                id
                title {
                    english
                    romaji
                }
                siteUrl
                episodes
                description(asHtml: true)
                status
                averageScore
                popularity
                genres
                coverImage {
                    medium
                    large
                }
                recommendations(perPage: 5) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            english
                            romaji
                        }
                        averageScore
                    }
                }
            }
            }
        }
    }
"""

ANIME_DETAILS_QUERY = """
query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            title {
                english
                romaji
                native
            }
            siteUrl
            description(asHtml: true)
            episodes
            status
            genres
            averageScore
            startDate {
                year
                month
                day
            }
            endDate {
                year
                month
                day
            }
            coverImage {
                large
                medium
                color
            }
            recommendations(perPage: 5) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            english
                            romaji
                        }
                        averageScore
                    }
                }
            }
            nextAiringEpisode {
                episode
                timeUntilAiring
            }
        }
    }
"""

SEARCH_ANIME_QUERY = """
query SearchAnime($search: String!) {
  Page(perPage: 10) {
    media(type: ANIME, search: $search, sort: POPULARITY_DESC) {
      id
      title {
        romaji
        english
      }
            siteUrl
      episodes
      description(asHtml: true)
      status
      averageScore
      popularity
      genres
      coverImage {
          medium
          large
      }
      recommendations(perPage: 5) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            english
                            romaji
                        }
                        averageScore
                    }
                }
            }
    }
  }
}
"""

ANIME_LIST_QUERY = """
    query ($username: String!, $status: MediaListStatus) {
        MediaListCollection(userName: $username, type: ANIME, status: $status) {
            lists {
                name
                entries {
                    media {
                        id
                        title {
                            english
                            romaji
                        }
                        siteUrl
                        episodes
                        description(asHtml: true)
                        status
                        averageScore
                        popularity
                        genres
                        coverImage {
                            medium
                            large
                        }
                        recommendations(perPage: 5) {
                            nodes {
                                mediaRecommendation {
                                    id
                                    title {
                                        english
                                        romaji
                                    }
                                    averageScore
                                }
                            }
                        }
                    }
                }
            }
        }
    }
"""

USER_PROFILE_QUERY = """
query ($name: String) {
    User(name: $name) {
        name
        siteUrl
        about
        avatar {
            large
            medium
        }
    }
}
"""

USER_STATS_QUERY = """
query ($name: String) {
    User(name: $name) {
        name
        siteUrl
        avatar {
            large
            medium
        }
        statistics {
            anime {
                count
                episodesWatched
                minutesWatched
                meanScore
            }
            manga {
                count
                chaptersRead
                volumesRead
                meanScore
            }
        }
    }
}
"""

UPDATE_ANIME_STATUS_MUTATION = """
mutation ($mediaId: Int, $status: MediaListStatus) {
    SaveMediaListEntry(mediaId: $mediaId, status: $status) {
        id
        status
    }
}
"""

DELETE_ANIME_FROM_LIBRARY_MUTATION = """
mutation ($id: Int) {
    DeleteMediaListEntry(id: $id) {
        deleted
    }
}
"""

ANIME_LIBRARY_STATUS_QUERY = """
query ($username: String!, $mediaId: Int) {
    MediaList(userName: $username, mediaId: $mediaId, type: ANIME) {
        id
        status
        progress
        score(format: POINT_3)
    }
}
"""

LIBRARY_STATUS_LABELS = {
    "CURRENT": "Watching",
    "PLANNING": "Planning",
    "COMPLETED": "Completed",
    "DROPPED": "Dropped",
    "PAUSED": "Paused",
    "REPEATING": "Repeating",
}

LIST_NAME_BY_STATUS = {
    "CURRENT": "watching",
    "PLANNING": "planning",
    "COMPLETED": "completed",
    "DROPPED": "dropped",
    "PAUSED": "paused",
    "REPEATING": "repeating",
}

STATUS_LABEL_TO_ENUM = {
    "Watching": "CURRENT",
    "Planning": "PLANNING",
    "Completed": "COMPLETED",
    "Dropped": "DROPPED",
    "Paused": "PAUSED",
    "Repeating": "REPEATING",
}

UPDATE_EPISODE_MUTATION = """
mutation ($mediaId: Int, $progress: Int) {
    SaveMediaListEntry(mediaId: $mediaId, progress: $progress) {
        id
        progress
    }
}
"""

UPDATE_RATING_MUTATION = """
mutation ($mediaId: Int, $score: Float) {
    SaveMediaListEntry(mediaId: $mediaId, score: $score) {
        id
        score(format: POINT_3)
    }
}
"""

VALID_MEDIA_LIST_STATUSES = set(STATUS_LABEL_TO_ENUM.values())

def get_current_season():
    month = datetime.datetime.now().month
    if month in (12, 1, 2):
        return "WINTER"
    elif month in (3, 4, 5):
        return "SPRING"
    elif month in (6, 7, 8):
        return "SUMMER"
    else:
        return "FALL"

async def get_trending_anime() -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": TRENDING_ANIME_QUERY},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["Page"]["media"]

async def get_seasonal_anime():
    season = get_current_season()
    year = datetime.datetime.now().year 

    variables = {"season": season, "year": year}
    async with httpx.AsyncClient() as client:
      response = await client.post(
          URL,
          json={"query": SEASONAL_ANIME_QUERY, "variables": variables},
          headers={"Content-Type": "application/json"},
      )
      response.raise_for_status()
      data = response.json()
      return data["data"]["Page"]["media"]
  
async def get_popular_anime():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": POPULAR_ANIME_QUERY},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["Page"]["media"]

async def get_top_rated_anime():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": TOP_RATED_ANIME_QUERY},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["Page"]["media"]

async def get_anime_details(anime_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": ANIME_DETAILS_QUERY, "variables": {"id": anime_id}},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["Media"]

        
async def search_anime(search: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": SEARCH_ANIME_QUERY, "variables": {"search": search}},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["Page"]["media"]


async def get_user_profile() -> dict:
    token = load_token()
    username = get_username()
    if not token or not username:
        raise ValueError("User is not authenticated")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": USER_PROFILE_QUERY, "variables": {"name": username}},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        data = response.json()
        user = (data.get("data") or {}).get("User")
        if not user:
            raise ValueError("Could not load user profile")
        return user


async def get_user_stats() -> dict:
    token = load_token()
    username = get_username()
    if not token or not username:
        raise ValueError("User is not authenticated")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": USER_STATS_QUERY, "variables": {"name": username}},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        data = response.json()
        user = (data.get("data") or {}).get("User")
        if not user:
            raise ValueError("Could not load user stats")
        return user
    
async def get_anime_list(username: str, status: str) -> list[dict]:
    query = ANIME_LIST_QUERY
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": query, "variables": {"username": username, "status": status}},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        lists = data["data"]["MediaListCollection"]["lists"]
        media_entries: list[dict] = []
        for media_list in lists:
            entries = media_list.get("entries") or []
            for entry in entries:
                media = entry.get("media")
                if media:
                    media_entries.append(media)
        return media_entries


async def get_library_status(anime_id: int) -> str | None:
    token = load_token()
    username = get_username()
    if not token or not username:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={
                "query": ANIME_LIBRARY_STATUS_QUERY,
                "variables": {"username": username, "mediaId": anime_id},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        status = (((data.get("data") or {}).get("MediaList") or {}).get("status"))
        if not status:
            return None

        normalized_status = status.strip().upper()
        return LIBRARY_STATUS_LABELS.get(normalized_status, normalized_status.replace("_", " ").title())


async def get_library_progress(anime_id: int) -> int | None:
    token = load_token()
    username = get_username()
    if not token or not username:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={
                "query": ANIME_LIBRARY_STATUS_QUERY,
                "variables": {"username": username, "mediaId": anime_id},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        progress = (((data.get("data") or {}).get("MediaList") or {}).get("progress"))
        if not isinstance(progress, int):
            return None
        return max(progress, 0)


async def get_library_score(anime_id: int) -> int | None:
    token = load_token()
    username = get_username()
    if not token or not username:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={
                "query": ANIME_LIBRARY_STATUS_QUERY,
                "variables": {"username": username, "mediaId": anime_id},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        score = (((data.get("data") or {}).get("MediaList") or {}).get("score"))
        if not isinstance(score, (int, float)):
            return None
        return max(1, min(int(score), 3))


async def remove_anime_from_library(anime_id: int) -> bool:
    token = load_token()
    username = get_username()
    if not token or not username:
        return False

    async with httpx.AsyncClient() as client:
        status_response = await client.post(
            URL,
            json={
                "query": ANIME_LIBRARY_STATUS_QUERY,
                "variables": {"username": username, "mediaId": anime_id},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if status_response.status_code == 404:
            return False
        status_response.raise_for_status()
        status_data = status_response.json()
        media_list = ((status_data.get("data") or {}).get("MediaList") or {})
        entry_id = media_list.get("id")

        if not isinstance(entry_id, int):
            return True

        delete_response = await client.post(
            URL,
            json={
                "query": DELETE_ANIME_FROM_LIBRARY_MUTATION,
                "variables": {"id": entry_id},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if delete_response.status_code == 404:
            return False
        delete_response.raise_for_status()
        delete_data = delete_response.json()
        deleted_payload = (delete_data.get("data") or {}).get("DeleteMediaListEntry")
        if isinstance(deleted_payload, bool):
            return deleted_payload
        if isinstance(deleted_payload, dict):
            return bool(deleted_payload.get("deleted"))
        return False

async def update_anime_status(anime_id: int, new_status: str) -> bool:
    token = load_token()
    if not token:
        return False

    normalized_status = new_status.strip()
    status_enum = (
        STATUS_LABEL_TO_ENUM.get(normalized_status)
        or STATUS_LABEL_TO_ENUM.get(normalized_status.title())
        or normalized_status.upper()
    )

    if status_enum not in VALID_MEDIA_LIST_STATUSES:
        raise ValueError(f"Invalid library status: {new_status}")

    variables = {"mediaId": anime_id, "status": status_enum}
    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": UPDATE_ANIME_STATUS_MUTATION, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        data = response.json()
        return "data" in data and "SaveMediaListEntry" in data["data"]


async def update_anime_progress(anime_id: int, progress: int) -> bool:
    token = load_token()
    if not token:
        return False

    safe_progress = max(int(progress), 0)
    variables = {"mediaId": anime_id, "progress": safe_progress}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": UPDATE_EPISODE_MUTATION, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        data = response.json()
        return "data" in data and "SaveMediaListEntry" in data["data"]


async def update_anime_rating(anime_id: int, score: int) -> bool:
    token = load_token()
    if not token:
        return False

    safe_score = max(1, min(int(score), 3))
    variables = {"mediaId": anime_id, "score": float(safe_score)}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            URL,
            json={"query": UPDATE_RATING_MUTATION, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        data = response.json()
        return "data" in data and "SaveMediaListEntry" in data["data"]
    
