from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .eu_public_feed import fetch_public_eu_feed_json
from .public_opportunity_feed import PublicOpportunityFeed


async def generate_public_opportunity_file(
    output: str | Path,
    *,
    min_records: int = 1,
    page_size: int = 100,
) -> int:
    """Fetch, validate and atomically publish the current structured EU feed.

    The destination is not touched until the upstream response has passed the
    public schema and minimum-record checks. A failed refresh therefore leaves
    the previously deployed Pages artifact intact.
    """
    if min_records < 0:
        raise ValueError("min_records must be non-negative")

    raw = await fetch_public_eu_feed_json(page_size=page_size, indent=None)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("generated opportunity feed is not valid JSON") from exc

    feed = PublicOpportunityFeed.model_validate(payload)
    if feed.opportunity_count != len(feed.opportunities):
        raise ValueError("opportunity_count does not match published records")
    if feed.opportunity_count < min_records:
        raise ValueError(
            f"refusing to publish {feed.opportunity_count} records; "
            f"minimum safe threshold is {min_records}"
        )

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        feed.model_dump_json(indent=2, exclude_none=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return feed.opportunity_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish the current structured opportunity feed for GitHub Pages")
    parser.add_argument("--output", default="web/data/opportunities.json")
    parser.add_argument("--min-records", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    return parser


def main() -> int:
    args = _parser().parse_args()
    count = asyncio.run(
        generate_public_opportunity_file(
            args.output,
            min_records=args.min_records,
            page_size=args.page_size,
        )
    )
    print(f"Published {count} structured opportunities to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
