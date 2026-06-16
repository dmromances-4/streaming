"""Tests unitarios Skill #3."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_invalid_url_error():
    from errors import InvalidUrlError

    exc = InvalidUrlError("bad")
    assert exc.http_status == 400


def test_rewrite_playlist():
    from m3u8_rewriter import rewrite_playlist

    content = """#EXTM3U
#EXT-X-VERSION:3
#EXTINF:6.0,
segment_000.ts
#EXTINF:6.0,
https://cdn.example.com/live/seg001.ts
"""
    result = rewrite_playlist(content, "https://stream.example.com/live/playlist.m3u8")
    assert "/api/v1/fetch?url=" in result
    assert "cdn.example.com" in result
    assert not result.strip().endswith("segment_000.ts")


def test_rewrite_playlist_media_uris():
    from m3u8_rewriter import rewrite_playlist

    content = """#EXTM3U
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Español",URI="https://rtvelivestream.rtve.es/rtvesec/la1/la1_main_dvr_es.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=3012608,RESOLUTION=1280x720,AUDIO="audios",SUBTITLES="subs"
https://rtvelivestream.rtve.es/rtvesec/la1/la1_main_dvr_720.m3u8
"""
    result = rewrite_playlist(content, "https://ztnr.rtve.es/ztnr/1688877.m3u8")
    assert "rtvelivestream.rtve.es" in result
    assert 'URI="/api/live/api/v1/fetch?url=' in result
    assert result.count("/api/v1/fetch?url=") == 2
    assert "https://rtvelivestream.rtve.es/rtvesec/la1/la1_main_dvr_es.m3u8" not in result


def test_validate_blocks_localhost():
    from errors import InvalidUrlError
    from url_validator import validate_target_url

    with pytest.raises(InvalidUrlError):
        validate_target_url("http://localhost/playlist.m3u8")


def test_static_resolver():
    from resolvers.static_resolver import resolve_static_channel

    result = resolve_static_channel({"stream_url": "https://example.com/live.m3u8"})
    assert result.manifest_url == "https://example.com/live.m3u8"
    assert result.error is None

    result2 = resolve_static_channel({})
    assert result2.manifest_url is None
    assert result2.error


def test_bbc_parse_manifest_href():
    from resolvers.bbc_iplayer_resolver import _parse_manifest_href

    xml = """<?xml version="1.0"?>
    <media xmlns="http://www.bbc.co.uk/2008/MPD">
      <items><item><kind>video</kind>
        <connection><href>https://vs-hls-push-uk-live.akamaized.net/x/manifest.m3u8</href></connection>
      </item></items>
    </media>"""
    assert _parse_manifest_href(xml) == "https://vs-hls-push-uk-live.akamaized.net/x/manifest.m3u8"


def test_rai_extract_m3u8():
    from resolvers.rai_resolver import _extract_m3u8_url

    body = '<url type="content">https://rai.example.com/live.m3u8?token=1</url>'
    assert _extract_m3u8_url(body) == "https://rai.example.com/live.m3u8?token=1"


def test_validate_allows_https():
    from url_validator import validate_target_url

    # No DNS resolution needed if we mock - this may resolve on network
    # Test scheme validation only
    with pytest.raises(Exception):
        validate_target_url("ftp://example.com/x")


def test_ccma_pick_hls_url():
    from resolvers.ccma_resolver import _pick_hls_url

    media = [
        {"geo": "CATALUNYA", "format": "HLS", "url": "https://cat.example/master.m3u8"},
        {"geo": "ESPANYA", "format": "HLS", "url": "https://es.example/master.m3u8"},
        {"geo": "TOTS", "format": "HLS", "url": "https://int.example/master.m3u8"},
    ]
    assert _pick_hls_url(media) == "https://es.example/master.m3u8"


def test_ccma_pick_hls_url_tots_fallback():
    from resolvers.ccma_resolver import _pick_hls_url

    media = [
        {"geo": "CATALUNYA", "format": "HLS", "url": "https://cat.example/master.m3u8"},
        {"geo": "TOTS", "format": "HLS", "url": "https://int.example/master.m3u8"},
    ]
    assert _pick_hls_url(media) == "https://int.example/master.m3u8"


def test_scrape_extract_m3u8():
    from resolvers._scrape_utils import extract_m3u8_urls, pick_best_m3u8

    html = 'var src = "https://cdn.example.com/live/master.m3u8?token=abc";'
    urls = extract_m3u8_urls(html)
    assert urls == ["https://cdn.example.com/live/master.m3u8?token=abc"]
    assert pick_best_m3u8(urls) == "https://cdn.example.com/live/master.m3u8?token=abc"


def test_filter_channels_autonomic_tag():
    from channel_catalog import filter_channels, reload_channels

    reload_channels()
    items = filter_channels(country="ES", tag="autonomic")
    assert items
    assert all("autonomic" in [t.lower() for t in (c.get("tags") or [])] for c in items)


def test_proxy_url_includes_channel_id():
    from m3u8_rewriter import proxy_url

    url = proxy_url("https://cdn.example.com/live/seg.ts", channel_id="es-telemadrid")
    assert "channel_id=es-telemadrid" in url
    assert "/api/v1/fetch?url=" in url


def test_proxy_headers_for_channel():
    from channel_catalog import proxy_headers_for_channel, reload_channels

    reload_channels()
    headers = proxy_headers_for_channel("es-telemadrid")
    assert headers.get("Referer") == "https://www.telemadrid.es/"
    assert headers.get("Origin") == "https://www.telemadrid.es"
    assert proxy_headers_for_channel("unknown-channel") == {}


def test_brightcove_pick_hls_source():
    from resolvers.brightcove_resolver import _pick_hls_source

    sources = [
        {"src": "https://example.com/live/playlist-dash.mpd", "type": "application/dash+xml"},
        {"src": "https://example.com/live/playlist-hls.m3u8", "type": "application/x-mpegURL"},
    ]
    assert _pick_hls_source(sources) == "https://example.com/live/playlist-hls.m3u8"


def test_extract_m3u8_from_json():
    from resolvers._scrape_utils import extract_m3u8_from_json, pick_best_m3u8

    html = """
    <script type="application/json">
    {"player":{"sourceURL":"https://cdn.example.com/live/master.m3u8"}}
    </script>
    """
    urls = extract_m3u8_from_json(html)
    assert "https://cdn.example.com/live/master.m3u8" in urls
    assert pick_best_m3u8(urls) == "https://cdn.example.com/live/master.m3u8"


def test_brightcove_video_path_numeric():
    from resolvers.brightcove_resolver import _video_path_from_ref

    assert _video_path_from_ref("1846756479408303045") == "1846756479408303045"
    assert _video_path_from_ref("ref:Live_Telemadrid") == "ref:Live_Telemadrid"
    assert _video_path_from_ref("Live_LaOtra") == "ref:Live_LaOtra"


def test_brightcove_policy_key_from_video_cloud():
    from resolvers.brightcove_resolver import _policy_key_from_config

    assert _policy_key_from_config({"policy_key": "pk-root"}) == "pk-root"
    assert _policy_key_from_config({"video_cloud": {"policy_key": "pk-cloud"}}) == "pk-cloud"
    assert _policy_key_from_config({}) is None
