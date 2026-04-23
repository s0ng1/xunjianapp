#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

wait_for_service_health() {
  local service="$1"
  local container_id=""
  local status=""

  echo "Waiting for ${service} to become healthy..."

  for _ in $(seq 1 60); do
    container_id="$(docker compose ps -q "${service}")"
    if [[ -n "${container_id}" ]]; then
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"
      if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
        echo "${service} is ${status}"
        return 0
      fi
      if [[ "${status}" == "exited" || "${status}" == "dead" ]]; then
        echo "${service} entered state ${status}"
        docker compose logs --tail=200 "${service}" || true
        return 1
      fi
    fi
    sleep 2
  done

  echo "Timed out waiting for ${service}; last status=${status:-unknown}"
  docker compose logs --tail=200 "${service}" || true
  return 1
}

check_http() {
  local name="$1"
  local url="$2"

  echo "Checking ${name}: ${url}"
  curl --silent --show-error --fail --max-time 10 "${url}" > /dev/null
}

echo "Starting compose stack..."
docker compose up -d --build

wait_for_service_health db
wait_for_service_health backend
wait_for_service_health frontend

check_http "backend health" "http://127.0.0.1:${BACKEND_PORT}/health"
check_http "backend readiness" "http://127.0.0.1:${BACKEND_PORT}/ready"
check_http "frontend home" "http://127.0.0.1:${FRONTEND_PORT}/"

echo "Running backend pytest inside container (SQLite fast suite)..."
docker compose exec -T backend pytest -m "not postgres_integration"

echo "Running backend PostgreSQL integration tests inside container..."
docker compose exec -T -e RUN_POSTGRES_INTEGRATION=1 backend pytest -m postgres_integration

echo "Running frontend typecheck inside container..."
docker compose exec -T frontend npm run typecheck

echo "Running asset lifecycle smoke flow..."
docker compose exec -T backend python - <<'PY'
import json
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
asset_ip = f"198.51.100.{int(time.time()) % 200 + 1}"
create_payload = {
    "ip": asset_ip,
    "type": "linux",
    "name": "phase1-smoke-asset",
}


def request(method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read()
        if not body:
            return response.status, None
        return response.status, json.loads(body)


status, created = request("POST", "/api/v1/assets", create_payload)
assert status == 201, status
assert created is not None and created["ip"] == asset_ip
asset_id = created["id"]

status, assets = request("GET", "/api/v1/assets")
assert status == 200, status
assert any(item["id"] == asset_id for item in assets), assets

status, _ = request("DELETE", f"/api/v1/assets/{asset_id}")
assert status == 204, status

print("Smoke flow passed for asset", asset_id)
PY

echo "Phase 1 acceptance completed."
