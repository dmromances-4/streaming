"""Validación de URLs para prevenir SSRF básico."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from errors import InvalidUrlError


def validate_target_url(url: str, *, block_private: bool = True) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidUrlError("URL must use http or https")
    if not parsed.hostname:
        raise InvalidUrlError("URL must have a hostname")

    if block_private:
        _check_hostname(parsed.hostname)

    return url


def _check_hostname(hostname: str) -> None:
    lowered = hostname.lower()
    if lowered in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise InvalidUrlError("Private/local URLs are not allowed")

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise InvalidUrlError(f"Cannot resolve hostname: {hostname}") from exc

    for info in addr_infos:
        ip = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            raise InvalidUrlError("Private IP addresses are not allowed")
