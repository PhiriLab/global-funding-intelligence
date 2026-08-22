from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml


@dataclass(frozen=True)
class FundingSource:
    id: str
    name: str
    primary_url: str
    geography: tuple[str, ...]
    categories: tuple[str, ...]
    source_type: str
    authority: str
    priority: str
    notes: str | None = None


@dataclass(frozen=True)
class SourceHealth:
    source_id: str
    ok: bool
    status_code: int | None
    final_url: str | None
    error: str | None = None


def load_funding_sources(path: str | Path = "config/funding_sources.yaml") -> tuple[dict[str, Any], list[FundingSource]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sources = [
        FundingSource(
            id=item["id"],
            name=item["name"],
            primary_url=item["primary_url"],
            geography=tuple(item.get("geography", [])),
            categories=tuple(item.get("categories", [])),
            source_type=item.get("source_type", "html"),
            authority=item.get("authority", "primary"),
            priority=item.get("priority", "medium"),
            notes=item.get("notes"),
        )
        for item in raw.get("sources", [])
    ]
    return raw.get("policy", {}), sources


async def check_source(client: httpx.AsyncClient, source: FundingSource) -> SourceHealth:
    try:
        response = await client.get(source.primary_url, follow_redirects=True)
        return SourceHealth(source_id=source.id, ok=200 <= response.status_code < 400, status_code=response.status_code, final_url=str(response.url))
    except httpx.HTTPError as exc:
        return SourceHealth(source_id=source.id, ok=False, status_code=None, final_url=None, error=str(exc))


async def check_all_sources(sources: list[FundingSource], concurrency: int = 8, timeout: float = 20.0) -> list[SourceHealth]:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    headers = {"User-Agent": "PhiriLab-Research-Observatory/1.0 funding-source-health-check"}
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, headers=headers) as client:
        async def bounded(source: FundingSource) -> SourceHealth:
            async with semaphore:
                return await check_source(client, source)
        return list(await asyncio.gather(*(bounded(source) for source in sources)))
