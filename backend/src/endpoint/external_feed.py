import asyncio
import json
from ipaddress import ip_address
from socket import inet_aton
from urllib.parse import urlsplit

import aiohttp

from src.config import get_config
from src.database import sessionmanager
from src.logging import get_logger

from .service import insert_missing_endpoints

logger = get_logger(__name__)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 1_000
REQUEST_TIMEOUT_SECONDS = 20


def parse_external_feed(payload: object) -> list[str]:
    """Return normalized public endpoint URLs from an untrusted feed payload."""
    if not isinstance(payload, list):
        raise ValueError("External feed must be a JSON array")
    if len(payload) > MAX_RECORDS:
        raise ValueError(f"External feed exceeds the {MAX_RECORDS} record limit")

    urls: list[str] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("server"), str):
            continue
        url = _normalize_external_url(item["server"])
        if url is not None and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _normalize_external_url(raw_url: str) -> str | None:
    url = raw_url.strip().removesuffix("/")
    if not url or any(character.isspace() for character in url) or "\\" in url:
        return None

    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        _ = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or "?" in url
        or "#" in url
    ):
        return None

    normalized_host = host.casefold().rstrip(".")
    if (
        "%" in normalized_host
        or normalized_host == "localhost"
        or normalized_host.endswith(".localhost")
    ):
        return None

    try:
        address = ip_address(normalized_host)
    except ValueError:
        try:
            address = ip_address(inet_aton(normalized_host))
        except OSError:
            address = None
    if address is not None and (
        not address.is_global
        or address.is_multicast
        or getattr(address, "is_site_local", False)
    ):
        return None

    return url


async def download_external_feed(url: str) -> list[str]:
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as client:
        async with client.get(url) as response:
            response.raise_for_status()
            if response.content_length and response.content_length > MAX_RESPONSE_BYTES:
                raise ValueError("External feed response is too large")
            try:
                body = await response.content.readexactly(MAX_RESPONSE_BYTES + 1)
            except asyncio.IncompleteReadError as error:
                body = error.partial
            else:
                raise ValueError("External feed response is too large")

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("External feed is not valid JSON") from error
    return parse_external_feed(payload)


async def sync_external_feed() -> None:
    """Import new feed URLs and queue local verification without failing startup."""
    try:
        urls = await download_external_feed(get_config().app.external_feed_url)
        async with sessionmanager.session() as session:
            _, new_ids = await insert_missing_endpoints(session, urls)

        from .scheduler import get_scheduler

        scheduler = get_scheduler()
        for endpoint_id in new_ids:
            await scheduler.schedule_endpoint_test(endpoint_id)
        logger.info("External feed sync imported %s new endpoints", len(new_ids))
    except Exception as error:
        logger.error("External feed sync failed: %s", error)
