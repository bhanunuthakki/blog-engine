"""credentials: leading-space values, spaced app password, missing keys,
and that the password never leaks through repr/str/errors."""

from pathlib import Path

import pytest

from blog_engine.credentials import CredentialsError, load_wordpress_credentials

_SECRET_PASSWORD = "dummyapppassword"


def _write_env(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "wordpress.env"
    path.write_text(contents, encoding="utf-8")
    return path


def test_leading_space_on_value_is_stripped(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL= https://bhanunuthakki.com\n"
        "WP_USERNAME=bhanu\n"
        "WP_APP_PASSWORD=dummy app password\n",
    )
    creds = load_wordpress_credentials(path)
    assert creds.site_url == "https://bhanunuthakki.com"


def test_spaced_app_password_has_all_spaces_removed(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL=https://bhanunuthakki.com\n"
        "WP_USERNAME=bhanu\n"
        "WP_APP_PASSWORD=dummy app password\n",
    )
    creds = load_wordpress_credentials(path)
    assert creds.app_password.get_secret_value() == _SECRET_PASSWORD


def test_site_url_without_scheme_gets_https(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL=bhanunuthakki.com\nWP_USERNAME=bhanu\nWP_APP_PASSWORD=abcd\n",
    )
    creds = load_wordpress_credentials(path)
    assert creds.site_url == "https://bhanunuthakki.com"


def test_site_url_trailing_slash_stripped(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL=https://bhanunuthakki.com/\nWP_USERNAME=bhanu\nWP_APP_PASSWORD=abcd\n",
    )
    creds = load_wordpress_credentials(path)
    assert creds.site_url == "https://bhanunuthakki.com"


def test_comments_and_blank_lines_are_ignored(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "# a comment\n\nWP_SITE_URL=https://bhanunuthakki.com\n"
        "WP_USERNAME=bhanu\nWP_APP_PASSWORD=abcd\n",
    )
    creds = load_wordpress_credentials(path)
    assert creds.username == "bhanu"


def test_value_containing_equals_sign_kept_whole(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL=https://bhanunuthakki.com\nWP_USERNAME=bhanu\nWP_APP_PASSWORD=ab=cd EFGH\n",
    )
    creds = load_wordpress_credentials(path)
    assert creds.app_password.get_secret_value() == "ab=cdEFGH"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(CredentialsError, match="not found"):
        load_wordpress_credentials(tmp_path / "missing.env")


def test_missing_key_names_the_key_and_the_path(tmp_path: Path) -> None:
    path = _write_env(tmp_path, "WP_SITE_URL=https://bhanunuthakki.com\nWP_USERNAME=bhanu\n")
    with pytest.raises(CredentialsError) as exc_info:
        load_wordpress_credentials(path)
    message = str(exc_info.value)
    assert "WP_APP_PASSWORD" in message
    assert str(path) in message


def test_empty_value_counts_as_missing(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL=https://bhanunuthakki.com\nWP_USERNAME=bhanu\nWP_APP_PASSWORD=   \n",
    )
    with pytest.raises(CredentialsError, match="WP_APP_PASSWORD"):
        load_wordpress_credentials(path)


def test_password_never_appears_in_repr_or_str(tmp_path: Path) -> None:
    path = _write_env(
        tmp_path,
        "WP_SITE_URL=https://bhanunuthakki.com\n"
        f"WP_USERNAME=bhanu\nWP_APP_PASSWORD={_SECRET_PASSWORD}\n",
    )
    creds = load_wordpress_credentials(path)
    assert _SECRET_PASSWORD not in repr(creds)
    assert _SECRET_PASSWORD not in str(creds)


def test_password_never_appears_in_missing_key_error(tmp_path: Path) -> None:
    """Even if a sibling value happens to look secret-shaped, the error for
    a *different* missing key must never echo it back."""
    path = _write_env(
        tmp_path, f"WP_SITE_URL=https://bhanunuthakki.com\nWP_APP_PASSWORD={_SECRET_PASSWORD}\n"
    )
    with pytest.raises(CredentialsError) as exc_info:
        load_wordpress_credentials(path)
    assert _SECRET_PASSWORD not in str(exc_info.value)
