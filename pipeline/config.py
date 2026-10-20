"""Central settings. Secrets come from environment variables (.env)."""
import os

API_BASE = "https://myhospitalsapi.aihw.gov.au/api/v1"

# MyHospitals measure categories to load (codes from /measure-categories)
CATEGORIES = [
    "MYH-ED",        # ED presentations
    "MYH-ED-WAITS",  # ED waiting times
    "MYH-ED-TIME",   # Time in ED
    "MYH-ES",        # Elective surgery
]

PAGE_SIZE = 1000              # the API's maximum rows per request
MAX_PAGES = 1000              # safety stop so a bug can never loop forever
REQUEST_PAUSE_SECONDS = 0.5   # be polite to a free public API
KEEP_VERSIONS = 2             # how many data versions to keep in the raw table


def db_dsn() -> str:
    """Connection string for Postgres, built from environment variables."""
    return (
        f"host={os.environ.get('DB_HOST', 'localhost')} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )
