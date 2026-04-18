from __future__ import annotations

from datetime import datetime, timezone

import httpx

from trending_hunter.fetchers import daily_velocity
from trending_hunter.models import Project, Source

_PH_API = "https://api.producthunt.com/v2/api/graphql"

_QUERY = """
query($first: Int) {
  posts(order: VOTES, first: $first) {
    edges {
      node {
        name
        tagline
        url
        votesCount
        createdAt
        commentsCount
      }
    }
  }
}
"""


def _ph_graphql(
    query: str,
    variables: dict,
    token: str,
    proxy: str | None = None,
) -> dict:
    client_kwargs: dict[str, object] = {
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        "timeout": 15,
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    with httpx.Client(**client_kwargs) as client:
        resp = client.post(_PH_API, json={"query": query, "variables": variables})
        resp.raise_for_status()
    return resp.json()


def _parse_ph_post(post: dict) -> Project | None:
    name = post.get("name")
    if not name:
        return None

    tagline = post.get("tagline", "")
    url = post.get("url", "")
    votes = post.get("votesCount", 0)
    created_at = post.get("createdAt", "")

    if created_at:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        velocity = daily_velocity(votes, created)
    else:
        velocity = float(votes)

    return Project(
        name=name,
        source=Source.PRODUCT_HUNT,
        url=url,
        stars=votes,
        star_velocity=round(velocity, 2),
        repo_age_days=0,
        description=tagline,
    )


def fetch_producthunt(
    token: str = "",
    top_n: int = 20,
    proxy: str | None = None,
) -> list[Project]:
    data = _ph_graphql(_QUERY, {"first": top_n}, token=token, proxy=proxy)
    edges = data.get("data", {}).get("posts", {}).get("edges", [])[:top_n]

    projects: list[Project] = []
    for edge in edges:
        project = _parse_ph_post(edge.get("node", {}))
        if project is not None:
            projects.append(project)
    return projects
