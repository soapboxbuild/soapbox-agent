# Project Kickoff Skill — Design Spec

**Date:** 2026-06-30
**Status:** Approved for implementation
**First project type:** Retrofit Analysis (AvalonBay)

---

## Problem

Starting a new analysis project for a client requires collecting a consistent set of scoping
information: goals, data sources, financial assumptions, existing documents, timeline, and
team. Today this happens ad hoc — in emails, Slack threads, or verbal conversations — leaving
agents without a structured reference and forcing repeated clarification requests throughout
delivery. The kickoff skill captures this information interactively in real time with the
client and produces a persistent project file that agents can reference for the duration of
the engagement.

---

## Goals

- Capture the 6 core scoping dimensions for any project type in a single interactive session
- Adapt questions to the specific project type (retrofit analysis, energy audit, etc.)
- Check existing asset data before asking for it — never request what's already known
- Produce a structured + narrative project file saved to the asset or portfolio folder
- Be extensible: new project types added by dropping in a file, not editing core logic

## Non-goals

- Executing the project itself (that's the job of the relevant analysis skill)
- Replacing a formal SOW or contract
- Handling projects that span multiple unrelated assets (multi-asset portfolio projects are
  scoped at the portfolio level)

---

## Architecture

```
skills/project-kickoff/
  SKILL.md                          ← core orchestration logic
  project-types/
    retrofit-analysis.md            ← first project type
    energy-audit.md                 ← future
    leed-certification.md           ← future
```

Output path: `projects/<asset-key>/<project-type>-kickoff.md`

The skill is invoked conversationally (e.g. "kick off a retrofit analysis for AvalonBay")
and runs entirely interactively via `AskUserQuestion` structured prompts, one at a time.

---

## Invocation & Project Type Inference

The skill parses the invocation text for:
1. **Project type** — matched against known keywords in the project-types registry
2. **Asset or portfolio name** — parsed from the same text, used to derive the asset key

**Asset key derivation:** lowercase, spaces → hyphens (e.g. "AvalonBay Meadows" → `avalonbay-meadows`)

**Match rules:**
- Clear keyword match → proceed without asking
- Ambiguous or no match → `AskUserQuestion` presenting known project types as options + "Other"
- Asset name missing → ask with free-text input
- Asset vs portfolio scope: inferred from context; if unclear, ask via `AskUserQuestion`

---

## Pre-flight Data Check

Before starting the Q&A loop, the skill scans the asset folder for existing data:

| What to check | Path |
|--------------|------|
| Cashflow model | `.cashflow-models/<asset-key>.json` |
| Prior project files | `projects/<asset-key>/` |
| PCA / condition reports | any file matching `*pca*`, `*condition*` |
| Energy audit | any file matching `*audit*`, `*energy*` |
| Equipment schedule | any file matching `*equipment*`, `*schedule*` |
| Utility data | any file matching `*utility*`, `*bills*`, `*espm*` |

Findings are surfaced in the relevant question: "I found an energy audit from [date] — is this
the document we should use, or do you have an updated version?" The user can confirm, replace,
or note that additional documents are coming.

---

## Q&A Loop

Six questions, asked one at a time via `AskUserQuestion`. Each question is adapted per project
type (see project-type files). The core template:

| # | Dimension | Purpose |
|---|-----------|---------|
| 1 | **Project goal** | What does success look like? Specific targets, drivers, constraints. |
| 2 | **Data sources + provider** | What equipment/building data will we use, and who provides it? |
| 3 | **Financial assumptions + provider** | What underwriting inputs apply, and who owns them? |
| 4 | **Existing CapEx / engineering docs** | What prior work exists? (Prefilled from pre-flight.) |
| 5 | **Milestones / timeline** | Key dates, phasing constraints, funding deadlines. |
| 6 | **Delivery team + POC** | Who's involved in delivery? Who is the primary client contact? |

Questions use `AskUserQuestion` with structured options where choices are enumerable (e.g.
project goal type, data source ownership), and free-text fields where the answer is open-ended.
Multi-select is used where appropriate (e.g. which data sources are needed).

---

## Project Type: Retrofit Analysis

Defined in `project-types/retrofit-analysis.md`. Adapted questions:

**Q1 — Project Goal**
- Options: Energy reduction target (%), Carbon neutrality / net-zero, Regulatory compliance
  deadline, CapEx planning / budget development, Other (free text)
- Follow-up (always): What is the primary driver? (Owner mandate, financing, regulatory, ESG reporting)

**Q2 — Data Sources**
- Options (multi-select): Equipment schedules, Existing conditions report, Utility history
  (12–24 months), Control system data / BMS export, Other
- For each selected: Who provides it? (Client, engineering firm, Soapbox pulls from ESPM, TBD)
- Pre-flight note: surface any utility/equipment data already found

**Q3 — Financial Assumptions**
- Structured inputs: Discount rate, Utility escalation rate (%/yr), Hold period (years),
  Incentive assumptions (IRA, state programs, utility rebates — yes/no/TBD)
- Provider: Client CFO/finance team, Soapbox standard assumptions, or custom

**Q4 — Existing CapEx / Engineering Docs**
- Prefilled from pre-flight scan with confirm/replace options
- If nothing found: ask for PCA, prior energy audit, equipment inventory, existing retrofit scope

**Q5 — Milestones / Timeline**
- Structured: Target construction start, Phasing constraints (occupied building, seasonality),
  Funding deadline (if applicable), Report delivery date needed

**Q6 — Team & POC**
- Multi-select roles: Soapbox lead, Client PM, Engineering firm, Owner's rep, Sustainability
  consultant, Contractor
- Free text: Primary client point of contact (name + email)

---

## Output File

Saved to `projects/<asset-key>/<project-type>-kickoff.md` immediately after the final question.

```markdown
# <Asset Name> — <Project Type> Kickoff
**Date:** YYYY-MM-DD
**Conducted by:** <agent name>
**Project type:** <type>

## Executive Summary
2–3 sentence narrative covering: what the project is, the primary goal/driver,
key constraints or timeline pressures, and who is leading delivery.

---

## 1. Project Goal
[Structured answer + any narrative context from user]

## 2. Data Sources
| Source | Provider | Status |
|--------|---------|--------|
| ...    | ...     | Confirmed / TBD |

## 3. Financial Assumptions
| Parameter | Value | Source |
|-----------|-------|--------|
| ...       | ...   | ...    |

## 4. Existing Documents
| Document | Date | Status |
|----------|------|--------|
| ...      | ...  | Found / Pending |

## 5. Timeline & Milestones
| Milestone | Target Date | Notes |
|-----------|-------------|-------|
| ...       | ...         | ...   |

## 6. Team & Point of Contact
| Role | Name / Firm | Contact |
|------|-------------|---------|
| ...  | ...         | ...     |

---
*Generated by project-kickoff skill v1.0.0 — [date]*
```

---

## Extensibility

Adding a new project type requires only:
1. Create `project-types/<new-type>.md` with adapted question definitions
2. Add the type name + trigger keywords to the registry section of `SKILL.md`

No changes to core orchestration logic.

---

## Open Questions

- Should the kickoff file be versioned (kickoff-v2.md) if re-run for the same project, or
  overwrite? Recommendation: timestamp and append, keeping history.
- Should the skill notify the assigned Soapbox delivery lead via Slack/email on completion?
  Out of scope for v1, but the POC field makes this easy to add.
