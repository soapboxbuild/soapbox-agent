---
name: project-kickoff
description: >
  Interactive project kickoff for real-time client sessions. Captures goal, data sources,
  financial assumptions, existing documents, timeline, and team for any project type.
  Adapts questions to the project type. Checks existing asset data before requesting it.
  Saves a structured + narrative project file to projects/<asset-key>/.
  Triggers on: "kick off", "project kickoff", "start a project", "kickoff for",
  "begin a [type] project", "run a kickoff", "kickoff [asset]",
  "run a portfolio analysis", "run portfolio analysis", "analyze the portfolio",
  "portfolio decarbonization", "portfolio analysis".
version: 1.1.0
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

| Trigger keywords | Project Type | Type key | Default scope |
|-----------------|-------------|----------|---------------|
| retrofit, retrofit analysis, energy retrofit, mechanical retrofit, building retrofit | Retrofit Analysis | retrofit-analysis | asset |
| portfolio analysis, run portfolio analysis, analyze portfolio, analyze the portfolio, portfolio decarbonization | Portfolio Analysis | portfolio-analysis | portfolio |

If the project type does not match any entry: ask via AskUserQuestion:
> "What type of project are we kicking off?"
> Options: Retrofit Analysis | Portfolio Analysis | Other (describe)

**For `portfolio-analysis` type:** scope is always **portfolio** — do not ask the scope question.
The "asset name" becomes the portfolio or client name (e.g. "Greystar Q3" or "BCLC").
If no client/portfolio name is given: ask via AskUserQuestion free text:
> "What is the name of this portfolio or client?"

**For all other types:** if the asset name is missing from the invocation: ask via AskUserQuestion free text:
> "What is the name of the asset (or portfolio)?"

If scope is ambiguous (non-portfolio-analysis type): ask via AskUserQuestion:
> "Is this for a single asset or a portfolio?"
> Options: Single asset | Portfolio

Ask each of these one at a time; do not ask the next until the previous is answered.

**Derive asset key:** lowercase the name, replace spaces with hyphens.
Examples: "AvalonBay" → `avalonbay` | "Prose Frontier OM" → `prose-frontier-om`

**Load project type definition:**
```bash
cat skills/project-kickoff/project-types/<type-key>.md
```
Follow the question definitions in that file for Steps 3–4.

---

## Step 2: Pre-flight Data Scan

**For `portfolio-analysis` type:** Skip the bash scans below. Instead, follow the pre-flight
instructions at the top of `skills/project-kickoff/project-types/portfolio-analysis.md` —
they use portfolio MCP tools (`query_portfolio_data`, `search_portfolio`) rather than
filesystem commands. Then return here for re-run handling and proceed to the Q&A loop.

**For all other project types**, scan for existing data before asking any questions. Run:

```bash
ls .cashflow-models/<asset-key>.json 2>/dev/null && echo "HAS_CASHFLOW" || true
ls projects/<asset-key>/<type-key>-kickoff.md 2>/dev/null && echo "HAS_PRIOR_KICKOFF" || true
ls projects/<asset-key>/ 2>/dev/null || true
find . -maxdepth 5 -path "*<asset-key>*" \( \
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

> **Portfolio scope note:** For portfolio-level kickoffs, `has_prior_kickoff` checks
> `projects/portfolio/<type-key>-kickoff.md`. The timestamped version writes to
> `projects/portfolio/<type-key>-kickoff-YYYY-MM-DD.md`.

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
# Asset scope:
mkdir -p projects/<asset-key>/
# Portfolio scope:
mkdir -p projects/portfolio/
```

Write the file using the output template from the project type file, filling in all
answers from the Q&A loop.

Confirm to the user, citing the exact output path computed above:
> "Project kickoff saved to `<output path>`.
> This file will be used as the project reference throughout delivery."
