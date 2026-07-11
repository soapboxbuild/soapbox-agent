# Demo Staging — Index

Staging for the **Demo** org (`8ebc72a7-dca1-4cb1-be02-eed12f38340f`) → **Demo** portfolio (`3b683c32-…`) to run three sustainability workflows reliably on stage as real managed-agent runs.

## Workflows
| # | Workflow | Asset | Status | Runbook |
|---|----------|-------|--------|---------|
| 1 | RSRA (Aris) | 4400 Prairie Crossing (`062cbda3`) | ✅ validated | `runbook-rsra.md` |
| 2 | ESG Profile | Madison (`cece8ad8`) | fill_report enum fixed (v14); pre-computed-payload prompt; verifying | `runbook-esg.md` (pending) |
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

## Scripts
- `stage-files.sh` — upload fixtures to the Files store (service-acct app API).
- `run-one.sh <assetId> "<prompt>" <tag>` — detached single-workflow rehearsal (survives session teardown; logs to `~/.demo_run_<tag>.log`).
- `scrub-check.py` — fail-closed real-name scrub gate.
