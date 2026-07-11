#!/usr/bin/env bash
# Stage demo fixtures into the Files store (asset document library) via the
# service-account app API, so the managed agents read them at run time.
# Idempotent-ish: skips a file if one with the same name already exists on the asset.
set -euo pipefail

API="https://soapbox-api-production.up.railway.app"
ORG="8ebc72a7-dca1-4cb1-be02-eed12f38340f"
SUPA="https://fplbvanvwvnviczozwhz.supabase.co"
AGENT_DIR="$HOME/soapbox-agent"

ANON=$(grep -hE "SUPABASE_ANON_KEY|PUBLIC_SUPABASE_ANON" "$HOME/soapbox-platform/.env" 2>/dev/null | grep -oE "eyJ[A-Za-z0-9._-]+" | head -1)
TOKEN=$(curl -s --max-time 20 "$SUPA/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON" -H "Content-Type: application/json" \
  -d '{"email":"claude@agents.soapbox.build","password":"SOURCED_FROM_ENV"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] || { echo "AUTH FAIL"; exit 1; }

# asset-files bucket allows: pdf, text/plain, text/csv, docx, xlsx, pptx, images, html (NOT json)
mime_for() { case "$1" in
  *.pdf) echo application/pdf;;
  *.xlsx) echo application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;;
  *.docx) echo application/vnd.openxmlformats-officedocument.wordprocessingml.document;;
  *.json|*.txt) echo text/plain;;   # json uploaded as text/plain (bucket rejects application/json)
  *) echo text/plain;; esac; }

upload() { # assetId path folder
  local asset="$1" path="$2" folder="$3" name mime
  name=$(basename "$path"); mime=$(mime_for "$name")
  local existing
  existing=$(curl -s --max-time 20 "$API/api/assets/$asset/files" \
    -H "Authorization: Bearer $TOKEN" -H "x-organization-id: $ORG" \
    | python3 -c "import sys,json;print(sum(1 for f in json.load(sys.stdin) if f.get('name')=='$name'))" 2>/dev/null || echo 0)
  if [ "$existing" != "0" ]; then echo "  skip (exists): $name"; return; fi
  curl -s --max-time 60 -X POST "$API/api/assets/$asset/files" \
    -H "Authorization: Bearer $TOKEN" -H "x-organization-id: $ORG" \
    -F "file=@$path;type=$mime" -F "folder=$folder" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print('  uploaded:', d.get('name'), d.get('id',d))" 2>/dev/null \
    || echo "  UPLOAD FAIL: $name"
}

RSRA_ASSET="062cbda3-aa2a-414b-8f48-aa61c5b69ad4"
ESG_ASSET="cece8ad8-37ee-430e-98d1-0046266674db"

echo "== RSRA (4400 Prairie Crossing) =="
upload "$RSRA_ASSET" "$AGENT_DIR/skills/rsra/demo/om_4400_prairie_crossing.pdf" "Deal Documents"
upload "$RSRA_ASSET" "$AGENT_DIR/skills/rsra/demo/rsra_data.json" "Demo Staging"
upload "$RSRA_ASSET" "$AGENT_DIR/skills/rsra/demo/physrisk_cache.json" "Demo Staging"
upload "$RSRA_ASSET" "$AGENT_DIR/skills/rsra/demo/bps_cache.json" "Demo Staging"

echo "== ESG (Madison) =="
upload "$ESG_ASSET" "$AGENT_DIR/skills/esg-profile/demo/madison/extract.xlsx" "ESG Inputs"
upload "$ESG_ASSET" "$AGENT_DIR/skills/esg-profile/demo/madison/notes_scrubbed.docx" "ESG Inputs"
upload "$ESG_ASSET" "$AGENT_DIR/skills/esg-profile/demo/madison/bps_cache.json" "ESG Inputs"
upload "$ESG_ASSET" "$AGENT_DIR/skills/esg-profile/demo/madison/example-sponsor.json" "Demo Staging"

echo "DONE"
