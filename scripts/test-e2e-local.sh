#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
repo_dir="$PWD"
test_dir=$(mktemp -d /tmp/smartfind-e2e.XXXXXX)
api_pid='' ; web_pid=''
cleanup() { if [ -n "$web_pid" ]; then kill "$web_pid" 2>/dev/null || true; fi; if [ -n "$api_pid" ]; then kill "$api_pid" 2>/dev/null || true; fi; rm -rf "$test_dir"; }
trap cleanup EXIT
export DATABASE_URL="sqlite:///$test_dir/test.db" UPLOAD_DIR="$test_dir/uploads"
export ENVIRONMENT=development GEMINI_API_KEY='' ENABLE_LOCAL_MODELS=false
export CORS_ORIGINS=http://127.0.0.1:13000 BACKEND_ORIGIN=http://127.0.0.1:18000
export BASE_URL=http://127.0.0.1:13000 API_ORIGIN=http://127.0.0.1:18000
export ADMIN_EMAIL=admin@example.edu ADMIN_PASSWORD=LocalAdminDemo123!
if command -v chromium >/dev/null 2>&1; then export CHROMIUM_PATH="$(command -v chromium)"; fi
export SMARTFIND_TEST_CREDENTIALS="$test_dir/admin.json"
python_bin="$repo_dir/.venv/bin/python"
(cd backend && "$python_bin" -m alembic upgrade head)
"$python_bin" scripts/seed_demo.py > "$test_dir/seed.log"
printf '{"email":"admin@example.edu","password":"LocalAdminDemo123!"}' > "$SMARTFIND_TEST_CREDENTIALS"
"$python_bin" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18000 > "$test_dir/api.log" 2>&1 & api_pid=$!
cd frontend
npm run build
node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 13000 > "$test_dir/web.log" 2>&1 & web_pid=$!
for attempt in $(seq 1 30); do
  if curl --noproxy '*' -fsS "$BASE_URL" >/dev/null 2>&1; then break; fi
  sleep 1
done
npm run test:e2e
