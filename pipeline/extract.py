"""Download data from the AIHW MyHospitals API."""
import logging
import time

import requests

from .config import API_BASE, MAX_PAGES, PAGE_SIZE, REQUEST_PAUSE_SECONDS

log = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update({
    "Accept": "application/json",
    "User-Agent": "qld-hospital-analytics (portfolio project)",
})

RETRY_WAITS = [5, 15, 30, 60]   # seconds to wait after each failed attempt


def get_json(url: str, params: dict | None = None) -> dict:
    """GET a URL and return its JSON, retrying with a growing wait on failure."""
    attempts = len(RETRY_WAITS) + 1
    for attempt in range(1, attempts + 1):
        try:
            resp = _session.get(url, params=params, timeout=90)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s %s: %s",
                        attempt, attempts, url, params, exc)
            if attempt == attempts:
                raise
            time.sleep(RETRY_WAITS[attempt - 1])


def get_version_info() -> dict:
    """Return the API's version_information block (contains data_version)."""
    return get_json(f"{API_BASE}/measure-categories")["version_information"]


def get_measure_codes(category_code: str) -> list[str]:
    """List the measure codes inside one category."""
    payload = get_json(f"{API_BASE}/measure-categories/{category_code}/measures")
    return [m["measure_code"] for m in payload["result"]]


def fetch_measure(category_code: str, measure_code: str) -> list[dict]:
    """Download every row of one measure, 1,000 rows at a time.

    Filtering by measure keeps the skip offset small, which avoids
    the 504 timeouts the API gives on deep offsets.
    """
    rows: list[dict] = []
    for page in range(MAX_PAGES):
        params = {"measure_code": measure_code,
                  "skip": page * PAGE_SIZE, "top": PAGE_SIZE}
        payload = get_json(f"{API_BASE}/flat-data-extract/{category_code}", params)
        batch = payload["result"]["data"]
        rows.extend(batch)
        if (page + 1) % 25 == 0 or len(batch) < PAGE_SIZE:
            log.info("%s/%s: page %d, %d rows so far",
                     category_code, measure_code, page + 1, len(rows))
        if len(batch) < PAGE_SIZE:   # a short page means we've reached the end
            return rows
        time.sleep(REQUEST_PAUSE_SECONDS)
    raise RuntimeError(f"{category_code}/{measure_code}: hit the MAX_PAGES safety limit")


def fetch_category(category_code: str) -> list[dict]:
    """Download every row of one category, one measure at a time."""
    rows: list[dict] = []
    for measure_code in get_measure_codes(category_code):
        rows.extend(fetch_measure(category_code, measure_code))
    log.info("%s: %d rows total", category_code, len(rows))
    return rows
