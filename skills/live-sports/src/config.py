"""Configuración del Skill #3."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8003
    skill_name: str = "live-sports"
    log_level: str = "INFO"

    proxy_timeout_seconds: int = 30
    max_redirects: int = 5
    user_agent: str = "StreamingPlatform/1.0 LiveSportsProxy"
    public_api_base: str = "/api/live"
    block_private_ips: bool = True

    vpn_required: bool = False
    vpn_health_url: str = "http://127.0.0.1:9999/v1/openvpn/status"

    live_channels_path: str = "/app/catalog/data/live-channels.yaml"
    live_channels_dir: str = "/app/catalog/data/live-channels"

    resolver_cache_ttl_seconds: int = 300
    bbc_iplayer_cookies: str = ""
    france_tv_cookies: str = ""


settings = Settings()
