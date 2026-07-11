# Demo Staging — Index

Staging for the **Demo** org (`8ebc72a7-dca1-4cb1-be02-eed12f38340f`) → **Demo** portfolio (`3b683c32-…`) to run three sustainability workflows reliably on stage as real managed-agent runs.

## Workflows
| # | Workflow | Asset | Status | Runbook |
|---|----------|-------|--------|---------|
| 1 | RSRA (Aris) | 4400 Prairie Crossing (`062cbda3`) | ✅ validated | `runbook-rsra.md` |
| 2 | ESG Profile | Madison (`cece8ad8`) | ✅ validated post-v14 (renders `esg-profile` artifact; ~5min, speed-polish pending) | `runbook-esg.md` |
| 3 | Decarb + Measure Ideation | 4th & Madison (`f6e043dd`) | inputs staged; Christopher runs the engagement, then demo resumes from Files | `runbook-decarb.md` (pending) |

## Key facts
- All names pseudonymized. Real-name denylist is untracked (`.scrub-denylist.json`); gate: `python3 demo-staging/scrub-check.py` (fail-closed).
- Service-account creds: untracked `demo-staging/.demo.env` (never commit).
- Decarb state persists to the **Files store** (folder `decarb-plan`), NOT the deprecated OpenWork worker workspace.
- fill_report template allowlist lives in `soapbox-platform/apps/api` (`agent-config.ts` enums + `managed-agents-runtime.ts` sets); `TOOLS_VERSION` bump busts cached agents.

## Pre-demo re-stage checklist
1. `python3 demo-staging/scrub-check.py` → SCRUB CLEAN.
2. Confirm assets present + `[DEMO MODE]` prompts:
   `select name, system_prompt is not null from assets where portfolio_id='3b683c32-2514-…';` (RSRA + ESG have prompts; decarb prompt added after Christopher's run).
3. Re-stage Files if missing: `bash demo-staging/stage-files.sh` (idempotent — skips existing).
4. One smoke of each workflow (fresh thread) the day before; keep the rendered artifacts as fallbacks.

## Fallback artifacts (show if a live render stalls on stage)
- RSRA: artifact `86943ce4-783a-4605-894b-67027e0eae10` (asset `062cbda3`, thread `0db2286c`).
- ESG: artifact `d93af6dc-8fdc-41bd-ae31-5b2ba72cf816` (asset `cece8ad8`, thread `39b5efaf`).
- Decarb: TBD after the engagement run.

## Timing observed (rehearsals)
- RSRA ~168s to rendered artifact (with live narration). ESG ~314s (live crrem+physrisk + render).
- Both exceed the 30–60s/turn target; they stream narration so the audience sees continuous progress. For strict snappiness, pre-stage more of the computed output (RSRA-style) and tighten the `[DEMO MODE]` prompt further.

## Scripts
- `stage-files.sh` — upload fixtures to the Files store (service-acct app API; sources `.demo.env`).
- `scrub-check.py` — fail-closed real-name scrub gate (PDF/XLSX/DOCX text extraction + word-boundary denylist).
