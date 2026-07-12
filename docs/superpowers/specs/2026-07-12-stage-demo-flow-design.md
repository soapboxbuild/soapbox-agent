# Stage Demo Flow — Reliable Scripted Replay Across the Three Workflows

**Date:** 2026-07-12
**Status:** Design (approved in brainstorming; pending spec review → writing-plans)
**Builds on:** `2026-07-11-demo-portfolio-staging-design.md`, `demo-staging/` (README + three runbooks)

## Problem

We want to present a blank-slate → finished-deliverable demo on stage where the *upstream* setup is genuinely live, but the expensive analysis lands **fully rendered within a fixed ~1–2 minute window** (while the presenter is on a flowchart slide).

The narrative the presenter drives:

> blank screen → **Add asset** → drop the OM → map loads instantly → select footprints → link Audette → open a thread → type a rapid prompt → some agent activity → flip to a flowchart slide for 1–2 min → return, and the report is **totally rendered**.

Real runs don't fit that window: a genuine RSRA is ~10–45 min, and even today's `[DEMO MODE]` runs are variable (RSRA ~168s, ESG ~314s) and depend on live model turns and live MCP calls (physrisk, crrem) that can stall or drift on stage. **Variability is the enemy** — a stage demo must be deterministic and rehearsable.

Decision (brainstorming): **scripted demo mode** — a rehearsable replay that *feels* real and is *built from real material*, but is reliable and fast. Applies to **all three** demos: RSRA, ESG Profile, Decarb.

## Non-negotiable constraints

- **Feel real, from real material.** The replay plays back the *actual recorded events* of a real, verified run — not fabricated narration. It looks 100% real because it is.
- **Reliable + fast.** Deterministic timeline, comfortably inside the slide window. No live model/MCP dependency in the analysis phase.
- **Demo-org scoped only.** All behavior gated to the Demo org (`8ebc72a7-dca1-4cb1-be02-eed12f38340f`), never reachable by real tenants.
- **Shared write DB is prod+stage.** Supabase ref `fplbvanvwvnviczozwhz` backs **both** prod and stage. Every fixture/seed write MUST be filtered to the Demo org/portfolio. This is a hard rule, not a guideline.
- **Scrub gate.** Recorded narration is new textual content → must pass `demo-staging/scrub-check.py` (fail-closed) before a fixture is frozen. Pseudonyms only; real names never appear.
- **Upstream stays live.** Add-asset, OM drop, instant map, footprint select, Audette link, open thread all run for real (already built).

## Architecture — four units

### Unit A — Org-scoped demo mode (enables live "Add asset")

Today `[DEMO MODE]` is attached per-asset via `system_prompt` on the three pre-staged assets. But the stage flow adds the asset **live from blank**, and a freshly created asset has no prompt or fixture. So promote demo mode from per-asset to **org-scoped**, reusing the exact pattern already proven by the onboarding modal's Demo-org instant-map override (`platform-web/src/components/app/AssetOnboardingModal.tsx`, `DEMO_ORG_ID`, `DEMO_FOOTPRINT`).

- Any asset created in the Demo org auto-enters demo mode.
- The workflow is identified from the prompt the presenter types (RSRA / ESG / decarb), mapping to the matching fixture (Unit B).
- Zero behavior change for real orgs — the branch is unreachable outside the Demo org id.

**Interface:** a single `isDemoOrg(orgId)` predicate + a workflow-intent classifier (prompt → `{rsra|esg|decarb}`), shared by the runtime branch (Unit C). Depends on: the Demo org id constant (already exists client-side; add the server-side equivalent).

### Unit B — Recorded golden-run fixtures + scrub gate (the "if this one works" gate)

**The demo *is* the fixture.** For each workflow we record ONE verified-clean run and freeze it as the replay source. Two fixture shapes:

1. **Replay shape** — RSRA, ESG. Capture the run's full ordered event stream (agent narration deltas + tool-call markers) *and* the terminal `fill_report` payload. The recording is the deliverable timeline.
2. **Present-completed shape** — Decarb. The engagement itself is long, interactive, and gated — not something to replay turn-by-turn. Instead, Christopher runs the real engagement once to produce completed state + a rendered plan in the Files store; the fixture is a **short** recorded "walk me through the plan" run (surface the ideated measures → display the already-rendered decarb artifact).

Each fixture must reflect the **current** verified output — this is exactly where "if this one works" bites:

| Workflow | Fixture asset | Must reflect | Gate status |
|---|---|---|---|
| RSRA | 4400 Prairie Crossing (`062cbda3`) | separated VaR block (cumulative $ vs annual %/yr), stepped/distinct decarb_sensitivity, Cambium grid factor, sane measure sizing | **BLOCKED** on one clean render (existing fallback `86943ce4` predates the fixes) |
| ESG | Madison (`cece8ad8`) | live-crrem/physrisk gap-fills baked into the recording (so neither needs to be live on stage); reconciled scorecard | Re-record after RSRA pattern proven |
| Decarb | 4th & Madison (`f6e043dd`) | completed engagement state + rendered plan in Files (Christopher's one real run) | **BLOCKED** on Christopher's engagement run |

**Fixture storage:** recorded event timelines + payloads stored as Demo-org-scoped fixtures (co-located with the existing demo-staging fixtures; exact store decided in the plan — DB row keyed by Demo org + workflow, or a Files-store fixture). Frozen only after `scrub-check.py` passes.

**Interface per fixture:** `{ workflow, events: OrderedEvent[], fillReportPayload, targetDurationMs }`. `present-completed` fixtures also reference the pre-rendered artifact id.

### Unit C — Timed replay branch in the managed-agent runtime (the mechanism)

**Surface correction:** the reveal flows through the **managed-agent thread stream** (`soapbox-platform/apps/api/src/services/managed-agents-runtime.ts`), NOT `RsraPanel`. `RsraPanel`'s `cached` state ("demo bypass — no real assessment") is deliberately inert during the demo and its `/rsra-pipeline/events` SSE is a *different* channel. RsraPanel is **out of scope** for the reveal.

In `managed-agents-runtime.ts`, gated to the Demo org behind the demo flag: when a demo-org thread receives the workflow prompt, **instead of running the live agent loop, replay the recorded fixture events on a fixed timeline** (~60–90s target — comfortably inside the 1–2 min window), then:

- **Replay shape:** end with a **live `fill_report`** using the recorded payload, rendering the artifact onto the *current* (live-created) asset. Re-running `fill_report` live sidesteps the `artifacts.asset_id NOT NULL` constraint for a freshly created asset (documented gotcha).
- **Present-completed shape (decarb):** end by surfacing the measures then displaying the pre-rendered artifact from Files.

**Why deterministic replay of real events:**
- Looks 100% real — it *is* the real recorded narration and tool-calls.
- No live model/MCP latency → predictable timing, rehearsable to the second.
- Removes the live-crrem/physrisk stage dependency (and crrem isn't even attached to the Demo portfolio per `00-env.md`).

**Trade-off recorded as a decision:** full scripted replay **drops the current live "hero" beats** (RSRA live physrisk; ESG live crrem+physrisk gap-fill). This was chosen deliberately: on stage, *looks real + never breaks* beats *genuinely live but variable*. Not an accident.

**Justification for bespoke server-side code** (against the usual avoid-server-side lean): a live stage demo's overriding requirement is "looks real + never breaks." A client-side fake would risk the thread diverging from backend persistence (messages/artifacts not actually written), which is more fragile on stage. The branch is tightly Demo-org gated and touches one file.

**Interface:** `maybeReplayDemoFixture(ctx): boolean` invoked at the top of the run loop; returns true (and drives the replay) when `isDemoOrg(orgId)` and a fixture matches the classified workflow; otherwise the normal live path runs unchanged. Must be verified against the runtime's actual stream-emission API (SSE event shape, message persistence points) so replayed events are indistinguishable from live ones and are correctly persisted.

### Unit D — Upstream onboarding beats (already built; verify only)

Add-asset → OM drop → instant map (Demo-org override) → footprint select → Audette link → open thread. These exist and are validated (`onboarding-fast-parallel-design.md`, the instant-map override). The spec's job here is a **verification checklist**, not new code: confirm they still chain cleanly into a Demo-org asset and hand off to Unit C. Audette link stays genuinely live (fast, and it's a real integration worth showing); if it ever becomes a timing risk, it can fold into the org-scoped demo shortcut later — out of scope now.

## Data flow (RSRA, representative)

```
Presenter: Add asset (Demo org)      → real asset row (Demo-org scoped)
         → drop OM                    → real file upload
         → instant map + footprints   → Demo-org override (no geocode)
         → link Audette               → live (real)
         → open thread + type prompt  → managed-agents-runtime receives prompt
                                         │
         [isDemoOrg && workflow=rsra] ──┤
                                         ▼
         Unit C: replay recorded RSRA events on ~60–90s timeline
                 (narration + tool-call markers stream to thread)
         Presenter flips to flowchart slide (1–2 min)
                                         ▼
         live fill_report(recorded payload) → artifact renders on current asset
         Presenter returns → report fully rendered ✅
```

ESG is identical with the esg-profile fixture. Decarb differs only at the tail (present-completed: surface measures → display pre-rendered artifact).

## Explicit decisions

1. **Full scripted replay** over live-with-cached-tools or progress-shell (user chose "pre-seed + timed reveal").
2. **Applies to all three workflows** with two fixture shapes (replay / present-completed).
3. **Drop live hero beats** (physrisk/crrem) for guaranteed timing — accepted trade.
4. **Reveal via managed-agent thread stream**, not RsraPanel.
5. **Org-scoped demo mode** (not per-asset) to support live add-asset.
6. **Bespoke server-side replay branch** justified by stage-reliability; tightly Demo-org gated.

## Out of scope

- RsraPanel changes.
- Any change to real-tenant behavior.
- Genuinely speeding up the real analysis pipeline (a separate, larger effort).
- New marketing/report templates (fixtures use the existing, already-fixed templates).

## Open items to resolve in the plan

- Exact fixture store (DB row vs Files-store) and recording tool (capture from a live service-account run).
- Server-side Demo-org constant + workflow classifier location.
- Verification that replayed events match the live stream shape and persist identically.
- Sequencing: RSRA fixture first (proves the pattern) → ESG → Decarb (gated on Christopher's engagement run).

## Success criteria

- From a blank Demo-org screen, a presenter completes the full narrative and the deliverable is fully rendered within the 1–2 min slide window, every rehearsal, with no live-analysis variability.
- The rendered artifact reflects the current verified output (post-fixes).
- `scrub-check.py` passes on every frozen fixture.
- No path reachable outside the Demo org.
