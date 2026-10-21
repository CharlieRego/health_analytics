"""Pipeline entry point: ingest -> dbt build -> (optional) ML -> status file."""
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg

from .config import db_dsn
from .ingest import run_ingest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("pipeline")

DBT_CMD = ["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"]
RUN_RESULTS = Path("dbt/target/run_results.json")
STATUS_FILE = Path("status/status.json")


def run_dbt(conn, run_id: str) -> bool:
    """Run dbt models and tests, then save the results. True if nothing failed."""
    from .dbt_audit import record_dbt_results   # created on Module 7
    RUN_RESULTS.unlink(missing_ok=True)          # never record a stale result
    result = subprocess.run(DBT_CMD)
    record_dbt_results(conn, run_id, RUN_RESULTS)
    return result.returncode == 0


def write_status(conn, run_id: str) -> None:
    """Write a small public summary of this run (used by the resume site on Module 13)."""
    run = conn.execute(
        """select status, started_at, finished_at, rows_loaded, data_version
           from audit.pipeline_runs where run_id = %s""",
        (run_id,),
    ).fetchone()
    tests = conn.execute(
        """select count(*) filter (where status = 'pass'),
                  count(*) filter (where status = 'warn'),
                  count(*) filter (where status in ('fail', 'error')),
                  count(*)
           from audit.dbt_results
           where run_id = %s and resource_type = 'test'""",
        (run_id,),
    ).fetchone()
    summary = {
        "status": run[0],
        "started_at": run[1].isoformat(),
        "finished_at": run[2].isoformat() if run[2] else None,
        "new_rows_loaded": run[3],
        "source_data_version": run[4],
        "tests_passed": tests[0],
        "tests_warned": tests[1],
        "tests_failed": tests[2],
        "tests_total": tests[3],
    }
    STATUS_FILE.parent.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps(summary, indent=2))


def main() -> int:
    skip_dbt = "--skip-dbt" in sys.argv
    run_id = str(uuid.uuid4())
    # rows stays None if ingest fails; ingest has already saved partial progress
    rows, status, message, exit_code = None, "success", None, 0

    with psycopg.connect(db_dsn(), autocommit=True) as conn:
        conn.execute("insert into audit.pipeline_runs (run_id) values (%s)", (run_id,))
        try:
            rows = run_ingest(conn, run_id)
            if not skip_dbt and not run_dbt(conn, run_id):
                status, exit_code = "tests_failed", 2
                message = "dbt build failed - see marts.rpt_data_quality"
            if status == "success" and os.environ.get("ML_ENABLED") == "1":
                from .ml_expected import run_model   # created on Module 11
                run_model(conn)
        except Exception as exc:
            log.exception("Pipeline failed")
            status, message, exit_code = "failed", str(exc)[:1000], 1

        conn.execute(
            """update audit.pipeline_runs
               set status = %s, finished_at = now(),
                   rows_loaded = coalesce(%s, rows_loaded, 0), message = %s
               where run_id = %s""",
            (status, rows, message, run_id),
        )
        write_status(conn, run_id)

    log.info("Run %s finished: status=%s, new rows=%s", run_id, status, rows)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
