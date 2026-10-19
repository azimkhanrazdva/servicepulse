import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from app.config import settings


class UnsafeTarget(ValueError):
    pass


def validate_url(value: str):
    try:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.fragment
            or "%" in url.hostname
            or any(ord(c) < 33 or ord(c) == 127 for c in value)
        ):
            raise UnsafeTarget(
                "Use an HTTP(S) URL without credentials, fragments or control characters"
            )
        _ = url.port
    except ValueError as exc:
        raise UnsafeTarget("Invalid HTTP(S) target") from exc
    return url


def origin(url):
    return url.scheme, url.hostname, url.port or (443 if url.scheme == "https" else 80)


async def pinned_target(value: str):
    url = validate_url(value)
    simulator = bool(settings.simulator_origin) and origin(url) == origin(
        validate_url(settings.simulator_origin)
    )
    addresses = await asyncio.get_running_loop().getaddrinfo(
        url.hostname,
        url.port or (443 if url.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    ips = [ipaddress.ip_address(answer[4][0]) for answer in addresses]
    if not ips or (not simulator and any(not ip.is_global for ip in ips)):
        raise UnsafeTarget("Destination address is not allowed")
    original = httpx.URL(value)
    return (
        original.copy_with(host=str(ips[0])),
        original.netloc.decode(),
        original.raw_host.decode(),
    )
