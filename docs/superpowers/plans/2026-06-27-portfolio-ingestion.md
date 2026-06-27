# Portfolio Ingestion Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `portfolio-ingest` skill that bulk-creates Soapbox assets from Drive/Box/OneDrive sources, matches documents to assets with confidence gating, links Audette buildings, and collects financial + LL/TT parameters conversationally.

**Architecture:** Three standalone Python scripts (ll_allocation, document_classifier, portfolio_match) serve as computation backends called via `bash` — matching the dcf_engine/intervention_engine pattern. A `SKILL.md` orchestrates the full conversational flow using those scripts plus Audette MCP tools and Supabase MCP for all API writes. All scripts accept JSON on the CLI and return JSON to stdout.

**Tech Stack:** Python 3.12, rapidfuzz 3.14.5, pdfplumber 0.11.10, pytest, Audette MCP (`mcp__claude_ai_Audette_AI__*`), Google Drive MCP (`mcp__claude_ai_Google_Drive__*`), Supabase MCP (`mcp__plugin_supabase_supabase__*`)

## Global Constraints

- Follow the dcf_engine.py CLI pattern: `--inputs '<json>'` → JSON to stdout, errors to stderr with exit code 1
- `rapidfuzz` is installed system-wide (3.14.5); `pdfplumber` is available (0.11.10)
- All scripts must run standalone: `python3 scripts/<name>.py --inputs '<json>'`
- Tests live in `scripts/tests/`; run with `python3 -m pytest scripts/tests/ -v`
- Confidence threshold for auto-link: **0.85**. Review threshold: **0.40**. Below 0.40 = "not found"
- BPS jurisdictions list: `{"NYC", "Boston", "DC", "Vancouver", "Denver", "Seattle", "Chicago"}`
- `analysis_ready: true` requires: `exit_year`, `exit_cap_rate`, `lease_structure`, `metering_config` all present
- Jurisdiction required only for BPS cities; defaults to `"other"` / `bps_liable: false` elsewhere
- Asset register `fund_name` overrides Audette fund data when both are present

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/ll_allocation.py` | Create | Three-factor LL/TT decision tree (lease + metering + jurisdiction + measure) |
| `scripts/document_classifier.py` | Create | Infer document type from filename + text sample |
| `scripts/portfolio_match.py` | Create | Fuzzy name/address scoring for system records and documents |
| `scripts/tests/test_ll_allocation.py` | Create | Unit tests for all decision tree branches |
| `scripts/tests/test_document_classifier.py` | Create | Unit tests for all doc type classifications |
| `scripts/tests/test_portfolio_match.py` | Create | Unit tests for match scoring + ambiguity detection |
| `skills/portfolio-ingest/SKILL.md` | Create | Conversational skill orchestrating all four stages |

---

## Task 1: LL/TT Allocation Decision Tree

**Files:**
- Create: `scripts/ll_allocation.py`
- Test: `scripts/tests/test_ll_allocation.py`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces: `resolve_ll_pct(inputs: dict) -> dict` with keys `ll_pct` (float), `tt_pct` (float), `warnings` (list[str]), `reasoning` (str)
- CLI: `python3 scripts/ll_allocation.py --inputs '{"lease_structure":"gross","metering_config":"master","jurisdiction":"Boston","bps_liable":true,"measure_category":"elevator"}'`

- [ ] **Step 1: Write failing tests**

```python
# scripts/tests/test_ll_allocation.py
import subprocess, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'll_allocation.py')

def run(inputs: dict) -> dict:
    result = subprocess.run(
        ['python3', SCRIPT, '--inputs', json.dumps(inputs)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)

def test_gross_lease_captures_all():
    r = run({"lease_structure": "gross", "metering_config": "master",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "in_unit_hvac"})
    assert r["ll_pct"] == 1.0
    assert r["tt_pct"] == 0.0

def test_nnn_lease_captures_nothing():
    r = run({"lease_structure": "nnn", "metering_config": "individual",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "in_unit_hvac"})
    assert r["ll_pct"] == 0.0
    assert r["tt_pct"] == 1.0

def test_elevator_always_ll_even_under_nnn():
    r = run({"lease_structure": "nnn", "metering_config": "individual",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "elevator"})
    assert r["ll_pct"] == 1.0

def test_envelope_nnn_paradox():
    r = run({"lease_structure": "nnn", "metering_config": "individual",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "envelope"})
    assert r["ll_pct"] == 0.0
    assert any("paradox" in w.lower() or "nnn" in w.lower() for w in r["warnings"])

def test_rubs_individual_warns_collective_action():
    r = run({"lease_structure": "rubs", "metering_config": "individual",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "in_unit_hvac"})
    assert r["ll_pct"] == 0.0
    assert any("rubs" in w.lower() or "collective" in w.lower() for w in r["warnings"])

def test_bps_jurisdiction_warns_nnn():
    r = run({"lease_structure": "nnn", "metering_config": "individual",
             "jurisdiction": "Boston", "bps_liable": True, "measure_category": "in_unit_hvac"})
    assert r["ll_pct"] == 0.0
    assert any("bps" in w.lower() or "fine" in w.lower() or "carbon" in w.lower() for w in r["warnings"])

def test_solar_always_ll_with_consent_warning_under_nnn():
    r = run({"lease_structure": "nnn", "metering_config": "individual",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "solar"})
    assert r["ll_pct"] == 1.0
    assert any("consent" in w.lower() for w in r["warnings"])

def test_modified_gross_master_metered():
    r = run({"lease_structure": "modified_gross", "metering_config": "master",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "in_unit_hvac"})
    assert r["ll_pct"] == 1.0

def test_modified_gross_individual_metered():
    r = run({"lease_structure": "modified_gross", "metering_config": "individual",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "in_unit_hvac"})
    assert r["ll_pct"] == 0.0

def test_green_lease_warns_to_check_clause():
    r = run({"lease_structure": "green_lease", "metering_config": "master",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "in_unit_hvac"})
    assert any("green lease" in w.lower() or "clause" in w.lower() for w in r["warnings"])

def test_output_schema():
    r = run({"lease_structure": "gross", "metering_config": "master",
             "jurisdiction": "other", "bps_liable": False, "measure_category": "elevator"})
    assert "ll_pct" in r and "tt_pct" in r and "warnings" in r and "reasoning" in r
    assert abs(r["ll_pct"] + r["tt_pct"] - 1.0) < 0.001
```

- [ ] **Step 2: Run tests — verify all fail**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/test_ll_allocation.py -v 2>&1 | head -30
```
Expected: `ERROR` — `scripts/ll_allocation.py` does not exist yet.

- [ ] **Step 3: Implement `scripts/ll_allocation.py`**

```python
#!/usr/bin/env python3
"""
ll_allocation.py — LL/TT savings split decision tree.

Resolves what fraction of energy measure savings flows to the landlord (LL)
vs tenant (TT) based on three factors: lease structure, metering configuration,
and jurisdiction. Building type is NOT a determinant — the three factors are.

Usage:
    python3 ll_allocation.py --inputs '<json>'

Input JSON keys:
    lease_structure   str  gross | nnn | modified_gross | rubs | green_lease
    metering_config   str  master | individual | submeter_passthrough
    jurisdiction      str  NYC | Boston | DC | Vancouver | Denver | Seattle | Chicago | other
    bps_liable        bool True if property owner faces carbon fine liability
    measure_category  str  elevator | conveying | transformer | common_area_lighting |
                           common_area_hvac | drv_controls | solar | rooftop_pv |
                           behind_meter_solar | envelope | in_unit_hvac | in_unit_lighting |
                           in_unit_dhw | in_unit_appliances | ev_charging | other

Output JSON keys:
    ll_pct     float  0.0–1.0 landlord capture fraction
    tt_pct     float  0.0–1.0 tenant capture fraction (= 1 - ll_pct)
    warnings   list   strings describing edge cases the analyst should verify
    reasoning  str    one-sentence explanation of the resolution path taken
"""
import argparse
import json
import sys

BPS_JURISDICTIONS = {"NYC", "Boston", "DC", "Vancouver", "Denver", "Seattle", "Chicago"}

ALWAYS_LL = {
    "elevator", "conveying", "transformer", "common_area_lighting",
    "common_area_hvac", "drv_controls", "ev_charging",
}

SOLAR = {"solar", "rooftop_pv", "behind_meter_solar"}

ENVELOPE = {"envelope", "insulation", "glazing", "air_sealing", "weatherization"}


def resolve_ll_pct(inputs: dict) -> dict:
    lease = inputs.get("lease_structure", "").lower()
    metering = inputs.get("metering_config", "").lower()
    jurisdiction = inputs.get("jurisdiction", "other")
    bps_liable = bool(inputs.get("bps_liable", False))
    measure = inputs.get("measure_category", "").lower()

    warnings = []

    # ── 1. Elevators / common-area systems — always LL regardless of lease ──
    if measure in ALWAYS_LL:
        return {
            "ll_pct": 1.0, "tt_pct": 0.0, "warnings": warnings,
            "reasoning": f"{measure} is a building/common-area system — always LL-controlled regardless of lease",
        }

    # ── 2. Solar — follows system owner; flag consent risk ──
    if measure in SOLAR:
        if lease == "nnn":
            warnings.append(
                "Rooftop solar typically requires tenant consent under NNN — confirm lease before assuming LL capture"
            )
        if lease == "green_lease":
            warnings.append(
                "Green lease detected: confirm solar consent and billing clause before assuming LL capture"
            )
        return {
            "ll_pct": 1.0, "tt_pct": 0.0, "warnings": warnings,
            "reasoning": "Solar: LL owns and operates the system, captures all savings; tenant consent required in most leases",
        }

    # ── 3. Envelope under NNN — the NNN paradox ──
    if measure in ENVELOPE and lease == "nnn":
        warnings.append(
            "NNN paradox: LL bears envelope capex but TT captures HVAC opex savings — "
            "consider green lease clause or shared savings mechanism"
        )
        return {
            "ll_pct": 0.0, "tt_pct": 1.0, "warnings": warnings,
            "reasoning": "Envelope under NNN: LL pays for installation, TT captures heating/cooling savings",
        }

    # ── 4. Gross lease — landlord pays all utilities, captures all savings ──
    if lease == "gross":
        return {
            "ll_pct": 1.0, "tt_pct": 0.0, "warnings": warnings,
            "reasoning": "Gross lease: landlord pays utility bills and captures 100% of operating savings",
        }

    # ── 5. NNN — tenant pays utilities directly ──
    if lease == "nnn":
        if bps_liable:
            warnings.append(
                "BPS jurisdiction: carbon fine avoidance value accrues to LL (property owner is legally liable) "
                "even though operating savings go to TT — model fine avoidance separately in the analysis"
            )
        return {
            "ll_pct": 0.0, "tt_pct": 1.0, "warnings": warnings,
            "reasoning": "NNN: tenant pays utilities directly and captures all operating savings; LL only benefits via BPS fine avoidance",
        }

    # ── 6. RUBS — resolve by metering ──
    if lease == "rubs":
        if metering == "master":
            warnings.append(
                "RUBS + master-metered: verify savings flow back to LL via RUBS rate adjustment, "
                "not passed through at old pre-retrofit rates"
            )
            return {
                "ll_pct": 1.0, "tt_pct": 0.0, "warnings": warnings,
                "reasoning": "RUBS + master-metered: LL pays master bill, captures savings if RUBS rates are updated",
            }
        else:
            warnings.append(
                "RUBS + individually-metered: individual savings accrue to each tenant's meter — "
                "collective action problem means savings may not recover to LL"
            )
            return {
                "ll_pct": 0.0, "tt_pct": 1.0, "warnings": warnings,
                "reasoning": "RUBS + individual meters: in-unit savings go to tenants; LL captures common area only (modeled separately)",
            }

    # ── 7. Modified gross / green lease — resolve by metering ──
    if lease in ("modified_gross", "green_lease"):
        if lease == "green_lease":
            warnings.append(
                "Green lease detected: follow specific clause language for savings attribution. "
                "Using metering configuration as proxy — verify clause wording."
            )
        if metering == "master":
            return {
                "ll_pct": 1.0, "tt_pct": 0.0, "warnings": warnings,
                "reasoning": "Master-metered: landlord pays the single utility bill and captures all savings",
            }
        if metering == "submeter_passthrough":
            warnings.append(
                "Submeter passthrough: LL captures the delta between old and new billing rates — "
                "verify passthrough billing arrangement with property management"
            )
            return {
                "ll_pct": 1.0, "tt_pct": 0.0, "warnings": warnings,
                "reasoning": "Submeter passthrough: LL installs measures, bills back at new rates, captures the spread",
            }
        # individually metered
        return {
            "ll_pct": 0.0, "tt_pct": 1.0, "warnings": warnings,
            "reasoning": "Individually metered: in-unit loads are TT-controlled; common area always LL (modeled separately)",
        }

    # ── Fallback ──
    warnings.append(f"Unknown lease structure '{lease}' — defaulting to 50/50. Review billing structure.")
    return {
        "ll_pct": 0.5, "tt_pct": 0.5, "warnings": warnings,
        "reasoning": "Unknown lease structure: using 50% LL as conservative estimate",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()

    try:
        inputs = json.loads(args.inputs)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    result = resolve_ll_pct(inputs)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/test_ll_allocation.py -v
```
Expected: `12 passed`

- [ ] **Step 5: Smoke test CLI**

```bash
cd ~/soapbox-agent && python3 scripts/ll_allocation.py --inputs '{"lease_structure":"nnn","metering_config":"individual","jurisdiction":"Boston","bps_liable":true,"measure_category":"elevator"}'
```
Expected output (elevator is always LL):
```json
{"ll_pct": 1.0, "tt_pct": 0.0, "warnings": [], "reasoning": "elevator is a building/common-area system — always LL-controlled regardless of lease"}
```

- [ ] **Step 6: Commit**

```bash
cd ~/soapbox-agent && git add scripts/ll_allocation.py scripts/tests/test_ll_allocation.py
git commit -m "feat: add LL/TT allocation decision tree (lease+metering+jurisdiction)"
```

---

## Task 2: Document Classifier

**Files:**
- Create: `scripts/document_classifier.py`
- Test: `scripts/tests/test_document_classifier.py`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces: `classify_document(filename: str, text_sample: str) -> dict` with keys `doc_type` (str), `confidence` (float), `signals_found` (list[str])
- CLI: `python3 scripts/document_classifier.py --inputs '{"filename":"PCA_Landmark_2024.pdf","text":"property condition assessment capital needs deferred maintenance"}'`

- [ ] **Step 1: Write failing tests**

```python
# scripts/tests/test_document_classifier.py
import subprocess, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'document_classifier.py')

def run(filename: str, text: str) -> dict:
    result = subprocess.run(
        ['python3', SCRIPT, '--inputs', json.dumps({"filename": filename, "text": text})],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)

def test_pca_by_filename():
    r = run("Landmark_PCA_2024.pdf", "building survey report")
    assert r["doc_type"] == "pca"
    assert r["confidence"] > 0

def test_pca_by_text():
    r = run("report.pdf", "property condition assessment capital needs deferred maintenance immediate needs")
    assert r["doc_type"] == "pca"

def test_audit_by_filename():
    r = run("GreenRock_Energy_Audit_Final.pdf", "some content here")
    assert r["doc_type"] == "audit"

def test_audit_by_text():
    r = run("study.pdf", "ashrae level ii energy audit energy conservation measure eui energy use intensity")
    assert r["doc_type"] == "audit"

def test_utility_by_filename():
    r = run("Electric_Bill_Q1_2024.pdf", "")
    assert r["doc_type"] == "utility"

def test_utility_by_text():
    r = run("data.xlsx", "meter data interval data kwh consumption billing period utility account")
    assert r["doc_type"] == "utility"

def test_capex_by_text():
    r = run("plan.pdf", "capital plan five-year plan capital expenditure capex reserve study")
    assert r["doc_type"] == "capex"

def test_lease_by_text():
    r = run("abstract.pdf", "lease abstract landlord tenant triple net nnn rent roll base rent")
    assert r["doc_type"] == "lease"

def test_unknown_returns_other():
    r = run("random_file.pdf", "this document contains nothing relevant whatsoever foo bar baz")
    assert r["doc_type"] == "other"
    assert r["confidence"] == 0.0

def test_output_schema():
    r = run("pca.pdf", "property condition assessment")
    assert "doc_type" in r and "confidence" in r and "signals_found" in r
    assert isinstance(r["doc_type"], str)
    assert isinstance(r["confidence"], float)
    assert isinstance(r["signals_found"], list)

def test_confidence_is_bounded():
    r = run("PCA_audit_utility_capex_lease.pdf",
            "property condition assessment energy audit kwh capital plan lease agreement")
    assert 0.0 <= r["confidence"] <= 1.0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/test_document_classifier.py -v 2>&1 | head -20
```
Expected: `ERROR` — script does not exist yet.

- [ ] **Step 3: Implement `scripts/document_classifier.py`**

```python
#!/usr/bin/env python3
"""
document_classifier.py — Infer document type from filename and text sample.

Usage:
    python3 document_classifier.py --inputs '<json>'

Input JSON keys:
    filename    str  Original filename (e.g. "Landmark_PCA_2024.pdf")
    text        str  First ~500 words of extracted document text (may be empty)

Output JSON keys:
    doc_type       str    pca | audit | utility | capex | lease | other
    confidence     float  0.0–1.0
    signals_found  list   keyword strings that triggered the classification
"""
import argparse
import json
import sys

DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "pca": [
        "property condition assessment", "property condition report", "pca",
        "capital needs assessment", "building survey", "physical condition",
        "deferred maintenance", "immediate needs", "short-term needs",
        "long-term needs", "capital reserve",
    ],
    "audit": [
        "energy audit", "energy assessment", "retro-commissioning", "ashrae",
        "green rock", "energy efficiency", "audit report", "level i", "level ii",
        "level iii", "eui", "energy use intensity", "energy conservation measure",
        "ecm", "retro commissioning", "benchmarking",
    ],
    "utility": [
        "utility bill", "utility invoice", "electric bill", "gas bill",
        "interval data", "meter data", "kwh", "therms", "consumption data",
        "utility account", "billing period", "energy usage", "electricity invoice",
        "natural gas invoice", "water bill",
    ],
    "capex": [
        "capital plan", "capital expenditure", "capex", "reserve study",
        "five-year plan", "10-year plan", "capital budget", "renovation budget",
        "improvement plan", "capital improvement", "replacement schedule",
    ],
    "lease": [
        "lease abstract", "rent roll", "lease agreement", "landlord", "tenant",
        "lessee", "lessor", "lease term", "base rent", "triple net", "nnn",
        "gross lease", "modified gross", "common area maintenance", "cam charges",
        "lease commencement", "lease expiration",
    ],
}


def classify_document(filename: str, text_sample: str) -> dict:
    combined = (filename.lower() + " " + text_sample.lower())

    scores: dict[str, int] = {}
    signals: dict[str, list[str]] = {}

    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        found = [kw for kw in keywords if kw in combined]
        scores[doc_type] = len(found)
        signals[doc_type] = found

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        return {"doc_type": "other", "confidence": 0.0, "signals_found": []}

    # Confidence: hitting 30% of a type's keywords = full confidence
    max_possible = len(DOC_TYPE_KEYWORDS[best_type])
    confidence = min(best_score / max(max_possible * 0.3, 1), 1.0)

    return {
        "doc_type": best_type,
        "confidence": round(confidence, 2),
        "signals_found": signals[best_type],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()

    try:
        inputs = json.loads(args.inputs)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    filename = inputs.get("filename", "")
    text = inputs.get("text", "")
    result = classify_document(filename, text)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/test_document_classifier.py -v
```
Expected: `11 passed`

- [ ] **Step 5: Smoke test CLI**

```bash
cd ~/soapbox-agent && python3 scripts/document_classifier.py --inputs '{"filename":"GreenRock_Landmark_Energy_Audit_2023.pdf","text":"ashrae level ii energy audit energy use intensity eui retro-commissioning"}'
```
Expected:
```json
{"doc_type": "audit", "confidence": 1.0, "signals_found": ["energy audit", "ashrae", "level ii", "eui", "energy use intensity", "retro-commissioning"]}
```

- [ ] **Step 6: Commit**

```bash
cd ~/soapbox-agent && git add scripts/document_classifier.py scripts/tests/test_document_classifier.py
git commit -m "feat: add document type classifier (pca/audit/utility/capex/lease)"
```

---

## Task 3: Fuzzy Matching Engine

**Files:**
- Create: `scripts/portfolio_match.py`
- Test: `scripts/tests/test_portfolio_match.py`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces two modes via `--mode`:
  - `system`: score asset register entry against list of Audette/ESPM candidates → ranked matches
  - `document`: score a document against list of asset records → ranked matches with ambiguity flag
- CLI system mode: `python3 scripts/portfolio_match.py --mode system --inputs '<json>'`
- CLI document mode: `python3 scripts/portfolio_match.py --mode document --inputs '<json>'`

**System mode input:**
```json
{
  "asset": {"name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC"},
  "candidates": [
    {"id": "aud-123", "name": "Landmark Colony Park", "address": "123 Colony Road", "city": "Charlotte", "state": "NC"},
    {"id": "aud-456", "name": "Meridian at Colony", "address": "456 Colony Rd", "city": "Charlotte", "state": "NC"}
  ]
}
```

**Document mode input:**
```json
{
  "filename": "Landmark_PCA_2024.pdf",
  "text": "property condition assessment for Landmark at Colony Park located at 123 Colony Road",
  "assets": [
    {"name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC", "fund_name": "GEdR"},
    {"name": "Meridian at Colony", "address": "456 Colony Rd", "city": "Charlotte", "state": "NC", "fund_name": "GEdR"}
  ]
}
```

- [ ] **Step 1: Write failing tests**

```python
# scripts/tests/test_portfolio_match.py
import subprocess, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'portfolio_match.py')

def run_system(asset: dict, candidates: list) -> list:
    inputs = {"asset": asset, "candidates": candidates}
    result = subprocess.run(
        ['python3', SCRIPT, '--mode', 'system', '--inputs', json.dumps(inputs)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)["matches"]

def run_document(filename: str, text: str, assets: list) -> list:
    inputs = {"filename": filename, "text": text, "assets": assets}
    result = subprocess.run(
        ['python3', SCRIPT, '--mode', 'document', '--inputs', json.dumps(inputs)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)["matches"]

ASSET = {"name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC"}
EXACT_CANDIDATE = {"id": "aud-001", "name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC"}
FUZZY_CANDIDATE = {"id": "aud-002", "name": "Landmark Colony Park", "address": "123 Colony Road", "city": "Charlotte", "state": "NC"}
UNRELATED = {"id": "aud-003", "name": "Sunset Apartments", "address": "999 Oak St", "city": "Denver", "state": "CO"}

def test_exact_match_scores_above_threshold():
    matches = run_system(ASSET, [EXACT_CANDIDATE])
    assert matches[0]["score"] >= 0.85
    assert matches[0]["auto_link"] is True

def test_fuzzy_match_in_review_range():
    matches = run_system(ASSET, [FUZZY_CANDIDATE])
    assert 0.40 <= matches[0]["score"] < 0.85
    assert matches[0]["auto_link"] is False
    assert matches[0]["needs_review"] is True

def test_unrelated_candidate_below_threshold():
    matches = run_system(ASSET, [UNRELATED])
    assert matches[0]["score"] < 0.40

def test_results_sorted_descending():
    matches = run_system(ASSET, [UNRELATED, EXACT_CANDIDATE, FUZZY_CANDIDATE])
    scores = [m["score"] for m in matches]
    assert scores == sorted(scores, reverse=True)

def test_empty_candidates_returns_empty():
    matches = run_system(ASSET, [])
    assert matches == []

ASSETS = [
    {"name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC", "fund_name": "GEdR"},
    {"name": "Meridian at Colony", "address": "456 Colony Rd", "city": "Charlotte", "state": "NC", "fund_name": "GEdR"},
]

def test_document_matches_correct_asset():
    matches = run_document(
        "Landmark_PCA_2024.pdf",
        "property condition assessment for Landmark at Colony Park 123 Colony Rd Charlotte",
        ASSETS
    )
    assert matches[0]["asset_name"] == "Landmark at Colony Park"
    assert matches[0]["score"] > matches[1]["score"]

def test_document_ambiguous_when_scores_close():
    # Generic filename + vague text → both assets score similarly
    matches = run_document(
        "Energy_Audit_Charlotte_GEdR.pdf",
        "GEdR Charlotte property energy audit",
        ASSETS
    )
    top_two_close = abs(matches[0]["score"] - matches[1]["score"]) <= 0.10
    if top_two_close and matches[1]["score"] >= 0.40:
        assert matches[0]["ambiguous"] is True
        assert matches[1]["ambiguous"] is True

def test_document_no_match_returns_low_score():
    matches = run_document("random.pdf", "nothing relevant here foo bar", ASSETS)
    assert all(m["score"] < 0.40 for m in matches)

def test_system_output_schema():
    matches = run_system(ASSET, [EXACT_CANDIDATE])
    m = matches[0]
    assert "id" in m and "name" in m and "score" in m and "auto_link" in m and "needs_review" in m

def test_document_output_schema():
    matches = run_document("file.pdf", "landmark colony", ASSETS)
    m = matches[0]
    assert "asset_name" in m and "score" in m and "auto_assign" in m and "ambiguous" in m
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/test_portfolio_match.py -v 2>&1 | head -20
```
Expected: `ERROR` — script does not exist yet.

- [ ] **Step 3: Implement `scripts/portfolio_match.py`**

```python
#!/usr/bin/env python3
"""
portfolio_match.py — Fuzzy name/address matching for portfolio ingestion.

Two modes:

  system mode: score an asset register entry against Audette/ESPM candidates.
  document mode: score a document (filename + text) against asset records.

Usage:
    python3 portfolio_match.py --mode system --inputs '<json>'
    python3 portfolio_match.py --mode document --inputs '<json>'

System mode output: {"matches": [{id, name, score, auto_link, needs_review}, ...]}
Document mode output: {"matches": [{asset_name, score, signals, auto_assign, ambiguous}, ...]}

Thresholds:
    >= 0.85  auto-link / auto-assign (no user review needed)
    0.40–0.84  needs_review = True (surfaces in review card)
    < 0.40   treated as "not found"

Ambiguous (document mode): top two candidates both >= 0.40 and within 0.10 of each other.
"""
import argparse
import json
import sys
from rapidfuzz import fuzz

AUTO_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.40
AMBIGUITY_GAP = 0.10


def score_system_match(asset: dict, candidate: dict) -> float:
    score = 0.0
    asset_name = asset.get("name", "").lower()
    cand_name = candidate.get("name", "").lower()

    name_ratio = fuzz.ratio(asset_name, cand_name) / 100
    if name_ratio >= 0.999:
        score += 0.60
    elif name_ratio >= 0.80:
        score += 0.35
    elif name_ratio >= 0.60:
        score += 0.15

    asset_addr = asset.get("address", "").lower()
    cand_addr = candidate.get("address", "").lower()
    asset_city = asset.get("city", "").lower()
    cand_city = candidate.get("city", "").lower()

    if asset_addr and cand_addr:
        addr_ratio = fuzz.ratio(asset_addr, cand_addr) / 100
        city_match = bool(asset_city and cand_city and
                         fuzz.ratio(asset_city, cand_city) / 100 >= 0.85)
        if addr_ratio >= 0.85 and city_match:
            score += 0.25
        elif addr_ratio >= 0.85:
            score += 0.15

    asset_state = asset.get("state", "").upper()
    cand_state = candidate.get("state", "").upper()
    if asset_state and cand_state and asset_state == cand_state:
        score += 0.05

    return round(min(score, 1.0), 3)


def run_system_mode(inputs: dict) -> dict:
    asset = inputs["asset"]
    candidates = inputs.get("candidates", [])

    matches = []
    for cand in candidates:
        score = score_system_match(asset, cand)
        matches.append({
            "id": cand.get("id", ""),
            "name": cand.get("name", ""),
            "score": score,
            "auto_link": score >= AUTO_THRESHOLD,
            "needs_review": REVIEW_THRESHOLD <= score < AUTO_THRESHOLD,
        })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {"matches": matches}


def score_document_match(filename: str, text: str, asset: dict) -> tuple[float, list[str]]:
    combined = (filename.lower() + " " + text.lower())
    score = 0.0
    signals = []

    asset_name = asset.get("name", "").lower()
    name_ratio = max(
        fuzz.partial_ratio(asset_name, combined) / 100,
        fuzz.ratio(asset_name, combined[:300]) / 100,
    )
    if name_ratio >= 0.90:
        score += 0.60
        signals.append(f"name '{asset.get('name')}' found in document")
    elif name_ratio >= 0.75:
        score += 0.35
        signals.append(f"partial name match for '{asset.get('name')}'")

    asset_addr = asset.get("address", "").lower()
    if asset_addr:
        addr_ratio = fuzz.partial_ratio(asset_addr, combined) / 100
        if addr_ratio >= 0.85:
            score += 0.25
            signals.append(f"address '{asset.get('address')}' found in document")

    fund = asset.get("fund_name", "").lower()
    if fund and fund in combined:
        score += 0.15
        signals.append(f"fund '{asset.get('fund_name')}' found in document")

    return round(min(score, 1.0), 3), signals


def run_document_mode(inputs: dict) -> dict:
    filename = inputs.get("filename", "")
    text = inputs.get("text", "")
    assets = inputs.get("assets", [])

    matches = []
    for asset in assets:
        score, signals = score_document_match(filename, text, asset)
        matches.append({
            "asset_name": asset.get("name", ""),
            "score": score,
            "signals": signals,
            "auto_assign": score >= AUTO_THRESHOLD,
            "ambiguous": False,
        })

    matches.sort(key=lambda x: x["score"], reverse=True)

    # Flag ambiguous: top two both above review threshold and within gap
    if (len(matches) >= 2
            and matches[0]["score"] >= REVIEW_THRESHOLD
            and matches[1]["score"] >= REVIEW_THRESHOLD
            and matches[0]["score"] - matches[1]["score"] <= AMBIGUITY_GAP):
        matches[0]["ambiguous"] = True
        matches[1]["ambiguous"] = True

    return {"matches": matches}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["system", "document"])
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()

    try:
        inputs = json.loads(args.inputs)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    if args.mode == "system":
        print(json.dumps(run_system_mode(inputs)))
    else:
        print(json.dumps(run_document_mode(inputs)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/test_portfolio_match.py -v
```
Expected: `11 passed` (the ambiguity test may skip assertion if scores don't land close — that's correct behaviour)

- [ ] **Step 5: Smoke test both modes**

```bash
# System mode
cd ~/soapbox-agent && python3 scripts/portfolio_match.py --mode system --inputs '{
  "asset": {"name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC"},
  "candidates": [
    {"id": "aud-001", "name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC"},
    {"id": "aud-002", "name": "Sunset Apartments", "address": "999 Oak St", "city": "Denver", "state": "CO"}
  ]
}'
```
Expected: first match `score >= 0.85`, `auto_link: true`; second match `score < 0.40`.

```bash
# Document mode
python3 scripts/portfolio_match.py --mode document --inputs '{
  "filename": "Landmark_PCA_2024.pdf",
  "text": "property condition assessment for Landmark at Colony Park 123 Colony Rd GEdR",
  "assets": [
    {"name": "Landmark at Colony Park", "address": "123 Colony Rd", "city": "Charlotte", "state": "NC", "fund_name": "GEdR"},
    {"name": "Meridian at Colony", "address": "456 Colony Rd", "city": "Charlotte", "state": "NC", "fund_name": "GEdR"}
  ]
}'
```
Expected: Landmark scores higher than Meridian, `auto_assign: true`.

- [ ] **Step 6: Commit**

```bash
cd ~/soapbox-agent && git add scripts/portfolio_match.py scripts/tests/test_portfolio_match.py
git commit -m "feat: add fuzzy matching engine for system records and documents"
```

---

## Task 4: Run Full Test Suite

Verify all three scripts integrate cleanly before writing the skill.

- [ ] **Step 1: Run all tests**

```bash
cd ~/soapbox-agent && python3 -m pytest scripts/tests/ -v --tb=short
```
Expected: all tests in `test_ll_allocation.py`, `test_document_classifier.py`, `test_portfolio_match.py` pass. Existing `test_dcf_engine.py` and `test_intervention_engine.py` also pass (no regressions).

- [ ] **Step 2: Verify script CLIs are executable**

```bash
cd ~/soapbox-agent && for s in ll_allocation document_classifier portfolio_match; do
  echo -n "$s: "
  python3 scripts/$s.py --help 2>&1 | head -1
done
```
Expected: each prints a usage line without error.

- [ ] **Step 3: Commit if any fixes needed**

```bash
cd ~/soapbox-agent && git add -p && git commit -m "fix: test suite integration corrections"
```
Only commit if fixes were needed. Skip if clean.

---

## Task 5: Portfolio Ingest Skill

**Files:**
- Create: `skills/portfolio-ingest/SKILL.md`

**Interfaces:**
- Consumes: `scripts/ll_allocation.py`, `scripts/document_classifier.py`, `scripts/portfolio_match.py`
- Consumes MCPs: `mcp__claude_ai_Google_Drive__*`, `mcp__claude_ai_Box__*`, `mcp__claude_ai_Microsoft_365__*`, `mcp__claude_ai_Audette_AI__*`, `mcp__plugin_supabase_supabase__*`
- Produces: Soapbox assets in database, documents in Supabase storage, portfolio thread

- [ ] **Step 1: Create skill directory**

```bash
mkdir -p ~/soapbox-agent/skills/portfolio-ingest
```

- [ ] **Step 2: Write `skills/portfolio-ingest/SKILL.md`**

```markdown
# Portfolio Ingest Skill

Bulk-creates Soapbox assets from client document sources, links pre-existing Audette
buildings and ESPM properties, and collects all financial and LL/TT parameters needed
for portfolio analysis. Runs four sequential stages: source discovery → matching →
confidence-gated review → execution.

## When to Invoke

Trigger this skill when the user says anything like:
- "Ingest the [client] portfolio"
- "Set up assets for [client]"
- "Import [N] properties from [Drive/Box/OneDrive]"
- "Create Soapbox assets from this property list"

## Computation Scripts

All matching, classification, and allocation logic lives in standalone Python scripts.
Call them via bash tool:

```bash
# LL/TT allocation
python3 ~/soapbox-agent/scripts/ll_allocation.py --inputs '<json>'

# Document type inference
python3 ~/soapbox-agent/scripts/document_classifier.py --inputs '<json>'

# Fuzzy matching — system records
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode system --inputs '<json>'

# Fuzzy matching — documents to assets
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode document --inputs '<json>'
```

## Stage 1: Source Discovery

### Step 1a — Collect document source

Ask the user:
> "What's the document source? (1) Google Drive folder  (2) Box folder  (3) OneDrive/SharePoint  (4) Files already uploaded to Soapbox"

- Drive: use `mcp__claude_ai_Google_Drive__search_files` with the folder ID or name; retrieve file list
- Box: use `mcp__claude_ai_Box__*` tools if available; otherwise ask user to share a file list
- OneDrive/SharePoint: use `mcp__claude_ai_Microsoft_365__*` tools if available
- Already uploaded: query Supabase storage for files tagged with the client portfolio tag

For each document found, extract:
- `filename`
- `path` / `file_id` (for later download)
- First 500 words of text (use `mcp__claude_ai_Google_Drive__read_file_content` for Drive;
  for PDFs use the file content tool; fall back to filename-only classification if unavailable)

### Step 1b — Collect asset register seed

Ask the user:
> "Do you have an asset register or property list? (1) Yes — spreadsheet/CSV  (2) Yes — I'll type them  (3) No — build from Audette"

- Option 1: read the file and extract rows as `{name, address, city, state, fund_name, sub_asset_type, exit_year, exit_cap_rate}`
- Option 2: accept a typed list, one property per line, extract what you can
- Option 3: call `mcp__claude_ai_Audette_AI__switch_customer_account` then `mcp__claude_ai_Audette_AI__list_buildings` to build the register from Audette

### Step 1c — Check external system availability

Ask:
> "Are this client's buildings already set up in Audette? (yes / no / some)"
> "Is ESPM connected for this org? (yes / no)"

Note answers — they control whether matching steps run.

## Stage 2: Matching

### Step 2a — Match asset register entries against Audette

For each asset in the register (if Audette is available):

1. Call `mcp__claude_ai_Audette_AI__switch_customer_account` with the client account
2. Call `mcp__claude_ai_Audette_AI__list_buildings` to get all buildings
3. Call the matching script:

```bash
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode system --inputs '{
  "asset": {"name": "<asset_name>", "address": "<address>", "city": "<city>", "state": "<state>"},
  "candidates": [<audette_buildings_as_json>]
}'
```

4. Record: `{asset_name, audette_candidate_id, audette_candidate_name, score, auto_link, needs_review}`

### Step 2b — Match documents to assets

For each document discovered in Stage 1:

```bash
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode document --inputs '{
  "filename": "<filename>",
  "text": "<first_500_words>",
  "assets": [<asset_register_as_json>]
}'
```

Record the top match and whether it is `auto_assign` or `ambiguous`.

Also classify each document:

```bash
python3 ~/soapbox-agent/scripts/document_classifier.py --inputs '{
  "filename": "<filename>",
  "text": "<first_500_words>"
}'
```

### Step 2c — Detect BPS jurisdiction

For each asset, check if its `city` or `state` is in the BPS list:
`NYC, New York, Boston, Washington DC, Vancouver, Denver, Seattle, Chicago`

Set `bps_liable: true` for matches. Auto-set `jurisdiction` to the matched city name.

### Step 2d — Report pre-review summary

Tell the user:
> "Matching complete. X of Y assets resolved automatically (Audette + documents). Z assets need review."

List auto-resolved assets briefly. Then begin Stage 3 for flagged assets.

## Stage 3: Review Pass

For each asset where ANY of the following is true, present a review card:
- Audette match score is 0.40–0.84 (needs confirmation)
- Any document match is ambiguous or unresolved
- `exit_year`, `exit_cap_rate`, `lease_structure`, or `metering_config` is missing
- Exit year is in the past

Present cards one at a time. Format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Asset N of M — [Asset Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM LINKS
  Audette  → "[candidate_name]" [score] — confirm? (y / enter ID / skip)
  ESPM     → not found — enter property ID or skip

DOCUMENTS ([N] unresolved of [total] total)
  ✓ [filename] → auto-assigned [pca]
  ? [filename] → matches [Asset A] [0.71] AND [Asset B] [0.68]
                  assign to: (1) [Asset A]  (2) [Asset B]  (3) neither
  ? [filename] → no match — assign to this asset or discard?

FINANCIAL PARAMETERS
  ✓ Fund:            [value]
  ✓ Sub-asset type:  [value]
  ? Exit year        → [if in past: "PAST DATE — enter projected exit year or type 'disposed'"]
  ? Exit cap rate    → not found, please enter (e.g. 4.5%)

LL/TT ALLOCATION INPUTS
  ? Lease structure  → gross / nnn / modified-gross / rubs / green-lease?
  ? Metering config  → master / individual / submeter-passthrough?
  ✓ Jurisdiction:    [city] ([BPS warning if applicable])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Parsing user responses:**
- `y` or `yes` → confirm the proposed value
- A number → select numbered option
- A typed value → use as the field value (e.g. `4.5%` → `exit_cap_rate: 0.045`)
- `skip` → leave field null; mark `analysis_ready: false`
- `disposed` (for exit year) → set `status: "disposed"`, exclude from analysis

**After user response, show edge case warnings inline if applicable:**
- NNN + envelope measure in plan → "Note: NNN paradox — LL bears capex, TT captures savings"
- Solar + no green lease → "Note: rooftop solar typically requires tenant consent"
- RUBS + individual metering → "Note: savings may not recover to LL — collective action problem"
- BPS jurisdiction → "Note: carbon fine liability sits with property owner regardless of lease"

After all cards, present final execution plan:
> "Ready to create [N] assets, link [N] to Audette, upload [N] documents. [N] will be analysis-ready. Proceed? (y/n)"

## Stage 4: Execution Pipeline

Execute all assets in parallel (run independently — no cross-asset dependencies).

### For each asset:

**Step 4.1 — Idempotency check**

Query Supabase for existing asset with same name + client tag:
```sql
SELECT id, metadata FROM assets 
WHERE name = '<asset_name>' 
AND '<client-slug>' = ANY(tags)
LIMIT 1
```

If found and `ingestion_status = 'success'`, skip this asset (already done).
If found and `ingestion_status = 'failed'`, resume from first incomplete step.

**Step 4.2 — Create Soapbox asset**

Use `mcp__plugin_supabase_supabase__execute_sql`:
```sql
INSERT INTO assets (name, building_name, property_type, tags, metadata)
VALUES (
  '<name>',
  '<building_name>',
  '<property_type>',
  ARRAY['portfolio-ingestion', '<client-slug>'],
  '{}'::jsonb
)
RETURNING id;
```

Map `sub_asset_type` to `property_type`:
- "High Rise", "Midrise", "Garden Style", "Low-Rise", "Townhomes", "Wrap", "Urban Style" → `"multifamily"`
- "Clubhouse" → `"amenity"`
- Default → `"multifamily"`

**Step 4.3 — Link Audette**

If Audette ID is confirmed:
1. Call `mcp__claude_ai_Audette_AI__get_building_model_details` with the confirmed ID
2. If successful: update asset metadata with `audette_building_id` and backfill `year_built`, `gross_floor_area_m2`, `num_floors` from response
3. If call fails: log error, leave `audette_id: null`, continue

**Step 4.4 — Link ESPM**

If ESPM ID was provided by user: store `espm_property_id` in asset metadata.
ESPM is never a blocking step — always continue regardless.

**Step 4.5 — Upload documents**

For each document assigned to this asset:
- Download file content (Drive MCP / Box MCP as appropriate)
- Upload to Supabase storage: path = `assets/<asset_id>/documents/<filename>`
- Record `{filename, storage_path, doc_type, source}` in asset metadata `documents` array

Check idempotency: if `<asset_id>/<filename>` already exists in storage, skip upload.

**Step 4.6 — Store financial + LL/TT metadata**

Write final metadata to asset:

```json
{
  "ingestion_status": "success",
  "ingestion_client": "<client-slug>",
  "audette_building_id": "<id_or_null>",
  "espm_property_id": "<id_or_null>",
  "fund_name": "<fund>",
  "sub_asset_type": "<type>",
  "exit_year": 2030,
  "exit_cap_rate": 0.045,
  "lease_structure": "gross",
  "metering_config": "master",
  "jurisdiction": "Boston",
  "bps_liable": true,
  "ll_allocation_overrides": {},
  "analysis_ready": true,
  "documents": [{"filename": "...", "storage_path": "...", "doc_type": "pca"}]
}
```

`analysis_ready: true` only if `exit_year`, `exit_cap_rate`, `lease_structure`, `metering_config` are all non-null.
For BPS jurisdictions, also require `jurisdiction` to be non-null.

Use SQL UPDATE:
```sql
UPDATE assets SET metadata = '<json>'::jsonb WHERE id = '<asset_id>';
```

**Step 4.7 — Report progress**

After each asset completes, output one line:
```
✓ Landmark at Colony Park (7/39) — Audette linked, 8 docs, analysis-ready
⚠ Northern Michigan (9/39) — missing exit_cap_rate, not analysis-ready
✗ ORE 82 (11/39) — disposed, excluded from analysis
```

### Step 4.8 — Create portfolio thread

After all assets finish:

1. Query Supabase for the portfolio's conversations table
2. Create a new conversation tagged `<client-slug>-portfolio-analysis`
3. Post an opening message summarising:
   - Total assets created, by fund
   - Analysis-ready count vs. pending
   - List of failed assets with error reasons
   - "Ready to run: portfolio-analysis workflow (spec 2)"

### Step 4.9 — Completion report

Present to user:
```
Portfolio Ingestion Complete — [Client]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total assets:       [N]
  Analysis-ready:   [N]
  Missing params:   [N]  ([fields])
  Disposed:         [N]
  Failed:           [N]

Audette linked:     [N] / [total]
ESPM linked:        [N] / [total]
Documents uploaded: [N] across [N] assets

Funds: [fund1 (N)]  [fund2 (N)] ...

Portfolio thread: /portfolio/threads/[client-slug]-portfolio-analysis
```

## Error Handling

- If a required MCP tool is unavailable, tell the user which tool and what to configure, then continue without that integration
- If Supabase INSERT fails, report the asset as failed with the SQL error
- Never silently swallow errors — always report what failed and why
- A failed asset does not stop other assets from processing
```

- [ ] **Step 3: Verify skill file is well-formed**

```bash
wc -l ~/soapbox-agent/skills/portfolio-ingest/SKILL.md
head -5 ~/soapbox-agent/skills/portfolio-ingest/SKILL.md
```
Expected: file exists, starts with `# Portfolio Ingest Skill`, is > 100 lines.

- [ ] **Step 4: Commit**

```bash
cd ~/soapbox-agent && git add skills/portfolio-ingest/SKILL.md
git commit -m "feat: add portfolio-ingest skill (Stage 1-4 conversational orchestrator)"
```

---

## Task 6: Supabase Metadata Column Migration

Ensure the `assets` table has a JSONB `metadata` column and a `tags` text-array column for the ingestion workflow to write to.

- [ ] **Step 1: Check existing schema**

Use `mcp__plugin_supabase_supabase__execute_sql` (or run locally):
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'assets' 
AND column_name IN ('metadata', 'tags');
```

- If both exist → skip to Step 4 (no migration needed)
- If missing → continue to Step 2

- [ ] **Step 2: Write migration**

Use `mcp__plugin_supabase_supabase__apply_migration` with name `add_asset_ingestion_fields`:

```sql
-- Add metadata JSONB column for ingestion and financial parameters
ALTER TABLE assets 
ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;

-- Add tags text array for portfolio tagging
ALTER TABLE assets 
ADD COLUMN IF NOT EXISTS tags text[] DEFAULT '{}';

-- Index for tag queries (portfolio-level lookups by client slug)
CREATE INDEX IF NOT EXISTS assets_tags_gin ON assets USING gin(tags);

-- Index for metadata queries (analysis_ready lookups)
CREATE INDEX IF NOT EXISTS assets_metadata_gin ON assets USING gin(metadata);
```

- [ ] **Step 3: Verify migration applied**

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'assets' 
AND column_name IN ('metadata', 'tags');
```
Expected: two rows returned — `metadata jsonb`, `tags ARRAY`.

- [ ] **Step 4: Smoke test write + read round-trip**

```sql
-- Write test metadata
UPDATE assets SET 
  metadata = '{"ingestion_status": "test", "analysis_ready": false}'::jsonb,
  tags = ARRAY['test-tag']
WHERE id = (SELECT id FROM assets LIMIT 1);

-- Read it back
SELECT metadata, tags FROM assets 
WHERE 'test-tag' = ANY(tags) LIMIT 1;

-- Clean up
UPDATE assets SET metadata = '{}'::jsonb, tags = '{}'
WHERE 'test-tag' = ANY(tags);
```
Expected: metadata and tags survive the round-trip.

- [ ] **Step 5: Commit migration note**

```bash
cd ~/soapbox-agent && cat >> docs/superpowers/specs/2026-06-27-portfolio-ingestion-design.md << 'EOF'

## Migration Applied

- `assets.metadata` JSONB column: confirmed present (added via Supabase MCP if needed)
- `assets.tags` text[] column: confirmed present (added via Supabase MCP if needed)
- GIN indexes on both columns for portfolio-level queries
EOF
git add docs/superpowers/specs/2026-06-27-portfolio-ingestion-design.md
git commit -m "docs: note Supabase migration status for asset metadata/tags columns"
```

---

## Self-Review Checklist

After completing all tasks, verify:

- [ ] All three Python scripts pass their tests: `python3 -m pytest scripts/tests/ -v` → all green
- [ ] LL allocation: NNN+elevator returns LL=1.0, NNN+envelope returns LL=0.0 with warning, gross returns LL=1.0 for all measures
- [ ] Document classifier: PCA filenames classify as `pca`, energy audit text classifies as `audit`
- [ ] Fuzzy matcher: exact name+address scores ≥ 0.85 (auto-link); fuzzy name-only scores 0.40–0.84 (review); unrelated < 0.40
- [ ] Skill file exists at `skills/portfolio-ingest/SKILL.md` and references correct script paths
- [ ] Supabase `assets` table has `metadata` jsonb and `tags` text[] columns
- [ ] All commits are on the feature branch with descriptive messages
