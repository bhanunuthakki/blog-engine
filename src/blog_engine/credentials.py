"""Load WordPress REST credentials from a `KEY=value` secrets env file.

The real file looks like:

    WP_SITE_URL= https://bhanunuthakki.com
    WP_USERNAME=bhanu
    WP_APP_PASSWORD=abcd EFGH ijkl MNOP

Leading/trailing whitespace on values and the spaced app-password display
format are both real quirks of how the file gets edited by hand, not edge
cases to defend against defensively — normalize them here, once.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr

from blog_engine.models import WordPressCredentials

_REQUIRED_KEYS = ("WP_SITE_URL", "WP_USERNAME", "WP_APP_PASSWORD")


class CredentialsError(RuntimeError):
    """Raised when the secrets env file is missing or malformed.

    Never includes the app-password value — only key names and the file
    path (AGENTS.md safety rule 4: a credential must never reach an
    exception message).
    """


def load_wordpress_credentials(env_path: Path) -> WordPressCredentials:
    """Parse `env_path` and return validated `WordPressCredentials`."""
    if not env_path.is_file():
        raise CredentialsError(f"WordPress secrets file not found: {env_path}")

    values = _parse_env_file(env_path)

    for key in _REQUIRED_KEYS:
        if not values.get(key, "").strip():
            raise CredentialsError(
                f"Missing or empty '{key}' in WordPress secrets file: {env_path}"
            )

    site_url = _normalize_site_url(values["WP_SITE_URL"])
    username = values["WP_USERNAME"]
    app_password = values["WP_APP_PASSWORD"].replace(" ", "")

    return WordPressCredentials(
        site_url=site_url, username=username, app_password=SecretStr(app_password)
    )


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse `KEY=value` lines, stripping whitespace from every value.

    `#` starts a full-line comment; blank lines are skipped. Values may
    contain `=` (only the first `=` on a line splits key from value).
    """
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            continue
        values[key.strip()] = value.strip()
    return values


def _normalize_site_url(url: str) -> str:
    """Ensure a scheme is present and strip trailing slashes."""
    normalized = url.strip()
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized.rstrip("/")
