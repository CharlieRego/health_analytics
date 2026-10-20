"""Load raw API rows into Postgres. Safe to re-run: each data version loads once."""
import json
import logging

from .config import CATEGORIES, KEEP_VERSIONS
from .extract import fetch_category, get_version_info

log = logging.getLogger(__name__)

PRUNE_OLD_VERSIONS_SQL = """
delete from raw.myh_flat r
using (
    select measure_category_code, data_version
    from (
        select measure_category_code, data_version,
               dense_rank() over (partition by measure_category_code
                                  order by data_version desc) as rnk
        from audit.source_loads
    ) v
    where rnk > %s
) old
where r.measure_category_code = old.measure_category_code
  and r.data_version = old.data_version
"""


def already_loaded(conn, category: str, data_version: int) -> bool:
    row = conn.execute(
        "select 1 from audit.source_loads "
        "where measure_category_code = %s and data_version = %s",
        (category, data_version),
    ).fetchone()
    return row is not None


def load_category(conn, run_id: str, category: str, version: dict) -> int:
    """Fetch one category and bulk-load it in a single transaction."""
    rows = fetch_category(category)
    with conn.transaction():          # all of it loads, or none of it does
        with conn.cursor() as cur:
            with cur.copy(
                "copy raw.myh_flat (run_id, measure_category_code, data_version, record) "
                "from stdin"
            ) as copy:
                for record in rows:
                    copy.write_row((run_id, category, version["data_version"], json.dumps(record)))
            cur.execute(
                """insert into audit.source_loads
                       (measure_category_code, data_version, run_id, date_uploaded, rows_loaded)
                   values (%s, %s, %s, %s, %s)""",
                (category, version["data_version"], run_id,
                 version.get("date_uploaded"), len(rows)),
            )
    return len(rows)


def run_ingest(conn, run_id: str) -> int:
    """Load every category that has new data. Returns the number of new rows."""
    version = get_version_info()
    log.info("API data_version=%s, uploaded %s",
             version["data_version"], version.get("date_uploaded"))
    conn.execute(
        "update audit.pipeline_runs set data_version = %s where run_id = %s",
        (version["data_version"], run_id),
    )

    total = 0
    for category in CATEGORIES:
        if already_loaded(conn, category, version["data_version"]):
            log.info("%s: this data version is already loaded, skipping", category)
            continue
        n = load_category(conn, run_id, category, version)
        log.info("%s: loaded %d rows", category, n)
        total += n

    deleted = conn.execute(PRUNE_OLD_VERSIONS_SQL, (KEEP_VERSIONS,)).rowcount
    if deleted:
        log.info("Pruned %d raw rows from old data versions", deleted)
    return total
