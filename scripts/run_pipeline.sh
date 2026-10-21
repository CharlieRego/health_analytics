#!/usr/bin/env bash
# Weekly pipeline run, called by cron. Pings Healthchecks.io with the result.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

ping() {
    if [ -n "${HEALTHCHECK_URL:-}" ]; then
        curl -fsS -m 10 --retry 3 "${HEALTHCHECK_URL}$1" > /dev/null || true
    fi
}

echo "=== Run started $(date -Is) ==="
if docker compose run --rm pipeline; then
    echo "=== Run finished OK $(date -Is) ==="
    ping ""
else
    echo "=== Run FAILED $(date -Is) ==="
    ping "/fail"
    exit 1
fi
