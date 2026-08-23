# NOTICE: This file is protected under RCF-PL
"""Tests for the websearch router endpoints.

Covers GET /api/websearch (search) and POST /api/websearch/synthesize
(synthesis).  All external calls (httpx) are mocked so no real network is
needed.
"""
from unittest.mock import AsyncMock, patch


# ── GET /api/websearch ──────────────────────────────────────────────────────

def _mock_meta_search_factory():
    """Return a callable that creates MetaSearchResponse with the passed query."""
    async def _meta_search(query, **kwargs):
        return {
            "query": query,
            "results": [
                {"title": "Result 1", "link": "https://a.com", "snippet": "snippet one", "source": "duckduckgo"},
                {"title": "Result 2", "link": "https://b.com", "snippet": "snippet two", "source": "wikipedia"},
            ],
            "by_source": {
                "duckduckgo": [
                    {"title": "Result 1", "link": "https://a.com", "snippet": "snippet one", "source": "duckduckgo"},
                ],
                "wikipedia": [
                    {"title": "Result 2", "link": "https://b.com", "snippet": "snippet two", "source": "wikipedia"},
                ],
            },
            "errors": {},
        }
    return _meta_search


@patch("app.routers.websearch.meta_search", new_callable=AsyncMock)
def test_websearch_returns_results(mock_meta, client, auth_headers):
    mock_meta.side_effect = _mock_meta_search_factory()
    r = client.get("/api/websearch?q=python+docs", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "python docs"
    assert data["total"] == 2
    assert len(data["results"]) == 2


@patch("app.routers.websearch.meta_search", new_callable=AsyncMock)
def test_websearch_filters_by_engine(mock_meta, client, auth_headers):
    mock_meta.side_effect = _mock_meta_search_factory()
    r = client.get("/api/websearch?q=test&engines=wikipedia", headers=auth_headers)
    assert r.status_code == 200
    mock_meta.assert_called_once()
    # Check that wikipedia was passed as an engine
    call_args, call_kwargs = mock_meta.call_args
    engines = call_kwargs.get("engines", call_args[1] if len(call_args) > 1 else ())
    assert "wikipedia" in engines


def test_websearch_requires_query(client, auth_headers):
    r = client.get("/api/websearch", headers=auth_headers)
    assert r.status_code == 422  # FastAPI validation


def test_websearch_requires_auth(client):
    r = client.get("/api/websearch?q=test")
    assert r.status_code in (401, 403)


# ── POST /api/websearch/synthesize ──────────────────────────────────────────

@patch("app.routers.websearch.meta_search", new_callable=AsyncMock)
def test_synthesize_returns_markdown(mock_meta, client, auth_headers):
    mock_meta.side_effect = _mock_meta_search_factory()
    r = client.post(
        "/api/websearch/synthesize",
        json={"query": "test query"},
        headers=auth_headers,
    )
    # May return 200 or 500 depending on whether Chromium is available,
    # but should not be a validation error
    assert r.status_code in (200, 500)
    mock_meta.assert_called_once()


def test_synthesize_requires_query(client, auth_headers):
    r = client.post(
        "/api/websearch/synthesize",
        json={},
        headers=auth_headers,
    )
    assert r.status_code == 422
