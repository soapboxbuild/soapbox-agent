#!/usr/bin/env bash
# Detached single-workflow rehearsal runner. Usage: run-one.sh <assetId> "<prompt>" <logtag>
set -euo pipefail
source "$(dirname "$0")/.demo.env"
ANON=$(grep -hE "SUPABASE_ANON_KEY|PUBLIC_SUPABASE_ANON" "$HOME/soapbox-platform/.env" | grep -oE "eyJ[A-Za-z0-9._-]+" | head -1)
API="https://soapbox-api-production.up.railway.app"; ORG="8ebc72a7-dca1-4cb1-be02-eed12f38340f"
TOKEN=$(python3 -c "import json,sys;print(json.dumps({'email':sys.argv[1],'password':sys.argv[2]}))" "$SOAPBOX_AGENT_EMAIL" "$SOAPBOX_AGENT_PASSWORD" | curl -s --max-time 20 "https://fplbvanvwvnviczozwhz.supabase.co/auth/v1/token?grant_type=password" -H "apikey: $ANON" -H "Content-Type: application/json" -d @- | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
CONV=$(curl -s --max-time 30 -X POST "$API/api/assets/$1/conversations" -H "Authorization: Bearer $TOKEN" -H "x-organization-id: $ORG" -H "Content-Type: application/json" -d "{\"title\":\"$3\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "CONV=$CONV" > "$HOME/.demo_run_$3.meta"
curl -s -N --max-time 1200 -X POST "$API/api/conversations/$CONV/messages" -H "Authorization: Bearer $TOKEN" -H "x-organization-id: $ORG" -H "Content-Type: application/json" -d "{\"content\":\"$2\"}" > "$HOME/.demo_run_$3.log" 2>&1
echo "DONE" >> "$HOME/.demo_run_$3.meta"
