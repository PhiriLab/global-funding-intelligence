from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .multi_source_public_feed import fetch_multi_source_public_feed


async def generate_public_opportunity_file(
    output: str | Path,
    *,
    min_records: int = 1,
    page_size: int = 100,
    html_source_limit: int = 20,
) -> int:
    """Fetch, validate and atomically publish the current structured multi-source feed.

    EU remains the required baseline source. UKRI, NIHR and Wellcome are additive
    collectors: an individual source can fail or yield no publishable detail pages
    without erasing valid records from the other sources. The destination is not
    touched until the combined feed passes the minimum-record check.
    """
    if min_records < 0:
        raise ValueError("min_records must be non-negative")
    if html_source_limit < 0:
        raise ValueError("html_source_limit must be non-negative")

    feed, source_results = await fetch_multi_source_public_feed(
        eu_page_size=page_size,
        html_source_limit=html_source_limit,
    )
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

    for result in source_results:
        print(
            f"{result.source_id}: discovered={result.discovered} "
            f"accepted={result.accepted} errors={len(result.errors)}"
        )
    return feed.opportunity_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish the current structured opportunity feed for GitHub Pages")
    parser.add_argument("--output", default="web/data/opportunities.json")
    parser.add_argument("--min-records", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--html-source-limit", type=int, default=20)
    return parser


def main() -> int:
    args = _parser().parse_args()
    count = asyncio.run(
        generate_public_opportunity_file(
            args.output,
            min_records=args.min_records,
            page_size=args.page_size,
            html_source_limit=args.html_source_limit,
        )
    )
    print(f"Published {count} structured opportunities to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
