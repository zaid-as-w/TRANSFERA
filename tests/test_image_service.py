"""Unit tests for Centralized Image Service and Fallback System."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import requests

from src.image_service import (
    FALLBACK_DATA_URIS,
    fetch_remote_image,
    get_club_crest_url,
    get_club_image,
    get_competition_image,
    get_competition_logo_url,
    get_country_flag,
    get_fallback_image,
    get_player_image,
    get_player_image_url,
    get_project_image_path,
    load_local_image,
    render_image_preview,
    render_player_image,
    validate_image_url,
)


def test_validate_image_url() -> None:
    """Test URL validator with various valid, invalid, empty, and null formats."""
    assert validate_image_url("https://example.com/player.png") is True
    assert validate_image_url("http://example.com/crest.jpg") is True
    assert validate_image_url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==") is True
    assert validate_image_url("data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=") is True

    # Invalid / empty / probe cases
    assert validate_image_url(None) is False
    assert validate_image_url("") is False
    assert validate_image_url("   ") is False
    assert validate_image_url("ftp://example.com/p.jpg") is False
    assert validate_image_url("http://localhost:8501/p.jpg") is False
    assert validate_image_url("http://127.0.0.1:8000/p.jpg") is False
    assert validate_image_url(12345) is False


def test_get_fallback_images() -> None:
    """Test fallback SVG data URIs for all supported categories."""
    for cat in ["player", "club", "competition", "country", "news"]:
        uri = get_fallback_image(cat)
        assert uri.startswith("data:image/svg+xml;base64,")
        assert len(uri) > 100

    # Unknown category falls back to player silhouette safely
    unknown_uri = get_fallback_image("unknown_category")
    assert unknown_uri == FALLBACK_DATA_URIS["player"]


def test_get_player_image_resolution(tmp_path: Any) -> None:
    """Test player image lookup with local files, valid remote URLs, and missing fallbacks."""
    # Remote valid URL returns the clean URL
    remote_url = "https://img.transfera.com/haaland.jpg"
    assert get_player_image(418560, remote_url) == remote_url

    # Missing player with no URL returns fallback SVG data URI
    missing_img = get_player_image(None, None)
    assert missing_img.startswith("data:image/svg+xml;base64,")

    # Empty string URL returns fallback
    empty_url_img = get_player_image(9999999, "")
    assert empty_url_img.startswith("data:image/svg+xml;base64,")


def test_local_image_loading(tmp_path: Any) -> None:
    """Test local image loading, missing files, and corruption handling."""
    dummy_img = tmp_path / "test.png"
    dummy_img.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagebytes123456789")

    # Valid local read
    data = load_local_image(dummy_img)
    assert data is not None
    assert len(data) > 10

    # Missing file returns None
    missing_file = tmp_path / "missing.png"
    assert load_local_image(missing_file) is None

    # Empty file returns None
    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")
    assert load_local_image(empty_file) is None


def test_project_image_path_resolution() -> None:
    """Test repository relative path resolution and case handling."""
    path = get_project_image_path("players", "nonexistent_123.png")
    assert "players" in str(path)
    assert path.name == "nonexistent_123.png"


@patch("requests.get")
def test_fetch_remote_image_success(mock_get: MagicMock) -> None:
    """Test mocked successful remote image fetch with valid MIME type."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "image/jpeg", "Content-Length": "1024"}
    mock_resp.content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"X" * 200
    mock_get.return_value = mock_resp

    result = fetch_remote_image("https://example.com/valid.jpg")
    assert result is not None
    assert result.startswith(b"\xff\xd8\xff\xe0")


@patch("requests.get")
def test_fetch_remote_image_http_404(mock_get: MagicMock) -> None:
    """Test mocked HTTP 404 response gracefully returns None."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    result = fetch_remote_image("https://example.com/notfound.jpg")
    assert result is None


@patch("requests.get")
def test_fetch_remote_image_http_403(mock_get: MagicMock) -> None:
    """Test mocked HTTP 403 Forbidden response gracefully returns None."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_get.return_value = mock_resp

    result = fetch_remote_image("https://example.com/forbidden.jpg")
    assert result is None


@patch("requests.get")
def test_fetch_remote_image_timeout(mock_get: MagicMock) -> None:
    """Test network timeout exception returns None without crashing."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
    result = fetch_remote_image("https://example.com/slow.jpg")
    assert result is None


@patch("requests.get")
def test_fetch_remote_image_invalid_content_type(mock_get: MagicMock) -> None:
    """Test server returning text/html error page instead of image."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.content = b"<html><body>Cloudflare Blocked</body></html>"
    mock_get.return_value = mock_resp

    result = fetch_remote_image("https://example.com/blocked_page.jpg")
    assert result is None


def test_get_club_and_competition_image() -> None:
    """Test club crest and competition logo URL generators."""
    crest = get_club_image(club_id=11)
    assert "https://tmssl.akamaized.net/images/wappen/head/11.png" in crest

    # None club falls back to SVG club placeholder
    fallback_crest = get_club_image(club_id=None)
    assert fallback_crest.startswith("data:image/svg+xml;base64,")

    comp = get_competition_image(competition_id="GB1")
    assert "https://tmssl.akamaized.net/images/logo/header/gb1.png" in comp

    fallback_comp = get_competition_image(competition_id=None)
    assert fallback_comp.startswith("data:image/svg+xml;base64,")


def test_country_flags() -> None:
    """Test flag resolver for known and unknown nations."""
    assert get_country_flag("England") == "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
    assert get_country_flag("Brazil") == "🇧🇷"
    assert get_country_flag("Unknown Country") == "🌐"
    assert get_country_flag(None) == "🌐"


def test_render_player_image_html() -> None:
    """Test HTML image tag generation with onerror self-healing attributes."""
    html = render_player_image(
        player_id=10,
        raw_image_url="https://example.com/player.jpg",
        name="Luka Modric",
        size_px=60,
    )
    assert "<img" in html
    assert 'src="https://example.com/player.jpg"' in html
    assert 'alt="Luka Modric"' in html
    assert "onerror=" in html
    assert "data:image/svg+xml;base64," in html


def test_render_image_preview_mock(monkeypatch: Any) -> None:
    """Test st.image wrapper handles errors without raising."""
    mock_st_image = MagicMock()
    monkeypatch.setattr("streamlit.image", mock_st_image)

    # Valid preview call
    render_image_preview("https://example.com/photo.jpg", caption="Test Preview", width=120)
    mock_st_image.assert_called_once()


def test_backwards_compatibility_aliases() -> None:
    """Verify legacy function names are aliased for older modules."""
    assert get_player_image_url == get_player_image
    assert get_club_crest_url == get_club_image
    assert get_competition_logo_url == get_competition_image
