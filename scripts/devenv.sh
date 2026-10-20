# Usage, from the repo root:  source scripts/devenv.sh
set -a; source .env; set +a
export DB_HOST=localhost        # outside Docker, the database is on localhost
source .venv/bin/activate
echo "Dev environment ready (DB_HOST=$DB_HOST)"
