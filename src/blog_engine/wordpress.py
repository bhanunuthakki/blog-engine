"""Typed WordPress REST client.

The app password never reaches a log line or exception message (AGENTS.md
safety rule 4): it lives in `WordPressCredentials.app_password` as a
`SecretStr` and is unwrapped via `.get_secret_value()` only inside
`_auth_header`, right where the header is built. It never goes in a URL —
only in the `Authorization` header — and any HTTP failure is re-raised as a
fresh `WordPressError` with `from None`, so a chained traceback can never
carry a credentialed request object forward.
"""

from __future__ import annotations

import base64
from typing import cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

from blog_engine.markdown_blocks import markdown_to_blocks
from blog_engine.models import PostDraft, PostStatus, WordPressCredentials

_NEVER_AUTOMATED_STATUSES = frozenset({PostStatus.PUBLISH, PostStatus.FUTURE})
"""Statuses `create_post` refuses outright — going live is a human action
taken in WP Admin, never something automated sync does. `PENDING`/`PRIVATE`
are allowed: neither is publicly visible."""


class WPPost(BaseModel):
    """The fields of a WordPress REST post response this project uses."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(gt=0)
    slug: str = Field(min_length=1)
    status: PostStatus
    link: str = Field(min_length=1)
    title: str = ""


class WordPressError(RuntimeError):
    """Raised for any WordPress REST failure. Message includes the status
    code and, when the response body carries a WP REST `code`/`message`
    pair, that too — never a URL or the app password."""


class WordPressClient:
    """A thin, typed wrapper over the WordPress REST API's `/wp/v2` surface."""

    def __init__(self, credentials: WordPressCredentials, *, timeout: float = 30.0) -> None:
        self._credentials = credentials
        self._base_url = f"{credentials.site_url}/wp-json/wp/v2"
        self._timeout = timeout

    def get_post_by_slug(self, slug: str) -> WPPost | None:
        response = self._request("GET", "/posts", params={"slug": slug, "status": "any"})
        results = _parse_json_list(response)
        if not results:
            return None
        first = results[0]
        if not isinstance(first, dict):
            raise WordPressError(f"WordPress returned an unexpected response for slug '{slug}'.")
        return _parse_post(cast(dict[str, object], first))

    def create_post(self, draft: PostDraft, status: PostStatus) -> WPPost:
        if status in _NEVER_AUTOMATED_STATUSES:
            raise WordPressError(
                f"Refusing to create post '{draft.slug}' with status "
                f"'{status.value}': publishing is a human action taken in "
                f"WP Admin, never something this automation does."
            )
        category_ids = [self.get_or_create_category(slug, slug) for slug in draft.category_slugs]
        tag_ids = [self.get_or_create_tag(slug, slug) for slug in draft.tag_slugs]
        body: dict[str, object] = {
            "title": draft.title,
            "slug": draft.slug,
            "status": status.value,
            "content": markdown_to_blocks(draft.markdown),
            "excerpt": draft.excerpt,
            "categories": category_ids,
            "tags": tag_ids,
        }
        response = self._request("POST", "/posts", json_body=body)
        return _parse_post(_parse_json_dict(response, f"creating post '{draft.slug}'"))

    def update_post(self, post_id: int, draft: PostDraft) -> WPPost:
        current = self._get_post(post_id)
        if current.status != PostStatus.DRAFT:
            raise WordPressError(
                f"Refusing to update post #{post_id}: status is "
                f"'{current.status.value}', not draft. A published post is "
                f"never overwritten by an automated sync."
            )
        category_ids = [self.get_or_create_category(slug, slug) for slug in draft.category_slugs]
        tag_ids = [self.get_or_create_tag(slug, slug) for slug in draft.tag_slugs]
        body: dict[str, object] = {
            "title": draft.title,
            "slug": draft.slug,
            "content": markdown_to_blocks(draft.markdown),
            "excerpt": draft.excerpt,
            "categories": category_ids,
            "tags": tag_ids,
        }
        response = self._request("POST", f"/posts/{post_id}", json_body=body)
        return _parse_post(_parse_json_dict(response, f"updating post #{post_id}"))

    def get_or_create_category(self, slug: str, name: str) -> int:
        return self._get_or_create_term("categories", slug, name)

    def get_or_create_tag(self, slug: str, name: str) -> int:
        return self._get_or_create_term("tags", slug, name)

    def verify_auth(self) -> str:
        """Confirm the credentials work by calling `/users/me`. Returns the
        authenticated display name; used by `blog-engine check-auth`."""
        response = self._request("GET", "/users/me")
        payload = _parse_json_dict(response, "checking authentication")
        name = payload.get("name")
        return name if isinstance(name, str) else self._credentials.username

    def _get_post(self, post_id: int) -> WPPost:
        response = self._request("GET", f"/posts/{post_id}", params={"context": "edit"})
        return _parse_post(_parse_json_dict(response, f"fetching post #{post_id}"))

    def _get_or_create_term(self, endpoint: str, slug: str, name: str) -> int:
        response = self._request("GET", f"/{endpoint}", params={"slug": slug})
        results = _parse_json_list(response)
        if results:
            first = results[0]
            if isinstance(first, dict):
                term_id = cast(dict[str, object], first).get("id")
                if isinstance(term_id, int):
                    return term_id

        create_response = self._request(
            "POST", f"/{endpoint}", json_body={"slug": slug, "name": name}
        )
        payload = _parse_json_dict(create_response, f"creating {endpoint[:-1]} '{slug}'")
        term_id = payload.get("id")
        if not isinstance(term_id, int):
            raise WordPressError(
                f"WordPress did not return a numeric id creating {endpoint[:-1]} '{slug}'."
            )
        return term_id

    def _auth_header(self) -> dict[str, str]:
        token = base64.b64encode(
            f"{self._credentials.username}:{self._credentials.app_password.get_secret_value()}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, object] | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=self._auth_header(),
                timeout=self._timeout,
                params=params,
                json=json_body,
            )
        except httpx.HTTPError:
            # httpx's own exception can stringify the request (URL + method);
            # the URL never carries the password (it's header-only), but
            # re-raise fresh anyway so nothing credentialed can ride along a
            # chained traceback out of this function.
            raise WordPressError(f"Request to WordPress failed: {method} {path}") from None
        if response.is_error:
            raise WordPressError(_format_error(response, method, path))
        return response


def _parse_json_dict(response: httpx.Response, action: str) -> dict[str, object]:
    """The JSON-object boundary: `httpx.Response.json()` is `Any`-typed, and
    `isinstance(x, dict)` on an `Any` can't recover the value type either —
    the single `cast` right after the check is what AGENTS.md's boundary
    exception is for, contained to this one helper for every JSON-dict read
    in the client."""
    payload = response.json()
    if not isinstance(payload, dict):
        raise WordPressError(f"WordPress returned an unexpected response {action}.")
    return cast(dict[str, object], payload)


def _parse_json_list(response: httpx.Response) -> list[object]:
    """The JSON-array boundary — see `_parse_json_dict`. A response that
    isn't a JSON array is treated as "no results" rather than an error: the
    only callers are list endpoints probing for an existing slug/term."""
    payload = response.json()
    if not isinstance(payload, list):
        return []
    return cast(list[object], payload)


def _parse_post(payload: dict[str, object]) -> WPPost:
    title = ""
    title_field = payload.get("title")
    if isinstance(title_field, dict):
        rendered = cast(dict[str, object], title_field).get("rendered")
        if isinstance(rendered, str):
            title = rendered
    return WPPost.model_validate(
        {
            "id": payload.get("id"),
            "slug": payload.get("slug"),
            "status": payload.get("status"),
            "link": payload.get("link"),
            "title": title,
        }
    )


def _format_error(response: httpx.Response, method: str, path: str) -> str:
    detail = ""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        payload = cast(dict[str, object], payload)
        code = payload.get("code")
        message = payload.get("message")
        if code is not None or message is not None:
            detail = f" ({code}: {message})"
    return f"WordPress {method} {path} failed with status {response.status_code}{detail}"
