# Demo Runbook — RSRA (Aris) on 4400 Prairie Crossing

**Status:** ✅ Validated end-to-end on stage (thread `0db2286c`, artifact "4400 Prairie Crossing — RSRA", ~168s).

## Setup (staged)
- Org: **Demo** (`8ebc72a7-…`) → portfolio **Demo** → asset **4400 PRAIRIE CROSSING** (`062cbda3-…`, Denver CO, multifamily, 2006).
- Files on asset: `om_4400_prairie_crossing.pdf` (Deal Documents), `rsra_data.json` + `physrisk_cache.json` + `bps_cache.json` (Demo Staging).
- Asset `system_prompt` = `[DEMO MODE — 4400 Prairie Crossing]` (uses the pre-computed payload; physrisk stays live; renders via fill_report).

## On stage (what you do)
1. Open the Demo org → 4400 Prairie Crossing → **new thread**.
2. Type: **"Run a Rapid Sustainability Risk Assessment on 4400 Prairie Crossing. The OM is in the deal folder."**
3. Watch the agent: locate the OM → read it → (live physrisk hazard/VaR beat) → render the branded RSRA report.

## Expected beats (~2–3 min total, streaming)
- "Reading the offering memorandum…" (finds `om_4400_prairie_crossing.pdf`)
- Live physrisk call (hero) — hazard table + Climate VaR populate
- `fill_report(rsra)` → branded artifact renders in the right pane.

## Hero live calls
- **physrisk** (Phase 4) — the genuinely dynamic beat.
- **fill_report(rsra)** — the render.

## Fallback
- If a live render stalls: the validated artifact from thread `0db2286c` is on the asset — open it from the artifacts pane / Files.

## Notes
- Numbers obey kWh/m², ≤2 sig figs, peer benchmarks. Pseudonymous (Stonebridge Capital / Denver relocation) — real names never appear (scrub gate: `python3 demo-staging/scrub-check.py`).
