# Helper File Pattern — Design Spec

**Date:** 2026-07-04
**Status:** Approved (Christopher). Ready for implementation plan.
**Applies to:** all Soapbox deliverable-producing skills — Portfolio Analysis, Decarb Plan,
Rehab Analysis (new skill, forthcoming), and any future project type.

## Problem

During an engagement the agent produces intermediate working HTML (baseline snapshots,
building-model verification, allocation tables, QA/adjudication views). Today these are saved
ad hoc: multiple files, inconsistent folders (`decarb-plan`, `Reports`), inconsistent names
(`p1-baseline-…`, `building-model-verification-…`). The result is clutter, no single place to
see the current state of the analysis, and rendered HTML doubling as a running scratchpad —
which reads as a trustworthy deliverable even when provisional.

## Decision

Every deliverable-producing skill maintains **exactly one growing, self-updating "helper" HTML
file per engagement** — an explicitly *internal* working companion, distinct from the polished
client deliverable. It preserves the standing "artifacts (deliverables) only at gates" rule by
giving the necessary working material one clean, clearly-labelled home.

## Pattern specification

### 1. File identity (stable → one growing file)
- **Folder:** `Helper Files`
- **Filename:** `[ISO start date] - Helper Files - [Deliverable Type].html`
  - `[ISO start date]` = the engagement/analysis **start date**, captured once and **fixed
    forever** (never the save date — a changing date would recreate the clutter this fixes).
    Stored in state (e.g. `state.helper.start_date`, `state.helper.filename`) so every later
    save reuses it verbatim.
  - `[Deliverable Type]` = the project type: `Decarb Plan`, `Portfolio Analysis`, `Rehab Analysis`.
  - Example: `2026-07-04 - Helper Files - Decarb Plan.html`
- **Save mechanism:** `save_file` with that exact `name` + `folder`. The runtime already
  **upserts by (asset_id, name, folder)** (deletes the existing row+object, re-uploads), so
  reusing the identical name overwrites in place — no new files, no clutter. This is existing
  behavior; no platform change is required.

### 2. Source-of-truth relationship (no drift)
- The JSON **state file remains the machine source of truth.**
- The helper is a **rendered human-readable view of state.** At every phase checkpoint the agent
  **regenerates the whole helper from current state** and saves it under the fixed name.
- "Grows and adapts" = re-render from state; the agent must **never** hand-edit the helper in a
  way that diverges from state. If a value is in the helper, it came from state.

### 3. Internal structure (shared hybrid skeleton)
Top-to-bottom, one shared skeleton for every deliverable type:
1. **Header badge** — bold `INTERNAL WORKING FILE — NOT THE DELIVERABLE`; plus deliverable type,
   asset/portfolio, engagement start date, current phase, last-updated timestamp.
2. **Source-of-Truth panel** — every key input as a row: value · source · provenance tier
   (`measured > audit > modeled > estimate`) · 🔒 locked flag (for adjudicated/locked values).
3. **Open Questions / pending adjudications** — what's unresolved and who owns it.
4. **Adjudication log** — decision · locked value · date (append-only history of resolved conflicts).
5. **Collapsible phase sections** — one `<details>` per workflow phase, each with a status marker
   (`✓ done` / `○ in progress` / `⚠ blocked`) and that phase's working detail. **The phase list is
   deliverable-specific** (see §5); everything above is identical across deliverable types.

Styling: lightweight, single self-contained HTML file (inline CSS, no external assets), Soapbox
brand-neutral. Legibility over polish — this is an internal instrument, not a client artifact.

### 4. Distinct from the deliverable
- The polished client deliverable is unchanged: rendered **only at its gate**, saved to `Reports/`.
- The helper lives in `Helper Files/` and carries the INTERNAL badge so it is never mistaken for
  or shipped as the deliverable.

### 5. Encoded once, referenced everywhere
- A single shared reference — `skills/_shared/helper-file-pattern.md` — defines this pattern and
  ships the **HTML skeleton** (sections 1–4 + the `<details>` phase-section template).
- Each deliverable skill (`decarb-plan`, `portfolio-analysis`, and the future `rehab-analysis`)
  **points to the shared reference** and supplies only its own **phase-section list** and the
  Source-of-Truth field set relevant to that deliverable.
- Per-deliverable phase maps:
  - **Decarb Plan:** P1 Kickoff · P1.5 Building/footprint validation · P2 Baseline (ESPM) ·
    P3 Allocation + Equipment survey · P4 Economics/measures · P4 Verification gate · P5 Deliverable.
  - **Portfolio Analysis:** per that skill's existing phase sequence (ingest → per-asset roll-up →
    portfolio economics → render); mapped during implementation.
  - **Rehab Analysis:** defined when that skill is built (new project type); the pattern is
    plug-in-ready — the new skill adds a phase list and reuses the shared skeleton unchanged.

### 6. Lifecycle
- **Create** at engagement start (capture fixed start date + filename into state); render the
  skeleton with the SoT panel seeded from kickoff.
- **Update** at every phase checkpoint (regenerate from state, save under fixed name).
- **Never gate on it** — it is a working aid; gates read state, not the helper.

## Migration / cleanup
- Going forward, decarb consolidates the scattered intermediate HTML (`p1-baseline-…`,
  `building-model-verification-…`) into the single `Helper Files/…- Decarb Plan.html`.
- Existing stray files (`decarb-plan/…`, `Reports/…verification…`) for the Westminster engagement:
  leave in place unless Christopher asks to delete (no functional need to remove; harmless).

## Non-goals
- No change to the deliverable render/gate flow.
- No platform/runtime code change (save_file upsert already supports this).
- No new tool — this is skill doctrine + a shared reference/skeleton.
- Not a source of truth — state remains authoritative; the helper is a view.

## Encoding surfaces (persistence, per prior pattern)
- Shared reference `skills/_shared/helper-file-pattern.md` (source of truth for the pattern),
  referenced by each deliverable skill → reaches Claude Code, opencode, and the app managed agent
  via the bundled skill.
- Related: [[decarb-plan-workflow]], analytics/provenance doctrine, and the decarb agent
  architecture decision record (this operationalizes its "artifacts only at gates" +
  "source-of-truth/provenance table" near-term actions).
