# Demo Staging — Index

Staging for the **Demo** org (`8ebc72a7-dca1-4cb1-be02-eed12f38340f`) → **Demo** portfolio (`3b683c32-…`) to run three sustainability workflows reliably on stage as real managed-agent runs.

## Workflows
| # | Workflow | Asset | Status | Runbook |
|---|----------|-------|--------|---------|
| 1 | RSRA (Aris) | 4400 Prairie Crossing (`062cbda3`) | ✅ validated (scripted replay; ~75s) | `runbook-rsra.md` |
| 2 | ESG Profile | Madison (`cece8ad8`) | ✅ validated post-v14 (renders `esg-profile` artifact; ~85s scripted replay) | `runbook-esg.md` |
| 3 | Decarb + Measure Ideation | 4th & Madison (`f6e043dd`) | ✅ validated (scripted replay; ~70s) | `runbook-decarb.md` |

## Key facts
- All names pseudonymized. Real-name denylist is untracked (`.scrub-denylist.json`); gate: `python3 demo-staging/scrub-check.py` (fail-closed).
- Service-account creds: untracked `demo-staging/.demo.env` (never commit).
- Decarb state persists to the **Files store** (folder `decarb-plan`), NOT the deprecated OpenWork worker workspace.
- fill_report template allowlist lives in `soapbox-platform/apps/api` (`agent-config.ts` enums + `managed-agents-runtime.ts` sets); `TOOLS_VERSION` bump busts cached agents.

## Pre-demo re-stage checklist
1. Fixtures committed + API deployed: verify `demo-fixtures/{rsra,esg,decarb}.json` are committed in `soapbox-platform/apps/api` and the API is running the latest build.
2. One E2E rehearsal per workflow on a fresh Demo-org thread the day before; keep the rendered artifacts as fallbacks.
3. `python3 demo-staging/scrub-check.py` → SCRUB CLEAN.
4. Confirm assets present + `[DEMO MODE]` prompts:
   `select name, system_prompt is not null from assets where portfolio_id='3b683c32-2514-…';` (RSRA + ESG have prompts; decarb prompt added after Christopher's run).
5. Re-stage Files if missing: `bash demo-staging/stage-files.sh` (idempotent — skips existing).

## Fallback artifacts (show if a live render stalls on stage)
- RSRA: artifact `86943ce4-783a-4605-894b-67027e0eae10` (asset `062cbda3`, thread `0db2286c`).
- ESG: artifact `d93af6dc-8fdc-41bd-ae31-5b2ba72cf816` (asset `cece8ad8`, thread `39b5efaf`).
- Decarb: TBD after the engagement run.

## Timing (scripted replay)
- **RSRA:** ~75s target (deterministic, scripted replay of a recorded run).
- **ESG:** ~85s target (deterministic, scripted replay of a recorded run).
- **Decarb:** ~70s target (deterministic, scripted replay of the completed engagement).
- All analysis phases are now fixed per fixture (deterministic replay), ensuring reliable on-stage timing. The only genuinely-live steps are upstream asset setup + final `fill_report` re-render.

## Fixture currency
- Fixtures live at `soapbox-platform/apps/api/src/services/demo-fixtures/{rsra,esg,decarb}.json`.
- Re-record (via `record-fixture.mjs`) or rebuild (via `build-fixture-from-run.mjs`) whenever the report template, skill output, or agent behavior changes materially.

## Scripts
- `stage-files.sh` — upload fixtures to the Files store (service-acct app API; sources `.demo.env`).
- `scrub-check.py` — fail-closed real-name scrub gate (PDF/XLSX/DOCX text extraction + word-boundary denylist).
