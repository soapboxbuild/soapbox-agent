# Project Kickoff Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `project-kickoff` skill that runs an interactive, structured client scoping session and saves a project reference file to `projects/<asset-key>/`.

**Architecture:** A core `SKILL.md` handles invocation parsing, pre-flight scanning, Q&A orchestration, and file writing. A `project-types/` subdirectory holds one file per project type defining its adapted questions and output template. The first project type is `retrofit-analysis`.

**Tech Stack:** Markdown skills (agentskills.io spec), AskUserQuestion tool for structured prompts, bash for file operations.

## Global Constraints

- Skills live in `skills/<name>/SKILL.md` — follow the agentskills.io frontmatter spec exactly
- Asset key convention: lowercase name, spaces → hyphens (e.g. "AvalonBay" → `avalonbay`)
- Output path: `projects/<asset-key>/<type-key>-kickoff.md` (asset) or `projects/portfolio/<type-key>-kickoff.md` (portfolio)
- Re-run: if output file exists, ask Overwrite vs Create new (timestamped `<type-key>-kickoff-YYYY-MM-DD.md`)
- One AskUserQuestion at a time — never batch questions
- Pre-flight scan before every data-related question

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `skills/project-kickoff/SKILL.md` | Create | Core orchestration: parse, pre-flight, Q&A loop, write output |
| `skills/project-kickoff/project-types/retrofit-analysis.md` | Create | Retrofit-specific question definitions and output template |

---

### Task 1: Create skill scaffold — frontmatter, invocation parsing, project type inference

**Files:**
- Create: `skills/project-kickoff/SKILL.md`

**Interfaces:**
- Produces: A loadable skill with a working trigger description and project type registry the Q&A loop (Task 3) will reference

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p ~/soapbox-agent/skills/project-kickoff/project-types
```

Expected: no output, exits 0.

- [ ] **Step 2: Write the SKILL.md scaffold**

Create `skills/project-kickoff/SKILL.md` with this exact content:

```markdown
---
name: project-kickoff
description: >
  Interactive project kickoff for real-time client sessions. Captures goal, data sources,
  financial assumptions, existing documents, timeline, and team for any project type.
  Adapts questions to the project type. Checks existing asset data before requesting it.
  Saves a structured + narrative project file to projects/<asset-key>/.
  Triggers on: "kick off", "project kickoff", "start a project", "kickoff for",
  "begin a [type] project", "run a kickoff", "kickoff [asset]".
version: 1.0.0
---

# Project Kickoff

You are running an interactive project scoping session. This may be happening in real
time with the client present — be professional, clear, and concise.

---

## Step 1: Parse Invocation

Extract from the invocation text:
- **Project type** — match against the Project Type Registry below
- **Asset or portfolio name** — the property or client name
- **Scope** — asset-level or portfolio-level (default: asset)

**Project Type Registry:**

| Trigger keywords | Project Type | Type key |
|-----------------|-------------|----------|
| retrofit, retrofit analysis, energy retrofit, mechanical retrofit, building retrofit | Retrofit Analysis | retrofit-analysis |

If the project type does not match any entry: ask via AskUserQuestion:
> "What type of project are we kicking off?"
> Options: Retrofit Analysis | Other (describe)

If the asset name is missing from the invocation: ask via AskUserQuestion free text:
> "What is the name of the asset (or portfolio)?"

If scope is ambiguous: ask via AskUserQuestion:
> "Is this for a single asset or a portfolio?"
> Options: Single asset | Portfolio

**Derive asset key:** lowercase the name, replace spaces with hyphens.
Examples: "AvalonBay" → `avalonbay` | "Prose Frontier OM" → `prose-frontier-om`

**Load project type definition:**
```bash
cat skills/project-kickoff/project-types/<type-key>.md
```
Follow the question definitions in that file for Steps 3–4.

---

## Step 2: Pre-flight Data Scan

Scan for existing data before asking any questions. Run:

```bash
ls .cashflow-models/<asset-key>.json 2>/dev/null && echo "HAS_CASHFLOW" || true
ls projects/<asset-key>/<type-key>-kickoff.md 2>/dev/null && echo "HAS_PRIOR_KICKOFF" || true
find . -maxdepth 4 \( \
  -iname "*pca*" -o \
  -iname "*condition*" -o \
  -iname "*audit*" -o \
  -iname "*energy*" -o \
  -iname "*equipment*" -o \
  -iname "*schedule*" -o \
  -iname "*utility*" -o \
  -iname "*bills*" -o \
  -iname "*espm*" \
\) 2>/dev/null
```

Track findings:
- `has_cashflow_model` — true if `.cashflow-models/<asset-key>.json` exists
- `has_prior_kickoff` — true if the output file already exists
- `found_docs` — list of matched filenames, classified by type (PCA, audit, utility, etc.)

**Re-run handling:** If `has_prior_kickoff` is true, ask before proceeding:
> "A kickoff file already exists for this project (`projects/<asset-key>/<type-key>-kickoff.md`).
> What would you like to do?"
> Options: Overwrite it | Create a new timestamped version

If "Create new": append `-YYYY-MM-DD` to the filename (use today's date).

---

## Step 3: Q&A Loop

Ask the 6 questions **one at a time**. For each question:

1. Check whether pre-flight found data that answers it (fully or partially).
2. If yes: surface the finding and ask to confirm or update.
   > "I found [document/data] — is this what we'll use, or do you have an updated version?"
   > Options: Use this | I have an updated version | Not sure yet
3. If no prior data: ask the full question as defined in the project type file.

Never ask more than one question per message.

---

## Step 4: Confirm and Save

After all 6 questions, present a summary and ask for confirmation:

> "Here's what I've captured for this project. Does everything look correct?"
> [Show all 6 answers as a bulleted list]
> Options: Looks good — save it | I need to change something

If "I need to change something": ask which question to revisit (options: list the 6 question
titles), then loop back to that question, then return here.

Once confirmed: proceed to Step 5.

---

## Step 5: Write Project File

Determine output path:
- Asset scope: `projects/<asset-key>/<type-key>-kickoff.md`
- Portfolio scope: `projects/portfolio/<type-key>-kickoff.md`
- Timestamped new: `projects/<asset-key>/<type-key>-kickoff-YYYY-MM-DD.md`

Create directory:
```bash
mkdir -p projects/<asset-key>/
```

Write the file using the output template from the project type file, filling in all
answers from the Q&A loop.

Confirm to the user:
> "Project kickoff saved to `projects/<asset-key>/<type-key>-kickoff.md`.
> This file will be used as the project reference throughout delivery."
```

- [ ] **Step 3: Verify the file is valid SKILL.md**

Check frontmatter is present and complete:
```bash
head -10 ~/soapbox-agent/skills/project-kickoff/SKILL.md
```
Expected output starts with `---` and includes `name:`, `description:`, `version:`.

- [ ] **Step 4: Commit**

```bash
cd ~/soapbox-agent
git add skills/project-kickoff/SKILL.md
git commit -m "feat(project-kickoff): add skill scaffold with invocation parsing and pre-flight scan"
```

---

### Task 2: Create retrofit-analysis project type definition

**Files:**
- Create: `skills/project-kickoff/project-types/retrofit-analysis.md`

**Interfaces:**
- Consumed by: `SKILL.md` Step 1 (`cat skills/project-kickoff/project-types/retrofit-analysis.md`)
- Produces: 6 question definitions + output template the Q&A loop and file writer use

- [ ] **Step 1: Write the project type file**

Create `skills/project-kickoff/project-types/retrofit-analysis.md` with this exact content:

```markdown
# Project Type: Retrofit Analysis

## Q1 — Project Goal

**Question:** "What is the primary goal of this retrofit project?"

AskUserQuestion options:
- Energy reduction target (specify % or kWh target)
- Carbon neutrality / net-zero by a specific year
- Regulatory compliance deadline (specify regulation)
- CapEx planning and budget development
- Other (describe)

**Follow-up (always):** "What is the primary driver behind this project?"
AskUserQuestion options:
- Owner or board mandate
- Financing or refinancing requirement (e.g. green loan, Fannie Mae Green Rewards)
- Regulatory requirement (local law, building performance standard)
- ESG reporting / investor requirement
- Proactive capital planning

Store as: `goal_type`, `goal_driver`, and any free-text detail.

---

## Q2 — Data Sources

**Pre-flight check:** Surface any equipment schedules, existing conditions reports,
or utility data found in the scan. For each found item:
> "I found [filename] — is this the [document type] we should use?"
> Options: Yes, use this | I have a newer version | Skip this one

**Question (for sources not found in pre-flight):**
"Which data sources will we need for this analysis?"

AskUserQuestion multi-select options:
- Equipment schedules (HVAC, lighting, envelope)
- Existing conditions report
- Utility history (12–24 months)
- Building automation / BMS export
- Prior energy model or simulation
- Other

**For each selected source:** Ask separately:
> "Who will provide the [source name]?"
> Options: Client provides | Engineering firm provides | Soapbox pulls from ESPM | TBD

Store as: `data_sources` — list of `{source, provider, status}`.

---

## Q3 — Financial Assumptions

**Pre-flight check:** If `has_cashflow_model` is true:
> "I found a cashflow model for this asset. Should we use its financial parameters
> as the starting point for this analysis?"
> Options: Yes, use existing parameters | No, we'll use custom assumptions

**Question:**
Ask each financial parameter individually (one AskUserQuestion per parameter):

1. **Discount rate:** Free text (e.g. "7.5%") — or "Use Soapbox standard (7%)"
2. **Utility escalation rate:** Free text (e.g. "3% per year") — or "Use Soapbox standard (3%/yr)"
3. **Hold period:** Options: 3 years | 5 years | 7 years | 10 years | Other
4. **Incentive assumptions:**
   Options (multi-select): IRA / federal tax credits | State incentive programs |
   Utility rebates | None | TBD — research needed

**Provider:** After all parameters:
> "Who will own / sign off on these financial assumptions?"
> Options: Client CFO / finance team | Soapbox standard assumptions | Joint — client reviews Soapbox defaults

Store as: `financial_assumptions` — `{discount_rate, escalation_rate, hold_period, incentives, provider}`.

---

## Q4 — Existing CapEx / Engineering Documents

**Pre-flight check (primary):** List all documents found in scan:
> "I found the following documents in your asset folder:"
> [List each found doc with its inferred type]
> "Are these the documents we should work from, or are there others?"
> Options: These are correct | Some are outdated — I'll provide updates | There are additional documents coming

**Question (if nothing found, or to capture additional):**
"Are there any existing CapEx plans or engineering documents we should incorporate?"

AskUserQuestion multi-select:
- Property Condition Assessment (PCA)
- Prior energy audit
- Existing retrofit scope or capital plan
- Equipment inventory
- None — starting fresh

For each selected: "Who holds this document and when can we expect it?"
Free text answer.

Store as: `existing_docs` — list of `{type, filename_or_description, provider, status}`.

---

## Q5 — Timeline & Milestones

**Question:** Ask each milestone individually:

1. **Report delivery needed by:**
   Options: Within 2 weeks | Within 1 month | Within 3 months | No hard deadline | Specific date (free text)

2. **Target construction / implementation start:**
   Options: This year | Next year | Not yet defined | Specific date (free text)

3. **Phasing constraints:**
   Options (multi-select): Occupied building (tenant disruption limits) | Seasonal constraints |
   Funding or grant deadline | Regulatory deadline | No constraints

4. **Funding deadline (if applicable):**
   Options: Yes — specify date | No deadline | TBD

Store as: `milestones` — `{report_by, construction_start, phasing_constraints, funding_deadline}`.

---

## Q6 — Team & Point of Contact

**Question:** "Who is involved in delivering this project?"

AskUserQuestion multi-select roles:
- Soapbox lead
- Client project manager
- Engineering firm
- Owner's representative
- Sustainability consultant
- General contractor
- Other

For each selected role: Ask "Who fills this role?" — free text (name and firm).

Then: "Who is the primary client point of contact?"
Free text: name and email address.

Store as: `team` — list of `{role, name_firm}` + `primary_contact: {name, email}`.

---

## Output Template

Use this template to write the project file. Fill every section from the Q&A answers.

```markdown
# <Asset Name> — Retrofit Analysis Kickoff
**Date:** YYYY-MM-DD
**Conducted by:** <agent name>
**Project type:** Retrofit Analysis

## Executive Summary

<2–3 sentence narrative covering: what the retrofit project is aiming to achieve,
the primary driver (owner mandate / regulatory / financing), key constraints or
timeline pressures, and who is leading delivery on the client side.>

---

## 1. Project Goal

**Primary goal:** <goal_type>
**Driver:** <goal_driver>
<Any additional detail provided>

## 2. Data Sources

| Source | Provider | Status |
|--------|---------|--------|
<One row per source: source name | provider | Confirmed / Pending / TBD>

## 3. Financial Assumptions

| Parameter | Value | Source |
|-----------|-------|--------|
| Discount rate | <value> | <provider> |
| Utility escalation | <value>/yr | <provider> |
| Hold period | <value> years | <provider> |
| Incentives | <list> | <provider> |

## 4. Existing Documents

| Document | Description / Filename | Provider | Status |
|----------|----------------------|---------|--------|
<One row per document>

## 5. Timeline & Milestones

| Milestone | Target | Notes |
|-----------|--------|-------|
| Report delivery | <date or timeframe> | |
| Construction start | <date or timeframe> | |
| Phasing constraints | — | <list constraints> |
| Funding deadline | <date or N/A> | |

## 6. Team & Point of Contact

| Role | Name / Firm | Contact |
|------|-------------|---------|
<One row per team member>

**Primary client contact:** <name> — <email>

---
*Generated by project-kickoff skill v1.0.0 — <date>*
```
```

- [ ] **Step 2: Verify the file was written**

```bash
wc -l ~/soapbox-agent/skills/project-kickoff/project-types/retrofit-analysis.md
```
Expected: > 100 lines.

- [ ] **Step 3: Commit**

```bash
cd ~/soapbox-agent
git add skills/project-kickoff/project-types/retrofit-analysis.md
git commit -m "feat(project-kickoff): add retrofit-analysis project type with 6 adapted questions and output template"
```

---

### Task 3: Smoke test — AvalonBay retrofit analysis kickoff

This task runs the skill end-to-end to verify it works before claiming done.

**Files:**
- Verify: `skills/project-kickoff/SKILL.md`
- Verify: `skills/project-kickoff/project-types/retrofit-analysis.md`
- Creates (if test passes): `projects/avalonbay/retrofit-analysis-kickoff.md`

**Interfaces:**
- Consumes: Both files from Tasks 1 and 2

- [ ] **Step 1: Invoke the skill**

In a Claude Code session, invoke:
> "Kick off a retrofit analysis project for AvalonBay."

- [ ] **Step 2: Verify invocation parsing**

The skill should:
- Infer project type: Retrofit Analysis (no question asked)
- Infer asset name: AvalonBay → key `avalonbay`
- Infer scope: asset-level

If it asks for project type or asset name unnecessarily, the inference logic needs fixing.

- [ ] **Step 3: Verify pre-flight runs**

The skill should run the bash scan without asking. Confirm it reports what it found
(or reports nothing found) before asking Q1.

- [ ] **Step 4: Verify Q&A — one question at a time**

Work through all 6 questions. Verify:
- Each question arrives separately (never two at once)
- Options match the retrofit-analysis.md definitions
- Pre-flight findings surface correctly in Q2 and Q4

- [ ] **Step 5: Verify output file**

After confirming answers, check the file was written:
```bash
cat ~/soapbox-agent/projects/avalonbay/retrofit-analysis-kickoff.md
```

Expected: File exists with all 6 sections populated + executive summary at top.

- [ ] **Step 6: Verify re-run behavior**

Run the skill again for the same asset:
> "Kick off a retrofit analysis project for AvalonBay."

Expected: The skill detects the existing file and asks Overwrite vs Create new before
proceeding with Q&A.

- [ ] **Step 7: Commit the test output**

```bash
cd ~/soapbox-agent
git add projects/avalonbay/retrofit-analysis-kickoff.md
git commit -m "test(project-kickoff): avalonbay smoke test output"
```
