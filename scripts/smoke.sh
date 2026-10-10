#!/usr/bin/env bash
# Posts every sample request to the n8n webhook and pretty-prints the ticket that comes back.
set -euo pipefail
cd "$(dirname "$0")/.."

N8N_URL="${N8N_URL:-http://localhost:5678}"
WEBHOOK="$N8N_URL/webhook/support-triage"

echo "Waiting for n8n at $N8N_URL ..."
for i in $(seq 1 60); do
  if curl -fsS "$N8N_URL/healthz/readiness" >/dev/null 2>&1; then break; fi
  if [ "$i" -eq 60 ]; then echo "n8n is not reachable. Is 'docker compose up -d' running?"; exit 1; fi
  sleep 2
done

failed=0
for sample in samples/*.json; do
  echo
  echo "=== $(basename "$sample" .json)"
  echo "--- request"
  python3 -m json.tool "$sample"
  echo "--- ticket"
  if ! response="$(curl -sS --max-time 180 -X POST -H 'Content-Type: application/json' --data @"$sample" "$WEBHOOK")"; then
    echo "Request failed"; failed=1; continue
  fi
  if ! printf '%s' "$response" | python3 -c 'import json, sys; d = json.load(sys.stdin); assert "ticket_id" in d, d; print(json.dumps(d, indent=2))'; then
    echo "Unexpected response: $response"; failed=1
  fi
done
exit "$failed"
