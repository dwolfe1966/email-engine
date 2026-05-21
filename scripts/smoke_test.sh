#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
CONTACT_EMAIL="${CONTACT_EMAIL:-smoke-test@example.com}"
STAMP="$(date +%s)"

echo "Checking health..."
curl -fsS "$BASE_URL/health" >/dev/null

echo "Checking readiness..."
curl -fsS "$BASE_URL/ready" >/dev/null

echo "Creating template..."
template_response="$(
  curl -fsS "$BASE_URL/api/v1/templates" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "smoke-test-'"$STAMP"'",
      "subject": "Hello {{ first_name }}",
      "html_body": "<p>Hello {{ first_name }}</p>",
      "text_body": "Hello {{ first_name }}"
    }'
)"
template_id="$(
  TEMPLATE_RESPONSE="$template_response" python3 -c 'import json, os; print(json.loads(os.environ["TEMPLATE_RESPONSE"])["id"])'
)"

echo "Upserting contact..."
contact_response="$(
  curl -fsS "$BASE_URL/api/v1/audiences/contacts" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$CONTACT_EMAIL\",
      \"first_name\": \"Smoke\",
      \"last_name\": \"Test\",
      \"source\": \"smoke_test\",
      \"attributes\": {}
    }"
)"
contact_id="$(
  CONTACT_RESPONSE="$contact_response" python3 -c 'import json, os; print(json.loads(os.environ["CONTACT_RESPONSE"])["id"])'
)"

echo "Generating unsubscribe token..."
curl -fsS -X POST "$BASE_URL/api/v1/audiences/contacts/$contact_id/unsubscribe-token" >/dev/null

echo "Sending contact email..."
curl -fsS "$BASE_URL/api/v1/send/contact" \
  -H "Content-Type: application/json" \
  -d "{
    \"template_id\": \"$template_id\",
    \"contact_id\": \"$contact_id\",
    \"variables\": {\"first_name\": \"Smoke\"}
  }" >/dev/null

echo "Sending console test email..."
curl -fsS "$BASE_URL/api/v1/send/test" \
  -H "Content-Type: application/json" \
  -d "{
    \"template_id\": \"$template_id\",
    \"to_email\": \"$CONTACT_EMAIL\",
    \"variables\": {\"first_name\": \"Smoke\"}
  }" >/dev/null

echo "Smoke test passed."
