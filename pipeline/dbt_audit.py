"""Save dbt model and test results into audit.dbt_results."""
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def record_dbt_results(conn, run_id: str, run_results: Path) -> None:
    if not run_results.exists():
        log.warning("No %s found - dbt may have failed before running anything", run_results)
        return

    data = json.loads(run_results.read_text())
    invocation_id = data["metadata"]["invocation_id"]
    rows = [
        (
            run_id,
            invocation_id,
            r["unique_id"],
            r["unique_id"].split(".")[0],   # "model", "test" or "seed"
            r["status"],
            r.get("failures"),
            (r.get("message") or "")[:1000],
            r.get("execution_time"),
        )
        for r in data["results"]
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """insert into audit.dbt_results
                   (run_id, invocation_id, unique_id, resource_type, status,
                    failures, message, execution_time)
               values (%s, %s, %s, %s, %s, %s, %s, %s)""",
            rows,
        )
    log.info("Recorded %d dbt results", len(rows))
