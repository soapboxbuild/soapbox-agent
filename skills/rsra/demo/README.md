# RSRA Demo Fixtures — 4400 Prairie Crossing

Pseudonymous demo fixtures for the RSRA (Rapid Sustainability Risk Assessment) workflow,
authored under task 2.1. These let a demo run of the `rsra` skill go from "reads an OM" to
"emits a `fill_report(template:'rsra')` artifact" without needing a real deal in the room.

## What's staged here

| File | Purpose |
|---|---|
| `om_4400_prairie_crossing.pdf` | 6-page pseudonymous Offering Memorandum. Feed this to the RSRA skill as the source document for Phase 1 (Document Triage). |
| `build_om.py` | The generator script for the OM PDF (reportlab). Re-run it if the OM needs to change; a local `.venv` with `reportlab` + `pypdf` + `cryptography` is checked into `.venv/` alongside it (created via `python3 -m venv .venv && .venv/bin/pip install reportlab`). |
| `rsra_data.json` | The **complete** `fill_report(template:'rsra', data)` payload — everything Phases 2–9 of the skill would have computed. Use this directly when demoing the report renderer without re-running the full research phases. Matches the schema documented in `skills/rsra/SKILL.md` (Phase 10 pre-flight checklist + inline example), including the fields `templates/rsra/schema.json` does not yet list (see note below). |
| `physrisk_cache.json` | Staged `assess_physical_risk` / `calculate_climate_var` results for 4400 Prairie Crossing, shaped exactly like the live physrisk MCP tool responses, so Phase 4 resolves instantly in a demo. |
| `bps_cache.json` | Staged jurisdiction/regulatory lookup (Energize Denver ordinance + Colorado HB21-1286 + federal IRA context) for Phase 3, shaped as a citable document rather than a code cache. |

## Pseudonymization

All names, brokers, developer, schools, and submarket data in these fixtures are invented.
The fictional asset "4400 Prairie Crossing" sits in Denver, CO 80238 (a real BPS jurisdiction,
so Energize Denver lookups are coherent). All unit counts, rents, NOI, CapEx, and
physical/regulatory figures are freshly invented, not transcribed from any source.

The private real→fictional mapping used while authoring lives in the **untracked**
`.pseudonym-map.md` in this directory (gitignored — it contains real source names and must
never be committed).

## The 2-3 live hero beats

Even with these fixtures staged, keep these calls live in a demo run — they are the parts
of the RSRA workflow that are genuinely dynamic and where a canned cache would undersell
the product:

1. **`assess_physical_risk` / `calculate_climate_var` (physrisk MCP) stays LIVE.**
   `physrisk_cache.json` exists so a demo *can* fall back to cached numbers if the live
   call is unavailable, but the intended hero beat is calling the real MCP tool against
   4400 Prairie Crossing's lat/lon (39.7702, -104.8756) on stage and watching the hail/heat/
   water-stress hazard table and Climate VaR populate live. Only use the cache as a backup.
2. **`fill_report(template:'rsra', data)`** — the actual report render (charts, sensitivity
   scatter, GHG donut) should be triggered live from `rsra_data.json` so the audience sees
   the real template render, not a screenshot.
3. **Regulatory/jurisdiction web lookups (Phase 3 corroboration)** — `bps_cache.json` gives
   the Energize Denver figures needed to move fast, but a live `brave_web_search` confirming
   the current year's published penalty rate is the more credible version of this beat if
   time allows; the cache explicitly labels its penalty figure as illustrative for this reason.

## Known schema note

`templates/rsra/schema.json` has `additionalProperties: false` and does not yet list
`decarb_sensitivity`, `ghg_scoping`, or `certifications_and_debt` at the top level, even
though `skills/rsra/SKILL.md`'s Phase-10 pre-flight checklist calls `decarb_sensitivity`
and `ghg_scoping` **required**, and `templates/rsra/layout.html` / `layout-agent.html` /
`layout-post.html` all read `data.decarb_sensitivity`, `data.ghg_scoping`, and
`data.certifications_and_debt` directly. `rsra_data.json` includes all three per the
SKILL.md contract and the template's actual runtime behavior; the schema file is stale
and should be updated separately (not part of this task).
