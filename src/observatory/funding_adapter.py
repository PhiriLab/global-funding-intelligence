from __future__ import annotations

import hashlib
import ipaddress
import posixpath
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx

from .untrusted import UntrustedContent, sanitise_external_text

MAX_BODY_BYTES = 1_000_000
MAX_REDIRECTS = 5
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}


@dataclass(frozen=True)
class FundingSnapshot:
    source_id: str
    source_url: str
    final_url: str
    status_code: int
    text: str
    content_hash: str
    candidate_links: tuple[str, ...]


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def _validated_port(parsed) -> int | None:
    try:
        return parsed.port
    except ValueError as exc:
        raise ValueError("funding source URL contains an invalid port") from exc


def canonicalise_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("funding source URLs must not contain user credentials")
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower().rstrip(".")
    port = _validated_port(parsed)
    try:
        host_ip = ipaddress.ip_address(host)
    except ValueError:
        host_ip = None
    rendered_host = f"[{host}]" if isinstance(host_ip, ipaddress.IPv6Address) else host
    netloc = rendered_host
    if port and not (scheme == "https" and port == 443):
        netloc = f"{rendered_host}:{port}"
    raw_path = parsed.path or "/"
    path = posixpath.normpath(re_slashes(raw_path))
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS))
    return urlunparse((scheme, netloc, path, "", query, ""))


def re_slashes(path: str) -> str:
    while "//" in path:
        path = path.replace("//", "/")
    return path


def _candidate_links(base_url: str, html: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    parser = _LinkParser()
    parser.feed(html)
    base_host = (urlparse(base_url).hostname or "").lower().rstrip(".")
    found: set[str] = set()
    for raw in parser.links:
        absolute = urljoin(base_url, raw)
        parsed = urlparse(absolute)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or host != base_host:
            continue
        try:
            canonical = canonicalise_url(absolute)
        except ValueError:
            continue
        if any(keyword in canonical.lower() for keyword in keywords):
            found.add(canonical)
    return tuple(sorted(found))


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def _assert_public_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("funding source URLs must not contain user credentials")
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("primary funding sources must use a valid HTTPS URL")
    port = _validated_port(parsed)
    host = parsed.hostname.rstrip(".")
    if host.lower() == "localhost":
        raise ValueError("local hosts are not allowed")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not _is_public_ip(str(literal)):
            raise ValueError("private, local, or reserved IP addresses are not allowed")
        return
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"unable to resolve funding source host: {host}") from exc
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise ValueError("funding source host resolves to a non-public address")


async def _read_limited_html(response: httpx.Response, max_bytes: int = MAX_BODY_BYTES) -> bytes:
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise ValueError(f"expected HTML source, got {content_type or 'unknown content type'}")
    declared = response.headers.get("content-length")
    if declared:
        try:
            declared_size = int(declared)
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > max_bytes:
            raise ValueError("funding source response exceeds maximum allowed size")
    body = bytearray()
    async for chunk in response.aiter_bytes():
        if len(body) + len(chunk) > max_bytes:
            raise ValueError("funding source response exceeds maximum allowed size")
        body.extend(chunk)
    return bytes(body)


async def fetch_primary_html(source_id: str, url: str, *, keywords: tuple[str, ...] = ("fund", "grant", "opportun", "call", "award"), timeout: float = 20.0) -> FundingSnapshot:
    _assert_public_https_url(url)
    headers = {"User-Agent": "PhiriLab-Research-Observatory/1.0 funding-intelligence"}
    current = canonicalise_url(url)
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=False) as client:
        for redirect_count in range(MAX_REDIRECTS + 1):
            _assert_public_https_url(current)
            async with client.stream("GET", current) as response:
                if response.is_redirect:
                    if redirect_count >= MAX_REDIRECTS:
                        raise ValueError("too many redirects from funding source")
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("redirect response missing Location header")
                    current = canonicalise_url(urljoin(current, location))
                    _assert_public_https_url(current)
                    continue
                response.raise_for_status()
                raw_bytes = await _read_limited_html(response)
                final = canonicalise_url(str(response.url))
                _assert_public_https_url(final)
                encoding = response.encoding or "utf-8"
                raw = raw_bytes.decode(encoding, errors="replace")
                safe_text = sanitise_external_text(raw)
                digest = hashlib.sha256(raw_bytes).hexdigest()
                links = _candidate_links(final, raw, keywords)
                UntrustedContent(source_url=final, text=safe_text)
                return FundingSnapshot(source_id=source_id, source_url=canonicalise_url(url), final_url=final, status_code=response.status_code, text=safe_text, content_hash=digest, candidate_links=links)
    raise RuntimeError("funding source fetch did not return a terminal response")
