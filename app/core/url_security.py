import ipaddress
import socket
from urllib.parse import urlparse

from app.core.exceptions import UnsafeUrlError
from app.core.metrics import UNSAFE_URL_BLOCKED_TOTAL


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        UNSAFE_URL_BLOCKED_TOTAL.labels(reason="invalid_scheme").inc()
        raise UnsafeUrlError("Only http and https image URLs are allowed.")
    if not parsed.hostname:
        UNSAFE_URL_BLOCKED_TOTAL.labels(reason="missing_hostname").inc()
        raise UnsafeUrlError("Image URL must include a hostname.")
    if parsed.username or parsed.password:
        UNSAFE_URL_BLOCKED_TOTAL.labels(reason="credentials").inc()
        raise UnsafeUrlError("Image URLs must not include credentials.")

    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "0.0.0.0"}:
        UNSAFE_URL_BLOCKED_TOTAL.labels(reason="localhost").inc()
        raise UnsafeUrlError("Localhost image URLs are not allowed.")

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        UNSAFE_URL_BLOCKED_TOTAL.labels(reason="dns_resolution").inc()
        raise UnsafeUrlError("Image URL hostname could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if _is_blocked_ip(ip):
            UNSAFE_URL_BLOCKED_TOTAL.labels(reason="blocked_ip").inc()
            raise UnsafeUrlError("Private, loopback, link-local, or reserved URLs are not allowed.")

    return url


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
