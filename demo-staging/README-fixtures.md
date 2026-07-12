# Fixture Recording & Validation Workflow

This directory contains tooling to record, scrub, validate, and commit golden-run fixtures for demo-scripted-replay.

## Prerequisites

Before first use, install the recorder's one dependency (`@supabase/supabase-js`) from this directory:

```bash
cd demo-staging && npm install   # or: bun install
```

## Required Environment Variables

To run the fixture recorder, you must source `.demo.env` and set the following:

- `SOAPBOX_AGENT_EMAIL` — service account email (e.g., `claude@agents.soapbox.build`)
- `SOAPBOX_AGENT_PASSWORD` — service account password (from Vaultwarden)
- `DEMO_API_HOST` — stage app API endpoint (e.g., `https://api.stage.soapbox.build`)
- `SUPABASE_URL` — Supabase project URL (e.g., `https://xyz.supabase.co`)
- `SUPABASE_ANON_KEY` — Supabase anon key (for public auth flows)

Example:
```bash
source .demo.env
export DEMO_API_HOST="https://api.stage.soapbox.build"
export SUPABASE_URL="https://xyz.supabase.co"
export SUPABASE_ANON_KEY="eyJ..."
```

## Recording Workflow

### Step 1: Record a Fixture

The `record-fixture.mjs` script runs a real agent against the Demo org, captures the SSE event stream with relative timestamps, and extracts the render payload.

**Important constraint:** The recorder targets **ONLY** the Demo-org asset (org ID: `8ebc72a7-dca1-4cb1-be02-eed12f38340f`). All API calls are made with `x-organization-id` set to this org.

```bash
node record-fixture.mjs \
  --workflow rsra \
  --asset 062cbda3-<demo-asset-id> \
  --prompt "Run a Rapid Sustainability Risk Assessment on 4400 Prairie Crossing. The OM is in the deal folder." \
  --target-ms 75000 \
  --out fixtures/rsra.json
```

**Output:**
- Writes a fixture JSON to `--out` (default: `fixtures/{workflow}.json`) with schema:
  ```json
  {
    "workflow": "rsra",
    "version": 1,
    "targetDurationMs": 75000,
    "recordedTotalMs": 62341,
    "events": [
      { "t": 123, "event": { "type": "...", ... } },
      ...
    ],
    "render": {
      "template": "rsra",
      "title": "Risk Assessment: 4400 Prairie Crossing",
      "data": { ... }
    }
  }
  ```
- Prints to stderr the conversation ID (for cleanup) and event count

### Step 2: Scrub Sensitive Data

The `.scrub-denylist.json` defines PII/secrets to strip from the fixture. `scrub-check.py`
scans the default fixture roots (`SCAN_DIRS`) when called with no arguments — pass the
fixture's actual path(s) to scan those instead (files or directories, recursively):

```bash
python3 demo-staging/scrub-check.py fixtures/rsra.json
```

This validates the fixture against the denylist and exits non-zero (fail-closed) on any
leaked term or an empty denylist. Use the existing `stage-files.sh` or manual edit to remove:
- Email addresses
- Tenant/API keys
- Internal IDs (except Demo-org reference)
- Personally identifying information

### Step 3: Validate Fixture Schema

Ensure the fixture matches the `DemoFixture` contract expected by Task 2 (platform replay engine). The schema requires:
- `workflow`: string (workflow name)
- `version`: number (fixture schema version, currently 1)
- `targetDurationMs`: number (expected run duration)
- `recordedTotalMs`: number (actual elapsed time in recording)
- `events`: array of `{ t: number, event: {...} }` with monotonic `t` (ms since first byte)
- `render`: object with `{ template, title, data }` — the payload for `fill_report` tool

The script validates:
- No `data` in event-stream `tool_call` markers (only `{ template }` survives in events[])
- `render` contains the full `data` exactly once
- All timestamps are monotonically increasing
- Required fields present

### Step 4: Commit the fixture into the API repo

Fixtures are **committed build-time assets**, not database rows. The platform loads
them with `readFileSync` from `apps/api/src/services/demo-fixtures/<workflow>.json`
(see `loadDemoFixture` in `apps/api/src/services/demo-replay.ts`). There is no
`/api/fixtures` endpoint and no `fixtures` table — copy the scrubbed, validated JSON
into that path in the `soapbox-platform` repo and commit it:

```bash
cp /tmp/rsra.json ~/soapbox-platform/apps/api/src/services/demo-fixtures/rsra.json
cd ~/soapbox-platform
git add apps/api/src/services/demo-fixtures/rsra.json
git commit -m "feat(demo): freeze verified rsra golden-run fixture"
```

The fixture takes effect on the next API deploy. `<workflow>` is one of `rsra`, `esg`, `decarb`.

## Cleanup: Delete Throwaway Conversations

The recorder creates a temporary conversation in the Demo org. Record its ID from stderr and clean up afterward to keep the org tidy:

```bash
# Using Supabase MCP (requires connected MCP server):
# Filter: organization_id = '8ebc72a7-dca1-4cb1-be02-eed12f38340f'
# Delete conversation rows with the recorded conversation ID

# Or via SQL:
# DELETE FROM conversations WHERE id = '<conv-id>' AND organization_id = '8ebc72a7-dca1-4cb1-be02-eed12f38340f'
```

Use the standard `cleanup-test-data` process defined in the Soapbox platform memory.

---

## References

- **Task 2 (Platform Replay Engine):** Consumes and validates `DemoFixture` schema
- **Task 5 (This recorder):** Produces fixtures conforming to the schema
- **Task 6 (RSRA render gate):** Must have a clean render before Step 2 of Task 5 (smoke-run) is gated
- **.superpowers/sdd/:** Task briefs and implementation guides
