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


def get_json(url: str, params: dict | None = None, retries: int = 3) -> dict:
    """GET a URL and return its JSON, retrying with a growing wait on failure."""
    for attempt in range(1, retries + 1):
        try:
            resp = _session.get(url, params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)


def get_version_info() -> dict:
    """Return the API's version_information block (contains data_version)."""
    return get_json(f"{API_BASE}/measure-categories")["version_information"]


def fetch_category(category_code: str) -> list[dict]:
    """Download every row of one measure category, 1,000 rows at a time."""
    rows: list[dict] = []
    for page in range(MAX_PAGES):
        payload = get_json(
            f"{API_BASE}/flat-data-extract/{category_code}",
            params={"skip": page * PAGE_SIZE, "top": PAGE_SIZE},
        )
        batch = payload["result"]["data"]
        rows.extend(batch)
        log.info("%s: page %d -> %d rows", category_code, page + 1, len(batch))
        if len(batch) < PAGE_SIZE:   # a short page means we've reached the end
            return rows
        time.sleep(REQUEST_PAUSE_SECONDS)
    raise RuntimeError(f"{category_code}: hit the MAX_PAGES safety limit")
