# Demo Portfolio Staging — Design

**Date:** 2026-07-11
**Owner:** Christopher
**Goal:** Make the "Demo" org on stage run three sustainability workflows **reliably** and with **snappy ~30–60 s turns** in front of a live audience, while still showing *real* workflows on the real product surface (Soapbox web app / managed agents).

---

## 1. Context & constraints (verified)

- **Runtime:** Soapbox web app, **managed-agent** threads. This is the customer-facing product surface — the demo runs *in the product*, not in a Claude Code session.
- **Environment:** the **"Demo"** org already exists.
  - org `8ebc72a7-dca1-4cb1-be02-eed12f38340f`
  - portfolio **"Demo"** `3b683c32-ea8e-4851-b350-fd7b85a60e2e`
  - asset **"4400 PRAIRIE CROSSING"** already present (RSRA asset).
  - DB: the app (prod + stage config) points at Supabase project `fplbvanvwvnviczozwhz`. Write path = Supabase MCP (`execute_sql` / `apply_migration`) + service-account app API. **Step 0 of implementation confirms whether stage is a branch of this ref.**
- **Hard platform facts driving the design:**
  - **Managed-agent skill bundles are FROZEN at install** per portfolio. We do **not** fork/patch skills for the demo; we re-sync the *current* bundle so the Demo portfolio has the latest, then rely on staged **state** + **helper files**.
  - Sessions are **ephemeral**; MCP tools have **timeouts** (heavy Audette writes need the higher timeout).
  - The **decarb render gate is HARD, fails-closed, and must never be gamed/bypassed** (skill rule). It reads **asset-scoped verifier findings** and requires a **verifier connector row** (`asset_connectors` plugin_verifier).

## 2. Non-negotiables

1. **Real workflows on the real surface.** We compress *time*, not honesty. Speed comes from pre-computed helper files and pre-staged state, not from faking the product.
2. **No gate-gaming, no skill code edits.** Gates pass because the analysis they check has *genuinely been done* and staged. (See §5.)
3. **Pseudonymize everything.** No real client/sponsor names or logos on stage. Real source files are **reference only** — never parsed live (their *contents* carry real identities; renaming a file does not scrub it).
4. **Idempotent, re-runnable staging.** Everything can be re-seeded cleanly before each demo.

## 3. The three workflows

One asset per workflow, one **minimal, workflow-scoped tool allowlist** per asset agent (limits tools → faster turns + failure isolation).

### 3.1 RSRA — asset "4400 Prairie Crossing" (pseudonym of Stoneweg deal)
- **Decision:** **Pre-stage the RSRA output; the OM drop is the visible trigger.**
- Live beat: user drops a **pseudonymous OM** → agent produces the RSRA report **served from staged state/helper files** (parse + lookups + CapEx are pre-computed). Render is the payoff.
- Reference source: `~/inbox/Prose Frontier OM.pdf` (used by *us* to author a clean, compact pseudonymous OM + the staged RSRA result). The real OM is never parsed on stage.
- Tool allowlist: RSRA render/report tools + the 1–2 MCPs the visible beat touches; slow lookups (BPS, benchmark, incentives) resolve from helper-file cache.

### 3.2 ESG Profile — sponsor "Madison" (pseudonymized)
- Reuse the existing **`esg-profile/demo`** runbook and fixture pattern verbatim, re-skinned to the "Madison" pseudonym.
- Live beats: **`crrem`** + **`physrisk`** calls (the visible gap-fillers). Everything else static (`static/*`).
- Reference source: `~/inbox/*ESG_DD_Report*` + `20251119 Madison - Watermark at Talbot Park.xlsx` → author pseudonymous `extract.xlsx`, `notes_scrubbed.docx`, `bps_cache.json`.
- Render ~60 s (accepted hero-turn cost for this workflow).

### 3.3 Decarb Plan + Measure Ideation — asset "4th & Madison" (pseudonym of JPMAM deal)
- **Decisions:** gates **auto-pass in demo mode via state-satisfaction** (hands-off); **Measure Ideation is surfaced as a visible on-screen beat**, then the plan renders.
- Pre-stage a **genuinely-completed engagement** to a gate-satisfied state:
  - asset + **building setup** (Audette property, equipment survey — all 10 groups, DHW sub-keys, null-not-zero per the equipment-survey schema),
  - **energy baseline** (calibrated),
  - **measures** (ideated set) + **cached economics** (gross + capture, landlord-share, solar VNM) + **cached costing** (Costing MCP results),
  - **resolved verifier findings + verifier connector row** at **asset scope** → render gate legitimately satisfied,
  - citations / provenance.
- Live run: agent **lists the ideated measures** (fast, from cached Audette results) → **renders the decarb plan** artifact. Hands-off but not opaque.
- Reference source: `~/inbox/4th and Madison.zip` (936 MB) — reference only, never parsed live.
- Tool allowlist: decarb render/report + measure surfacing tools; Audette/costing/verifier results served from staged state.

## 4. Cross-cutting staging mechanisms

- **Skill bundle re-sync:** confirm current soapbox-agent bundle version, re-sync to the Demo portfolio's `installed_plugins.skills` so it's the latest (bundle is frozen at install — must re-sync per portfolio).
- **Per-asset helper-file cache:** all slow external results staged as files/state the skills read — benchmarks, BPS, incentives, CRREM pathway, physrisk hazard, Audette model, costing. Live turns hit cache, not slow external calls.
- **Per-asset minimal tool allowlist:** each workflow agent sees only the MCPs its visible beat needs.
- **Anonymization pipeline:** author fresh pseudonymous fixtures from reference sources; reuse the ESG demo scrub denylist (`demo/.scrub-denylist.json`) + a **pre-go-live scrub gate** (`scrub-demo-data.mjs`-style) that fails closed if any real name leaks. Never stage un-scrubbed source.
- **Demo runbooks:** one runbook per workflow (exact prompt to type, expected beats, timing budget, fallback), same shape as the existing `esg-profile/demo/README.md`.

## 5. Why this is honest, not gaming

The gates verify that analysis was done to a provenance standard. We **do that analysis ahead of time** and stage its genuine artifacts (verifier findings resolved, connector row present, baseline/measures/economics real and reconciled). The live gate check passes because the work is actually complete — identical to how a real completed engagement would pass. We never (a) patch gate logic, (b) record-and-confirm a token finding to clear the gate, or (c) `save_file`-bypass a blocked render.

## 6. Reliability rails

- **Idempotent seed scripts** (check-first upserts) per asset, re-runnable before each demo.
- **Pre-flight rehearsal:** run all three end-to-end on stage once; confirm <60 s turns, gate passes, renders succeed.
- **Fallback artifacts:** keep the staged rendered outputs so a stalled live render can be shown from cache without breaking the demo.
- **Cleanup:** service-account test threads/records bulk-deleted after rehearsals (standing practice).

## 7. Out of scope

- No changes to production orgs/portfolios — **Demo org only**.
- No new skills or skill code changes; no new MCP servers.
- No real-name/logo display.

## 8. Open implementation questions (resolve during planning, not blockers)

1. Confirm stage vs prod: is the demo served from `fplbvanvwvnviczozwhz` directly or a branch? (Step 0.)
2. Exact mechanism by which RSRA/decarb skills pick up staged output vs re-running (helper-file hook vs pre-written asset state/report row) — determined per skill during planning.
3. Current installed skill-bundle version on the Demo portfolio vs latest soapbox-agent `main`.
