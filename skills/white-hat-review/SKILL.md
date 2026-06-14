---
name: white-hat-review
description: >
  Use after any agent-generated report, analysis, or recommendation to critically
  review its accuracy, flag unsupported claims, verify numbers against source
  documents, and suggest corrections. Triggers on: "review this report", "check
  this analysis", "is this correct", "fact-check this", "how confident are you",
  "white hat review", or proactively when a major report has just been generated.
version: 1.0.0
---

# White Hat Review

Skeptically audit any agent-generated output — report, analysis, artifact, or recommendation — before it leaves the conversation. The goal is not to be difficult but to catch errors before they reach clients or inform decisions.

**Default posture:** Assume numbers are wrong until confirmed against a source. Assume methodology claims need a citation. Assume omissions are meaningful.

---

## Step 1: Obtain the Output to Review

If the user hasn't provided it explicitly:
- Check for artifacts created in this conversation (`preview_file` or prior tool results)
- Ask: "Which report or analysis should I review? I can see [list recent artifacts/outputs]."

---

## Step 2: Structured Critique

Work through the output section by section. For each claim, assign a verdict:

| Symbol | Meaning |
|--------|---------|
| ✓ | Verified against source document or widely accepted standard |
| ⚠ | Plausible but unverified — needs a reference |
| ✗ | Appears incorrect or contradicted by source material |
| ? | Cannot assess without more data |

### What to check

**Numbers and calculations**
- Are units consistent throughout? (kWh vs MWh, $/sqft vs $/sqm, tCO₂ vs tCO₂e)
- Do totals add up? Spot-check 2–3 calculations by hand.
- Are percentage changes directionally correct? (A → B: if A=100 and B=120, increase is 20%, not 20% → correct; if B=80, it's a 20% decrease)
- Are benchmarks appropriate for building type, location, and vintage?

**Claims and assertions**
- Every "this building will save X tons" needs: methodology + baseline assumption + projection year
- Regulatory claims ("this building violates LL97") need: the specific penalty calculation and the threshold it crosses
- "Best practice" claims need a source (ASHRAE, CRREM, EPA, local code)

**Methodology**
- Is the correct standard cited? (CRREM v2.05 not v1, Local Law 97 not BEPS, etc.)
- Is the baseline period correct? (12 months of actual data, not estimated)
- Are emission factors appropriate for the utility/location/year?
- Is the carbon pathway correct for the building type and jurisdiction?

**Omissions**
- Missing caveats about data quality (e.g. estimated vs metered data)
- No uncertainty range on projections
- Compliance analysis that ignores tenant vs landlord scope split
- Financial analysis without discount rate or inflation assumption

---

## Step 3: Verify Key Claims Against Source Documents

For each ⚠ or ✗ finding, use tools to verify:

1. `search_documents("query")` — search indexed documents for supporting evidence
2. `search_files("keyword")` — find the specific bill, report, or survey that should support the claim
3. `read_file(storage_path)` — pull the actual numbers from source

Document what you find:
```
Claim: "Electricity consumption is 2.4M kWh/year"
Source checked: SCL bill January 2024 (read_file)
Finding: ⚠ Jan–Jun 2024 = 1.1M kWh (annualised = ~2.2M kWh, not 2.4M)
Recommendation: Re-check full 12-month total; clarify data period used
```

---

## Step 4: Reference Check for Standards and Regulations

For claims about codes, standards, or regulations:
- State which version of the standard applies and whether the report uses it correctly
- Flag if a newer version exists that might change the conclusion
- Note if a jurisdiction-specific variation applies (e.g. NYC LL97 ≠ Washington BEPS ≠ Seattle Building Tune-Up)

Common areas where agents err:
- CRREM pathways: wrong building use type selected (office vs mixed-use changes the pathway)
- Local Law 97: using the wrong threshold year (2024 vs 2030 limits differ)
- ENERGY STAR scores: wrong reference building vintage or climate zone
- Emission factors: using national average when a state/utility-specific factor exists

---

## Step 5: Deliver the Review

Format the review as a structured document:

```
## White Hat Review — [Report Title]
Reviewed: [date]
Overall confidence: [HIGH / MEDIUM / LOW]

### Critical Issues (must fix before distribution)
[✗ findings that change conclusions or contain factual errors]

### Cautions (should fix or caveat)
[⚠ findings — unverified claims, missing methodology, unsupported numbers]

### Verified Claims
[✓ items confirmed against source — brief list]

### Recommended Additions
[what would make this report stronger: missing caveats, additional sources, 
ranges instead of point estimates, sensitivity analysis]

### Suggested Edits
[specific text changes, numbered]
```

---

## Rules

- Never accept a number as correct just because an agent generated it
- Always check at least 3 numerical claims against source documents
- If source documents are unavailable to verify a claim, mark it ⚠ and say why
- Do not soften findings to be polite — name errors clearly
- Distinguish between "wrong" (verifiably incorrect) and "unverified" (could be right, no source found)
- If you cannot access a reference needed to verify a claim, say so explicitly rather than defaulting to ✓
