---
name: sustainability-passport
description: >
  Generate a Sustainability Passport for a property being disposed of (sold, traded, or refinanced).
  Compiles energy performance, carbon footprint, certifications, compliance status, utility data,
  and ESG metrics into a standardized investor-ready document. Triggers on: "sustainability passport",
  "green credentials", "ESG summary for sale", "sustainability disclosure", "disposition sustainability",
  "green due diligence package", "sustainability report for buyers".
version: 1.0.0
---

# Sustainability Passport — Disposition

Generate a standardized sustainability disclosure document for a property being sold, traded, or refinanced. This passport gives buyers and their advisors a complete, defensible picture of the property's environmental footprint, compliance posture, and green credentials.

**Audience:** Buyers, brokers, lenders, ESG-mandated institutional investors.

**Default posture:** Only include claims you can source from uploaded documents, utility data, or connected systems (Audette, ENERGY STAR). Flag estimates clearly. Buyers will verify.

---

## Step 1: Gather Data Sources

Before writing, inventory what's available:

**From uploaded files:**
- [ ] Utility bills (last 24 months minimum — 36 preferred)
- [ ] ENERGY STAR Portfolio Manager reports
- [ ] LEED / BREEAM / Fitwel certificate or scorecard
- [ ] Local law compliance filings (LL97, BERDO, Building Benchmarking)
- [ ] Recent energy audit or retro-commissioning report
- [ ] Capital improvements log (HVAC, envelope, lighting upgrades)
- [ ] Phase I / Phase II environmental reports

**From connected tools:**
- Search Audette for building model, carbon plan, and existing assessments
- Check CRREM pathway if available
- Pull ENERGY STAR score if Portfolio Manager is connected

**Prompt the user for anything missing:**
> "To complete the passport I need [X]. Can you upload it or let me know the values directly?"

---

## Step 2: Sustainability Passport Structure

Generate the passport as a structured document artifact with these sections:

### Section 1 — Property Identity
- Address, asset type, year built, gross floor area (SF / SM)
- Ownership entity, disposition date / expected close
- Primary use (office, multifamily, industrial, mixed-use, etc.)

### Section 2 — Energy Performance
| Metric | Value | Source | Period |
|--------|-------|--------|--------|
| Site EUI (kBtu/sf/yr) | | | |
| Source EUI (kBtu/sf/yr) | | | |
| ENERGY STAR Score (1–100) | | | |
| Total annual energy cost | | | |
| Grid emission factor (lbs CO₂/kWh) | | | |

**Trend:** Include 3-year trajectory (improving / flat / worsening) if data supports it.

### Section 3 — Carbon Footprint
| Scope | Annual tCO₂e | Method |
|-------|-------------|--------|
| Scope 1 (on-site combustion) | | |
| Scope 2 (purchased electricity) | | |
| Total operational carbon | | |

- Carbon intensity (kgCO₂e/m² or lbsCO₂/sf)
- CRREM pathway alignment: above/on/below stranding risk curve (if available)
- 2030 target gap (if applicable)

### Section 4 — Green Certifications
List all active certifications with expiry dates:
- LEED (version, level, score)
- BREEAM (rating, score)
- ENERGY STAR Certification (year earned, score)
- Fitwel / WELL / RESET / others
- Local green building designations

Note: flag certifications within 12 months of expiry.

### Section 5 — Regulatory Compliance
| Regulation | Jurisdiction | Status | Penalty Risk |
|-----------|-------------|--------|-------------|
| Local Law 97 | NYC | | |
| BERDO | Boston | | |
| Building Benchmarking | [City] | | |
| State energy codes | [State] | | |

For each applicable regulation:
- Current compliance status (compliant / at risk / non-compliant)
- Projected compliance through 2030 and 2035 at current trajectory
- Estimated penalty exposure if non-compliant ($/year)
- Required capital to achieve compliance

### Section 6 — Capital Improvements (Sustainability-Related)
Table of completed sustainability capex (last 10 years):
| Year | Measure | Cost | Impact |
|------|---------|------|--------|
| | HVAC replacement | | EUI reduction |
| | LED lighting retrofit | | kWh/yr savings |
| | Solar PV installation | | kW capacity |
| | Envelope improvements | | |

### Section 7 — Stranding Risk & Forward Outlook
- CRREM stranding year (if model available)
- Required decarbonization capex to 2030 / 2035 / 2050
- Key risk factors: grid decarbonization exposure, fuel-switching requirements, regulatory trajectory
- Recommended buyer actions (optional — frame as opportunities, not liabilities)

### Section 8 — ESG Summary (for Institutional Buyers)
One-paragraph narrative suitable for buyer's ESG committee or investment memo:
- Lead with the strongest credential
- Acknowledge the material risks honestly
- Quantify the opportunity (cost of compliance, potential green premium)

---

## Step 3: Quality Checks Before Delivery

Before finalizing, verify:
- [ ] All EUI / carbon numbers are sourced — no ungrounded estimates
- [ ] Compliance status is current (not based on expired filings)
- [ ] Certification expiry dates are included
- [ ] Penalty estimates cite the specific regulation and rate
- [ ] CRREM stranding year is labeled "estimated" if based on modeled data
- [ ] No greenwashing — do not overclaim on partial-year or projected data

---

## Output Format

Deliver as:
1. **Structured HTML artifact** — formatted for printing / PDF export
2. **Executive summary** (200 words max) — suitable for OM teaser or data room index

If the user asks for a Word or PDF export, use the write_file tool to create a `.docx` version.

---

## Common Edge Cases

**No utility data available:**
> "Utility data is the foundation of this passport. Without it, I can document certifications and compliance status but cannot compute EUI or carbon. Options: (1) request bills from the seller/operator, (2) use ENERGY STAR Portfolio Manager if connected, (3) note 'data not available' and estimate from CBECS benchmarks with clear disclosure."

**Property has deferred maintenance / poor performance:**
> "The data shows [specific issues]. I'll document this accurately — buyers will find it anyway. We can frame it as priced-in capex opportunity rather than hidden liability."

**Multiple buildings / campus:**
> "I'll generate one passport per building plus a portfolio-level summary. Should I treat the campus as a single reporting boundary or separate properties?"
