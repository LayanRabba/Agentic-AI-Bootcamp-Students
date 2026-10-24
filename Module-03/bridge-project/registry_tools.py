
"""
Registry tools for the Vendor Onboarding Desk.

GLEIF: Legal Entity Identifier registry.
OFAC: US sanctions list.

All tools return strings and do not raise
exceptions to the calling agent.
"""

from __future__ import annotations

import csv
import difflib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


NO_RECORDS = "NO_RECORDS"
NO_SANCTIONS_MATCH = "NO_SANCTIONS_MATCH"
LOOKUP_UNAVAILABLE = "LOOKUP_UNAVAILABLE"

_UA = (
    "JHF-Agentic-AI-Bootcamp/1.0 "
    "(student project)"
)

_TIMEOUT = 30

_SDN_URL = (
    "https://www.treasury.gov/ofac/downloads/sdn.csv"
)

_SDN_CACHE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".sdn_cache.csv",
)


# ================================================
# TOOL 1: OFAC SANCTIONS SCREENING
# ================================================

def _load_sdn() -> list[tuple[str, str]]:
    """Download once, then use the local SDN cache."""

    if not os.path.exists(_SDN_CACHE):
        request = urllib.request.Request(
            _SDN_URL,
            headers={"User-Agent": _UA},
        )

        with urllib.request.urlopen(
            request, timeout=60
        ) as response:
            with open(_SDN_CACHE, "wb") as file:
                file.write(response.read())

    with open(
        _SDN_CACHE,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:

        rows = csv.reader(file)

        return [
            (row[1].strip(), row[3].strip())
            for row in rows
            if (
                len(row) > 3
                and row[2].strip().lower() == "-0-"
                and row[1].strip()
            )
        ]


def _normalise(name: str) -> str:
    """Normalize a name for fuzzy matching."""

    value = re.sub(
        r"[^a-z0-9 ]",
        " ",
        (name or "").lower(),
    )

    for suffix in (
        " ltd", " llc", " inc", " plc",
        " ag", " a s", " pjsc", " fze",
        " aps", " gmbh", " sa", " nv", " bv",
    ):
        value = value.replace(suffix, " ")

    return " ".join(value.split())


def sanctions_screen(
    name: str,
    top: int = 5,
) -> str:
    """
    Screen a legal name against the OFAC SDN list.

    Returns the closest matching entries and
    their similarity scores from 0.0 to 1.0.

    A similarity match is NOT a legal finding
    that two entities are identical.
    """

    try:
        sdn = _load_sdn()
    except Exception:
        return LOOKUP_UNAVAILABLE

    target = _normalise(name)

    if not target:
        return NO_SANCTIONS_MATCH

    scored = []

    for listed, programme in sdn:
        score = difflib.SequenceMatcher(
            None,
            target,
            _normalise(listed),
        ).ratio()

        scored.append(
            (score, listed, programme)
        )

    scored.sort(reverse=True)

    best = scored[:top]

    if not best or best[0][0] < 0.55:
        return NO_SANCTIONS_MATCH

    lines = [
        (
            f"closest entries on the OFAC list "
            f"to '{name}' "
            f"(similarity 0.0-1.0, NOT a verdict):"
        )
    ]

    for score, listed, programme in best:
        lines.append(
            f"  {score:.2f}  {listed}"
            f"   [programme: {programme}]"
        )

    return "\n".join(lines)


# ================================================
# TOOL 2: GLEIF REGISTRY LOOKUP
# ================================================

def gleif_lookup(legal_name: str) -> str:
    """
    Query the live GLEIF Legal Entity Identifier
    registry using the company's legal name.

    Return all candidates rather than only
    the first record.

    Each result includes:
    - Legal name
    - LEI
    - Country
    - Entity status
    - Registration status

    Return NO_RECORDS when the registry reports
    no matches.

    Return LOOKUP_UNAVAILABLE when the registry
    request or response cannot be completed.
    """

    try:
        params = urllib.parse.urlencode({
            "filter[entity.legalName]": legal_name,
            "page[size]": "100",
        })

        url = (
            "https://api.gleif.org/api/v1/"
            "lei-records?"
            + params
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": _UA,
                "Accept": "application/vnd.api+json",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=_TIMEOUT,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        records = payload.get("data", [])

        if not records:
            return NO_RECORDS

        lines = []
        exact_matches = 0

        for record in records:

            attributes = (
                record.get("attributes") or {}
            )

            entity = (
                attributes.get("entity") or {}
            )

            registration = (
                attributes.get("registration") or {}
            )

            name_info = (
                entity.get("legalName") or {}
            )

            if isinstance(name_info, dict):
                name = name_info.get("name", "")
            else:
                name = str(name_info)

            address = (
                entity.get("legalAddress") or {}
            )

            country = address.get(
                "country",
                "UNKNOWN",
            )

            entity_status = entity.get(
                "status",
                "UNKNOWN",
            )

            registration_status = (
                registration.get(
                    "status",
                    "UNKNOWN",
                )
            )

            lei = (
                attributes.get("lei")
                or record.get("id")
                or "UNKNOWN"
            )

            if (
                name.strip().casefold()
                == legal_name.strip().casefold()
            ):
                exact_matches += 1

            lines.append(
                f"Legal name: {name} "
                f"| LEI: {lei} "
                f"| country: {country} "
                f"| entity status: {entity_status} "
                f"| registration status: "
                f"{registration_status}"
            )

        summary = (
            f"{len(records)} candidates; "
            f"{exact_matches} exactly matching "
            f"'{legal_name}'"
        )

        return (
            summary
            + "\n"
            + "\n".join(lines)
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        OSError,
    ):
        return LOOKUP_UNAVAILABLE
