#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

backend_port="$(printenv API_PORT || printf 8000)"
frontend_port="$(printenv FRONTEND_PORT || printf 3000)"
backend_pid=""
frontend_pid=""

cleanup() {
    [ -z "$backend_pid" ] || kill "$backend_pid" 2>/dev/null || true
    [ -z "$frontend_pid" ] || kill "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [ ! -x .venv/bin/python ] || [ ! -f nexus-saa-s-ai-platform/node_modules/next/dist/bin/next ]; then
    printf '%s\n' "Install the Python and Next.js dependencies before starting FloatChat." >&2
    exit 1
fi

.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port "$backend_port" &
backend_pid=$!
for (( attempt=0; attempt<30; attempt++ )); do
    if ! kill -0 "$backend_pid" 2>/dev/null; then
        printf '%s\n' "The backend exited during startup." >&2
        exit 1
    fi
    if curl --max-time 1 --fail --silent "http://127.0.0.1:$backend_port/api/v1/health" > /dev/null; then
        break
    fi
    sleep 1
done
if (( attempt == 30 )); then
    printf '%s\n' "The backend health check timed out." >&2
    exit 1
fi

cd nexus-saa-s-ai-platform
if ! printenv NEXT_PUBLIC_API_BASE_URL > /dev/null && ! printenv NEXT_PUBLIC_API_URL > /dev/null; then
    export NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$backend_port"
fi
node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port "$frontend_port" &
frontend_pid=$!
printf 'FloatChat http://127.0.0.1:%s · API http://127.0.0.1:%s/docs\n' "$frontend_port" "$backend_port"

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
    sleep 1
done
if ! kill -0 "$backend_pid" 2>/dev/null; then
    wait "$backend_pid"
else
    wait "$frontend_pid"
fi
