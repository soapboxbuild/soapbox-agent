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
