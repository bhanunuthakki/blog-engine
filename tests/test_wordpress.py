"""wordpress: credential never leaks into an exception, and update_post
refuses to write over a non-draft post — defense in depth behind
sync.decide's own REPORT_PUBLISHED_DRIFT routing."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from blog_engine.models import PostDraft, PostStatus, WordPressCredentials
from blog_engine.wordpress import WordPressClient, WordPressError

_SECRET = "dummy-app-password"

FakeRequest = Callable[..., httpx.Response]


def _credentials() -> WordPressCredentials:
    return WordPressCredentials(
        site_url="https://bhanunuthakki.com", username="bhanu", app_password=SecretStr(_SECRET)
    )


def _draft() -> PostDraft:
    return PostDraft(title="Range", slug="range", markdown="Body text.")


def _ok_json(payload: object) -> FakeRequest:
    """A fake `httpx.request` that always returns `200` with `payload` as
    the JSON body, ignoring the request it was called with."""

    def handler(method: str, url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


def _install_fake_request(
    monkeypatch: pytest.MonkeyPatch, handler: FakeRequest
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        calls.append({"method": method, "url": url, **kwargs})
        return handler(method, url, **kwargs)

    monkeypatch.setattr("blog_engine.wordpress.httpx.request", fake_request)
    return calls


def test_auth_header_carries_basic_token_built_from_secret_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_request(monkeypatch, _ok_json({"name": "bhanu"}))
    client = WordPressClient(_credentials())
    client.verify_auth()
    header = calls[0]["headers"]["Authorization"]
    assert header.startswith("Basic ")


def test_password_never_appears_in_url(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_request(monkeypatch, _ok_json({"name": "bhanu"}))
    client = WordPressClient(_credentials())
    client.verify_auth()
    assert _SECRET not in calls[0]["url"]


def test_request_failure_error_message_never_contains_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_http_error(method: str, url: str, **kw: Any) -> httpx.Response:
        raise httpx.ConnectError(f"Connection failed: {url}")

    _install_fake_request(monkeypatch, raise_http_error)
    client = WordPressClient(_credentials())
    with pytest.raises(WordPressError) as exc_info:
        client.verify_auth()
    assert _SECRET not in str(exc_info.value)


def _forbidden_response(method: str, url: str, **kw: Any) -> httpx.Response:
    return httpx.Response(
        403, json={"code": "rest_forbidden", "message": "Sorry, you are not allowed."}
    )


def test_error_response_message_never_contains_password(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_request(monkeypatch, _forbidden_response)
    client = WordPressClient(_credentials())
    with pytest.raises(WordPressError) as exc_info:
        client.verify_auth()
    message = str(exc_info.value)
    assert _SECRET not in message
    assert "403" in message
    assert "rest_forbidden" in message


def test_update_post_refuses_when_existing_status_is_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        assert method == "GET"  # never reaches a POST
        return httpx.Response(
            200,
            json={
                "id": 7,
                "slug": "range",
                "status": "publish",
                "link": "https://bhanunuthakki.com/range/",
                "title": {"rendered": "Range"},
            },
        )

    calls = _install_fake_request(monkeypatch, handler)
    client = WordPressClient(_credentials())
    with pytest.raises(WordPressError, match="publish"):
        client.update_post(7, _draft())
    assert all(call["method"] == "GET" for call in calls)


def test_create_post_refuses_publish_status_with_no_request_issued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        raise AssertionError("no HTTP request should be made")

    calls = _install_fake_request(monkeypatch, handler)
    client = WordPressClient(_credentials())
    with pytest.raises(WordPressError, match="publish"):
        client.create_post(_draft(), PostStatus.PUBLISH)
    assert calls == []


def test_create_post_refuses_future_status_with_no_request_issued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        raise AssertionError("no HTTP request should be made")

    calls = _install_fake_request(monkeypatch, handler)
    client = WordPressClient(_credentials())
    with pytest.raises(WordPressError, match="future"):
        client.create_post(_draft(), PostStatus.FUTURE)
    assert calls == []


@pytest.mark.parametrize("status", [PostStatus.DRAFT, PostStatus.PENDING, PostStatus.PRIVATE])
def test_create_post_allows_non_public_statuses(
    monkeypatch: pytest.MonkeyPatch, status: PostStatus
) -> None:
    _install_fake_request(
        monkeypatch,
        _ok_json(
            {
                "id": 1,
                "slug": "range",
                "status": status.value,
                "link": "https://bhanunuthakki.com/?p=1",
                "title": {"rendered": "Range"},
            }
        ),
    )
    client = WordPressClient(_credentials())
    post = client.create_post(_draft(), status)
    assert post.status == status


def test_update_post_succeeds_when_existing_status_is_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        if method == "GET" and url.endswith("/posts/7"):
            return httpx.Response(
                200,
                json={
                    "id": 7,
                    "slug": "range",
                    "status": "draft",
                    "link": "https://bhanunuthakki.com/?p=7",
                    "title": {"rendered": "Range"},
                },
            )
        if url.endswith("/categories"):
            return httpx.Response(200, json=[])
        if url.endswith("/tags"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json={
                "id": 7,
                "slug": "range",
                "status": "draft",
                "link": "https://bhanunuthakki.com/?p=7",
                "title": {"rendered": "Range"},
            },
        )

    _install_fake_request(monkeypatch, handler)
    client = WordPressClient(_credentials())
    post = client.update_post(7, _draft())
    assert post.status == PostStatus.DRAFT


def test_get_or_create_category_reuses_existing_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_request(monkeypatch, _ok_json([{"id": 5, "slug": "books"}]))
    client = WordPressClient(_credentials())
    assert client.get_or_create_category("books", "Books") == 5


def test_get_or_create_category_creates_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        if method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json={"id": 9, "slug": "books"})

    _install_fake_request(monkeypatch, handler)
    client = WordPressClient(_credentials())
    assert client.get_or_create_category("books", "Books") == 9


def test_get_post_by_slug_returns_none_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_request(monkeypatch, _ok_json([]))
    client = WordPressClient(_credentials())
    assert client.get_post_by_slug("missing") is None


def test_get_post_by_slug_parses_wp_post(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_request(
        monkeypatch,
        _ok_json(
            [
                {
                    "id": 3,
                    "slug": "range",
                    "status": "draft",
                    "link": "https://bhanunuthakki.com/?p=3",
                    "title": {"rendered": "Range"},
                }
            ]
        ),
    )
    client = WordPressClient(_credentials())
    post = client.get_post_by_slug("range")
    assert post is not None
    assert post.id == 3
    assert post.title == "Range"


def test_verify_auth_returns_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_request(monkeypatch, _ok_json({"name": "Bhanu Nuthakki"}))
    client = WordPressClient(_credentials())
    assert client.verify_auth() == "Bhanu Nuthakki"


# ---------------------------------------------------------------------------
# UTF-8 survives to the actual request bytes (curly quotes, em dashes).
# ---------------------------------------------------------------------------

_UNICODE_TITLE = "Franklin\N{RIGHT SINGLE QUOTATION MARK}s Life — An American Story"


def test_httpx_json_body_round_trips_unicode_as_correct_utf8() -> None:
    """The real risk surface: httpx's `json=` serialization must produce
    bytes that decode back to the exact original string, not `?`-substituted
    or mis-encoded bytes. Builds a real `httpx.Request` (no client/monkeypatch
    involved) and inspects its actual wire body."""
    request = httpx.Request(
        "POST", "https://bhanunuthakki.com/wp-json/wp/v2/posts", json={"title": _UNICODE_TITLE}
    )
    body_bytes = request.read()
    assert json.loads(body_bytes.decode("utf-8"))["title"] == _UNICODE_TITLE


def test_create_post_request_body_carries_exact_unicode_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End to end through the client: the title reaching `httpx.request`'s
    `json` kwarg must be the exact original string, byte-for-byte round
    trippable, not mangled on the way through our own code."""
    calls = _install_fake_request(
        monkeypatch,
        _ok_json(
            {
                "id": 1,
                "slug": "range",
                "status": "draft",
                "link": "https://bhanunuthakki.com/?p=1",
                "title": {"rendered": _UNICODE_TITLE},
            }
        ),
    )
    client = WordPressClient(_credentials())
    draft = PostDraft(title=_UNICODE_TITLE, slug="range", markdown="Body text.")
    client.create_post(draft, PostStatus.DRAFT)
    post_calls = [c for c in calls if c["url"].endswith("/posts")]
    body = post_calls[0]["json"]
    assert body["title"] == _UNICODE_TITLE
    # Confirm it also survives actual UTF-8 wire encoding, not just the
    # in-memory python string.
    wire_request = httpx.Request("POST", "https://example.com", json=body)
    assert json.loads(wire_request.read().decode("utf-8"))["title"] == _UNICODE_TITLE
