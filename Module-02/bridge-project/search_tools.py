
"""
Web search tool for the Module 2 bridge project.

Search backends:
- DuckDuckGo Instant Answer API
- Wikipedia API

Results contain source URLs or one of two markers:

NO_RESULTS:
    Search ran successfully but found nothing useful.

SEARCH_UNAVAILABLE:
    Neither search backend could be used.

Compatibility fix:
    DuckDuckGo sometimes returns HTTP 202 with valid
    Instant Answer JSON. Accept valid JSON in that case.
"""

from __future__ import annotations

import time

import requests


NO_RESULTS = "NO_RESULTS"
SEARCH_UNAVAILABLE = "SEARCH_UNAVAILABLE"

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AgenticBootcamp/1.0)"
    )
}

_TIMEOUT = 12


class Unreachable(Exception):
    """Search service could not be reached successfully."""


def _get(url: str, params: dict) -> dict | None:
    """
    Make an HTTP GET request with retries.

    HTTP 200:
        Accept valid JSON.

    HTTP 202 from DuckDuckGo:
        Accept valid JSON if present.

    HTTP 429 / 503:
        Retry after a short delay.

    Other HTTP errors:
        Return None without treating them as
        successful search results.
    """

    last_error = "unknown"

    for attempt in range(3):
        try:
            response = requests.get(
                url,
                params=params,
                headers=_UA,
                timeout=_TIMEOUT,
            )

            status = response.status_code

            is_duckduckgo = (
                url.startswith("https://api.duckduckgo.com/")
            )

            acceptable_status = (
                status == 200
                or (is_duckduckgo and status == 202)
            )

            if acceptable_status:
                try:
                    data = response.json()
                except ValueError:
                    return None

                if isinstance(data, dict):
                    return data

                return None

            if status in (429, 503):
                last_error = f"HTTP {status}"

                time.sleep(1.5 * (attempt + 1))
                continue

            return None

        except requests.RequestException as error:
            last_error = (
                f"{type(error).__name__}: {error}"
            )

            time.sleep(1.0 * (attempt + 1))

    raise Unreachable(last_error)


def _duckduckgo(
    query: str,
) -> list[tuple[str, str, str]]:
    """Fetch relevant DuckDuckGo Instant Answer results."""

    data = _get(
        "https://api.duckduckgo.com/",
        {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        },
    )

    if not data:
        return []

    found: list[tuple[str, str, str]] = []

    if data.get("AbstractText"):
        found.append(
            (
                data.get("Heading") or query,
                data["AbstractText"],
                data.get("AbstractURL", ""),
            )
        )

    for topic in data.get("RelatedTopics", [])[:4]:
        if not isinstance(topic, dict):
            continue

        if not topic.get("Text"):
            continue

        found.append(
            (
                topic["Text"][:60],
                topic["Text"],
                topic.get("FirstURL", ""),
            )
        )

    return found


def _wikipedia(
    query: str,
) -> list[tuple[str, str, str]]:
    """Search Wikipedia and retrieve introductory extracts."""

    hits = _get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 3,
        },
    )

    if not hits:
        return []

    titles = [
        hit["title"]
        for hit in hits.get("query", {}).get("search", [])
    ]

    if not titles:
        return []

    extracts = _get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": "|".join(titles),
            "format": "json",
        },
    )

    if not extracts:
        return []

    found: list[tuple[str, str, str]] = []

    pages = (
        extracts.get("query", {})
        .get("pages", {})
        .values()
    )

    for page in pages:
        content = (
            page.get("extract") or ""
        ).strip()

        if not content:
            continue

        title = page.get("title", "")

        url = (
            "https://en.wikipedia.org/wiki/"
            + title.replace(" ", "_")
        )

        found.append(
            (title, content, url)
        )

    return found


def web_search(
    query: str,
    max_chars: int = 1400,
) -> str:
    """
    Search available backends.

    Return:
        - Plain text findings with source URLs
        - NO_RESULTS
        - SEARCH_UNAVAILABLE
    """

    query = (query or "").strip()

    if not query:
        return NO_RESULTS

    reachable = False
    results: list[tuple[str, str, str]] = []

    for backend in (
        _duckduckgo,
        _wikipedia,
    ):
        try:
            found = backend(query)

        except Unreachable:
            continue

        reachable = True
        results.extend(found)

        if len(results) >= 3:
            break

    if not reachable:
        return SEARCH_UNAVAILABLE

    if not results:
        return NO_RESULTS

    output = []
    used = 0

    for index, (title, content, url) in enumerate(
        results[:5],
        start=1,
    ):
        snippet = " ".join(content.split())

        remaining = max_chars - used

        if len(snippet) > remaining:
            snippet = snippet[:max(0, remaining)]

        if not snippet:
            break

        output.append(
            f"[{index}] {title}\n"
            f"    {snippet}\n"
            f"    source: {url or 'n/a'}"
        )

        used += len(snippet)

        if used >= max_chars:
            break

    if not output:
        return NO_RESULTS

    return "\n\n".join(output)


def selftest() -> int:
    """Check the two search backends."""

    print("checking search backends from this machine")
    print("=" * 60)

    reachable_count = 0

    backends = [
        ("duckduckgo", _duckduckgo),
        ("wikipedia", _wikipedia),
    ]

    for name, backend in backends:
        try:
            results = backend("Anthropic")

        except Unreachable as error:
            print(
                f"  {name:<12} UNREACHABLE   {error}"
            )
            continue

        reachable_count += 1

        print(
            f"  {name:<12} reachable     "
            f"({len(results)} hits)"
        )

    print("=" * 60)

    if reachable_count == 0:
        print(
            "Neither backend returned a usable response."
        )
        return 1

    print(
        "At least one backend returned a usable response."
    )
    return 0


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        raise SystemExit(selftest())

    query = (
        " ".join(sys.argv[1:])
        or "who founded Anthropic"
    )

    print(
        f"QUERY: {query}\n"
        + "=" * 60
    )

    print(web_search(query))
