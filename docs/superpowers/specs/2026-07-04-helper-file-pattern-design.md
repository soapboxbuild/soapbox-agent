# Helper File & Artifact-Tiering Pattern — Design Spec

**Date:** 2026-07-04
**Status:** Approved (Christopher). Ready for implementation plan.
**Applies to:** all Soapbox deliverable-producing skills — Portfolio Analysis, Decarb Plan,
Rehab Analysis (new skill, forthcoming), and any future project type.

## Problem

Two related messes during an engagement:
1. **Scattered working HTML.** Intermediate material (baseline snapshots, building-model
   verification, allocation tables, QA views) is saved ad hoc — multiple files, inconsistent
   folders (`decarb-plan`, `Reports`), inconsistent names — producing clutter and no single
   place to see the current state of the analysis.
2. **Over-produced gate artifacts.** The HTML rendered at intermediate phases/gates is big,
   overly verbose, and styled like a finished deliverable — so a provisional checkpoint reads as
   trustworthy client output, and effort goes into polishing things that are just checkpoints.

## Decision — two tiers, nothing in between

Every deliverable-producing skill classifies all its outputs into exactly two tiers:

| Tier | What | Treatment | Location |
|---|---|---|---|
| **Working / checklist** | ONE growing "helper" HTML per engagement + the verifier's `findings.md` ledger. Absorbs all intermediate **and gate** material: source-of-truth panel, open questions, adjudication log, and per-phase / per-gate **checklists**. | **Utilitarian** — plain, terse, legible. Never "designed." | `Helper Files/` |
| **Design-forward** | Exactly two client deliverables: the **Report** and the **Delivery-Meeting Slides**. | Polished, brand-quality. Rendered **only at their gate**. | `Reports/` |

Nothing sits between these tiers. Intermediate/gate renders no longer exist as standalone
verbose HTML — they collapse into checklist sections of the helper file. Human gates are reviewed
**as the relevant checklist section of the helper**, not as a polished artifact.

## The two design-forward deliverables
- **Report** — the existing polished report (HTML → PDF), gated by the hard verifier
  render-gate (unchanged: still blocks until findings are clean).
- **Delivery-Meeting Slides** — a distinct deliverable for the client delivery meeting
  (methodology, follow-up questions, key results). Draws content *from* the report but
  **extends beyond it**; it is not merely a PPTX export of the report. Authored as its own
  design-forward artifact. (The slide template/generator itself is a separate build if one does
  not yet exist; this spec establishes it as a design-forward deliverable and its tier placement.)

## Helper file specification

### 1. File identity (stable → one growing file)
- **Folder:** `Helper Files`
- **Filename:** `[ISO start date] - Helper Files - [Deliverable Type].html`
  - `[ISO start date]` = engagement **start date**, captured once and **fixed forever** (never the
    save date). Stored in state (`state.helper.start_date`, `state.helper.filename`) so every later
    save reuses it verbatim.
  - `[Deliverable Type]` = the project type: `Decarb Plan`, `Portfolio Analysis`, `Rehab Analysis`.
  - Example: `2026-07-04 - Helper Files - Decarb Plan.html`
- **Save mechanism:** `save_file` with that exact `name` + `folder`. The runtime already
  **upserts by (asset_id, name, folder)** (deletes the existing row+object, re-uploads), so
  reusing the identical name overwrites in place — one growing file, no clutter. No platform
  change required.

### 2. Source-of-truth relationship (no drift)
- The JSON **state file remains the machine source of truth.**
- The helper is a **rendered human-readable view of state.** At every phase checkpoint the agent
  **regenerates the whole helper from current state** and saves it under the fixed name.
- "Grows and adapts" = re-render from state; the agent must **never** hand-edit the helper in a
  way that diverges from state. If a value is in the helper, it came from state.

### 3. Internal structure (shared hybrid skeleton)
Top to bottom, one shared skeleton for every deliverable type:
1. **Header badge** — bold `INTERNAL WORKING FILE — NOT THE DELIVERABLE`; deliverable type,
   asset/portfolio, engagement start date, current phase, last-updated timestamp.
2. **Source-of-Truth panel** — every key input as a row: value · source · provenance tier
   (`measured > audit > modeled > estimate`) · 🔒 locked flag (adjudicated/locked values).
3. **Open Questions / pending adjudications** — unresolved items and who owns each.
4. **Adjudication log** — decision · locked value · date (append-only).
5. **Per-phase / per-gate checklist sections** — one collapsible `<details>` per workflow phase,
   each a **checklist** with status markers (`✓ done` / `○ in progress` / `⚠ blocked`) plus the
   minimal working detail for that phase. This is what a human reviews at a gate. **The phase list
   is deliverable-specific** (see §5); everything above is identical across deliverable types.

Styling: single self-contained HTML file (inline CSS, no external assets), utilitarian and
legible. Deliberately **not** brand-polished — polish is reserved for the two design-forward tiers.

### 4. Encoded once as a standalone skill, referenced by path
- The pattern + shared HTML skeleton live in a **standalone skill: `skills/helper-files/SKILL.md`**
  — mirroring the repo's existing shared-concern convention (`decarb-plan` already references
  `skills/utility-split-estimation/SKILL.md` by path). This gets the shared skeleton auto-listed
  in the bundle router, bundled for the managed agent, and reachable in Claude Code / opencode,
  with **one source of truth** (no per-skill copies → no drift).
- Each deliverable skill (`decarb-plan`, `portfolio-analysis`, future `rehab-analysis`) **points to
  `skills/helper-files/SKILL.md` by path** and supplies only: its own **phase/gate checklist list**
  and the Source-of-Truth field set relevant to that deliverable.
- Per-deliverable phase maps:
  - **Decarb Plan:** P1 Kickoff · P1.5 Building/footprint validation · P2 Baseline (ESPM) ·
    P3 Allocation + Equipment survey · P4 Economics/measures · P4 Verification gate · P5 Deliverable(s).
  - **Portfolio Analysis:** its existing phase sequence (ingest → per-asset roll-up → portfolio
    economics → render); mapped during implementation.
  - **Rehab Analysis:** defined when that skill is built (separate new project type / skill); the
    pattern is plug-in-ready — the new skill adds a phase list and reuses the shared skeleton unchanged.

### 5. Lifecycle
- **Create** at engagement start (capture fixed start date + filename into state); render the
  skeleton with the SoT panel seeded from kickoff.
- **Update** at every phase checkpoint (regenerate from state, save under the fixed name).
- **Gate review** reads the relevant checklist section of the helper — never a polished artifact.
- **Never gate on it** — it is a working aid; gates read state, not the helper.

## Verifier findings ledger
The verifier plugin's `findings.md` ledger is working/checklist material and lives in the same
`Helper Files/` folder (was `Verification/`). Changed in `verifier-mcp` `src/ledger.ts` (folder
lookup + insert both → `Helper Files`; committed `aba65e7`). **Deploy deferred** — deploying the
verifier connector-service severs live engagements' verifier MCP connection; ship between
engagements. After deploy, migrate the two existing `Verification/findings.md` rows (one asset-,
one portfolio-scoped) to folder `Helper Files` so the ledger continues updating in place rather
than orphaning the old rows and creating new ones.

## Migration / cleanup
- Going forward, decarb consolidates scattered intermediate/gate HTML (`p1-baseline-…`,
  `building-model-verification-…`) into the single `Helper Files/…- Decarb Plan.html`.
- Existing stray Westminster HTML files: leave in place unless Christopher asks to delete (harmless).

## Non-goals
- No change to the report render/verifier-gate flow (the report gate stays).
- No platform/runtime code change (`save_file` upsert already supports the one-file behavior).
- No new tool — this is skill doctrine + a shared skeleton skill.
- The helper is not a source of truth — state remains authoritative; the helper is a view.
- Building the slide-deck template/generator is out of scope here (tracked separately); this spec
  only fixes its tier (design-forward) and that it extends beyond the report.

## Encoding surfaces (persistence)
- `skills/helper-files/SKILL.md` — source of truth for the pattern + skeleton — referenced by each
  deliverable skill → reaches Claude Code, opencode, and the app managed agent via the bundled skill.
- Operationalizes the decarb agent architecture decision's "artifacts only at gates" and
  "source-of-truth/provenance table" near-term actions. Related: [[decarb-plan-workflow]].
