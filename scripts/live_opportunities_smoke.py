from __future__ import annotations

import os
import sys
from playwright.sync_api import sync_playwright


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    raw_url = os.environ.get("PAGE_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not raw_url:
        fail("PAGE_URL or URL argument is required")
    base = raw_url.rstrip("/") + "/"

    page_errors: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="en-GB")
        page = context.new_page()

        # Exercise the production browser path without adding synthetic analytics rows.
        page.route("**/rest/v1/gfi_usage_events", lambda route: route.fulfill(status=201, body=""))
        page.route("**/rest/v1/gfi_usefulness_pulse", lambda route: route.fulfill(status=201, body=""))
        page.route("**/rest/v1/gfi_application_journey_events", lambda route: route.fulfill(status=201, body=""))

        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        response = page.goto(base, wait_until="domcontentloaded", timeout=30_000)
        if response is None or not response.ok:
            fail(f"live page failed to load: {getattr(response, 'status', None)}")

        page.wait_for_function(
            """() => {
              const el = document.querySelector('#opportunityFeedStatus');
              return el && !el.textContent.includes('Loading verified opportunity feed');
            }""",
            timeout=30_000,
        )

        status = page.locator("#opportunityFeedStatus").inner_text().strip()
        if "unavailable" in status.lower():
            fail(f"opportunity feed reports unavailable: {status}")

        cards = page.locator("#opportunityCards .opportunity-card")
        card_count = cards.count()
        if card_count < 1:
            fail("no opportunity cards rendered in the live browser")

        shown_count = page.locator("#opportunityCount").inner_text().strip()
        if shown_count != str(card_count):
            fail(f"opportunity count mismatch: UI={shown_count}, cards={card_count}")

        if page.locator("#opportunitySourceHealth .source-health-item").count() < 1:
            fail("source-health UI did not render")

        required = [
            "#opportunityLifecycleFilter",
            "#opportunitySearch",
            "#opportunityCountry",
            "#opportunityOrganisation",
            "#opportunityGMRoute",
            "#opportunityEvidence",
            ".profile-matcher",
            "#applicationJourney",
        ]
        missing = [selector for selector in required if page.locator(selector).count() != 1]
        if missing:
            fail(f"missing Opportunities controls/components: {missing}")

        # Search must update cards and recover when cleared.
        search = page.locator("#opportunitySearch")
        search.fill("__gfi_smoke_no_match__")
        page.wait_for_function("document.querySelector('#opportunityCount').textContent === '0'")
        if page.locator("#opportunityCards .opportunity-empty").count() != 1:
            fail("empty-state did not render after a no-match search")
        search.fill("")
        page.wait_for_function("Number(document.querySelector('#opportunityCount').textContent) > 0")

        # Country sanitizer is part of the applicant-route interaction path.
        country = page.locator("#opportunityCountry")
        country.fill("g1b")
        if country.input_value() != "GB":
            fail(f"country input sanitizer failed: {country.input_value()!r}")
        country.fill("")

        # Primary-source CTA must remain a real external link.
        source_link = page.locator("#opportunityCards .source-link").first
        href = source_link.get_attribute("href") or ""
        if not href.startswith("http"):
            fail(f"primary-source link is invalid: {href!r}")

        if page_errors:
            fail(f"browser page errors: {page_errors}")
        if console_errors:
            fail(f"browser console errors: {console_errors}")

        print(
            "Live Opportunities browser smoke passed: "
            f"{card_count} card(s), source health, filters, search, profile matcher, journey UI, source link"
        )
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
