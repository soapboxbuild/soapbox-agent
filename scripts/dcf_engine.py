#!/usr/bin/env python3
"""
dcf_engine.py — Real estate DCF computation engine.

Routes on profile.asset_type:
  multifamily  → unit-mix revenue model
  office/industrial/retail → lease-roll model
  hotel → USALI operating-company model

Usage:
    python3 dcf_engine.py --inputs '<json>'

Output: JSON to stdout with keys:
    annual          list of {year, gpr_or_revenue, egi_or_gop, noi, unlevered_cf}
    going_in_noi    float
    stabilized_noi  float (year hold_period_years NOI)
    exit_value      float
    unlevered_irr   float
    equity_multiple float  (always 1.0 for unlevered — placeholder for levered)
    summary_card    str
"""

import argparse
import json
import sys
from functools import reduce
from typing import Any


# ─── IRR via Newton-Raphson ───────────────────────────────────────────────────

def _npv(rate: float, cashflows: list[float]) -> float:
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def _npv_derivative(rate: float, cashflows: list[float]) -> float:
    return sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows))


def irr(cashflows: list[float], guess: float = 0.10, max_iter: int = 1000,
        tol: float = 1e-8) -> float | None:
    rate = guess
    for _ in range(max_iter):
        npv_val = _npv(rate, cashflows)
        deriv = _npv_derivative(rate, cashflows)
        if abs(deriv) < 1e-14:
            return None
        new_rate = rate - npv_val / deriv
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
        # Clamp to avoid divergence
        rate = max(-0.99, min(rate, 10.0))
    return None


def cumulative_growth(rates: list[float], year: int) -> float:
    """Product of (1+g) for years 0..year-1."""
    return reduce(lambda acc, g: acc * (1 + g), rates[:year], 1.0)


def safe_growth(rates: list[float], year: int) -> float:
    """Growth rate for a given year — clamp to last available."""
    idx = min(year - 1, len(rates) - 1)
    return rates[idx]


# ─── Multifamily ──────────────────────────────────────────────────────────────

def build_multifamily_dcf(inputs: dict) -> dict:
    units = sum(ut["count"] for ut in inputs["unit_mix"])
    hold = inputs["hold_period_years"]
    rent_g = inputs["growth"]["rent"]
    exp_g = inputs["growth"]["expense"]
    opex = inputs["opex"]

    annual = []
    for year in range(1, hold + 1):
        rg = cumulative_growth(rent_g, year)
        eg = cumulative_growth(exp_g, year)

        # Revenue
        gpr = sum(ut["count"] * ut["market_rent"] * rg * 12
                  for ut in inputs["unit_mix"])
        loss_to_lease = gpr * inputs.get("loss_to_lease_pct", 0.02)
        adj_gpr = gpr - loss_to_lease
        vacancy = adj_gpr * inputs.get("vacancy_pct", 0.05)
        concessions = adj_gpr * inputs.get("concessions_pct", 0.01)
        bad_debt = adj_gpr * inputs.get("bad_debt_pct", 0.0015)
        nri = adj_gpr - vacancy - concessions - bad_debt

        other_income = inputs.get("other_income_per_unit", 0) * units * rg
        egi = nri + other_income

        # Expenses
        total_opex = (
            opex.get("payroll_per_unit", 0) * units * eg
            + opex.get("om_per_unit", 0) * units * eg
            + opex.get("marketing_per_unit", 0) * units * eg
            + opex.get("ga_per_unit", 0) * units * eg
            + opex.get("utilities_per_unit", 0) * units * eg
            + egi * opex.get("management_fee_pct", 0.025)
            + opex.get("insurance_per_unit", 0) * units * eg
            + opex.get("taxes_per_unit", 0) * units * eg
            + opex.get("reserves_per_unit", 0) * units
        )
        noi = egi - total_opex

        annual.append({
            "year": year,
            "gpr": round(gpr, 0),
            "egi": round(egi, 0),
            "noi": round(noi, 0),
            "unlevered_cf": round(noi, 0),
        })

    # Exit
    exit_rent_growth = safe_growth(rent_g, hold + 1)
    exit_noi = annual[-1]["noi"] * (1 + exit_rent_growth)
    exit_value = exit_noi / inputs["exit_cap_rate"] * (1 - inputs.get("sale_costs_pct", 0.015))

    return annual, round(exit_value, 0), units


def format_multifamily_card(annual: list, exit_value: float, irr_val: float,
                             em: float, units: int, asset_name: str) -> str:
    going_in_noi = annual[0]["noi"]
    stab_noi = annual[-1]["noi"]
    exit_cap_implied = annual[-1]["noi"] / exit_value if exit_value else 0

    lines = [
        f"{asset_name} — Cashflow Model (Multifamily | US)",
        "─" * 52,
        f"Going-in NOI:     ${going_in_noi:>12,.0f}  (${going_in_noi/units:,.0f}/unit)",
        f"Stabilized NOI:   ${stab_noi:>12,.0f}  (${stab_noi/units:,.0f}/unit)",
        f"Unlevered IRR:    {irr_val*100:>11.1f}%",
        f"Equity Multiple:  {em:>11.2f}x",
        f"Exit Value:       ${exit_value:>12,.0f}  ({exit_cap_implied*100:.1f}% implied cap)",
        "─" * 52,
        "Full DCF available — ask for year-by-year breakdown.",
    ]
    return "\n".join(lines)


# ─── Commercial (office/industrial/retail) ────────────────────────────────────

def build_commercial_dcf(inputs: dict) -> dict:
    sf = inputs["total_sf"]
    hold = inputs["hold_period_years"]
    rent_g = inputs["growth"]["rent"]
    exp_g = inputs["growth"]["expense"]
    occ = inputs["current_occupancy"]
    passing_rent = inputs["passing_rent_psf"]
    market_rent = inputs["market_rent_psf"]
    opex_psf = inputs["opex_psf"]
    mgmt_fee_pct = inputs.get("management_fee_pct", 0.03)
    capex_psf = inputs.get("capex_psf", 1.5)

    # TI/LC inputs — capital costs at lease renewal
    ti_psf_at_renewal = inputs.get("ti_psf_at_renewal", 0.0)
    lc_pct_of_lease_value = inputs.get("lc_pct_of_lease_value", 0.0)
    avg_lease_term_years = inputs.get("avg_lease_term_years", 5)
    renewal_probability = inputs.get("renewal_probability", 0.65)

    # Annual fraction of leases that roll (need to be re-leased)
    annual_turnover = (1 / avg_lease_term_years) * (1 / renewal_probability)

    # Simple lease-roll model: blend passing → market over hold
    annual = []
    for year in range(1, hold + 1):
        rg = cumulative_growth(rent_g, year)
        eg = cumulative_growth(exp_g, year)

        # Blend toward market rent as leases roll (linear for simplicity)
        blend = min(year / hold, 1.0)
        effective_rent_psf = passing_rent * (1 - blend) * rg + market_rent * blend * rg
        occupied_sf = sf * occ
        gross_revenue = effective_rent_psf * occupied_sf

        # Lease structure: gross = landlord pays opex; NNN = opex recovered
        lease_structure = inputs.get("profile", {}).get("lease_structure", "gross")
        if lease_structure in ("nnn", "net"):
            net_opex = capex_psf * sf * eg  # only structural capex
        else:
            net_opex = opex_psf * sf * eg

        management_fee = gross_revenue * mgmt_fee_pct
        noi = gross_revenue - net_opex - management_fee

        # TI/LC: capital outflows at lease renewal — reduce unlevered CF but NOT NOI
        ti_cost = sf * annual_turnover * ti_psf_at_renewal
        lc_cost = sf * annual_turnover * effective_rent_psf * avg_lease_term_years * lc_pct_of_lease_value
        ti_lc_cost = ti_cost + lc_cost

        annual.append({
            "year": year,
            "gross_revenue": round(gross_revenue, 0),
            "egi": round(gross_revenue, 0),
            "noi": round(noi, 0),
            "ti_lc_cost": round(ti_lc_cost, 0),
            "unlevered_cf": round(noi - ti_lc_cost, 0),
            "effective_rent_psf": round(effective_rent_psf, 2),
        })

    exit_noi = annual[-1]["noi"] * (1 + safe_growth(rent_g, hold + 1))
    exit_value = exit_noi / inputs["exit_cap_rate"] * (1 - inputs.get("sale_costs_pct", 0.015))
    return annual, round(exit_value, 0), sf


def format_commercial_card(annual: list, exit_value: float, irr_val: float,
                            em: float, sf: float, asset_type: str,
                            asset_name: str) -> str:
    going_in_noi = annual[0]["noi"]
    stab_noi = annual[-1]["noi"]
    going_in_cap = going_in_noi / exit_value if exit_value else 0
    lines = [
        f"{asset_name} — Cashflow Model ({asset_type.title()} | US)",
        "─" * 52,
        f"Going-in NOI:     ${going_in_noi:>12,.0f}  (${going_in_noi/sf:.2f}/SF)",
        f"Stabilized NOI:   ${stab_noi:>12,.0f}  (${stab_noi/sf:.2f}/SF)",
        f"Unlevered IRR:    {irr_val*100:>11.1f}%",
        f"Equity Multiple:  {em:>11.2f}x",
        f"Exit Value:       ${exit_value:>12,.0f}",
        f"Going-in Cap:     {going_in_cap*100:>11.1f}%",
        "─" * 52,
        "Full DCF available — ask for year-by-year breakdown.",
    ]
    return "\n".join(lines)


# ─── Hotel (USALI) ────────────────────────────────────────────────────────────

def build_hotel_dcf(inputs: dict) -> dict:
    rooms = inputs["rooms"]
    adr = inputs["adr"]
    occ = inputs["going_in_occupancy"]
    hold = inputs["hold_period_years"]
    revpar_g = inputs["growth"]["revpar"]
    exp_g = inputs["growth"]["expense"]

    annual = []
    for year in range(1, hold + 1):
        rg = cumulative_growth(revpar_g, year)
        eg = cumulative_growth(exp_g, year)

        revpar = adr * occ * rg
        rooms_revenue = revpar * rooms * 365
        other_revenue = rooms_revenue * inputs.get("other_revenue_pct", 0.18)
        total_revenue = rooms_revenue + other_revenue

        rooms_expense = rooms_revenue * inputs.get("rooms_expense_pct", 0.28)
        undistributed = total_revenue * inputs.get("undistributed_expense_pct", 0.28)
        gross_op_profit = total_revenue - rooms_expense - undistributed

        mgmt_fee = total_revenue * inputs.get("management_fee_pct", 0.03)
        ffe_reserve = total_revenue * inputs.get("ffe_reserve_pct", 0.04)
        insurance = inputs.get("insurance_per_room", 800) * rooms * eg
        taxes = inputs.get("taxes_per_room", 2500) * rooms * eg

        noi = gross_op_profit - mgmt_fee - ffe_reserve - insurance - taxes

        annual.append({
            "year": year,
            "total_revenue": round(total_revenue, 0),
            "revpar": round(revpar, 2),
            "gross_op_profit": round(gross_op_profit, 0),
            "egi": round(gross_op_profit, 0),
            "noi": round(noi, 0),
            "unlevered_cf": round(noi, 0),
        })

    exit_noi = annual[-1]["noi"] * (1 + safe_growth(revpar_g, hold + 1))
    exit_value = exit_noi / inputs["exit_cap_rate"] * (1 - inputs.get("sale_costs_pct", 0.015))
    return annual, round(exit_value, 0), rooms


def format_hotel_card(annual: list, exit_value: float, irr_val: float,
                      em: float, rooms: int, asset_name: str) -> str:
    going_in_noi = annual[0]["noi"]
    stab_noi = annual[-1]["noi"]
    revpar = annual[0].get("revpar", 0)
    lines = [
        f"{asset_name} — Cashflow Model (Hotel | USALI)",
        "─" * 52,
        f"Going-in RevPAR:  ${revpar:>11.2f}",
        f"Going-in NOI:     ${going_in_noi:>12,.0f}  (${going_in_noi/rooms:,.0f}/room)",
        f"Stabilized NOI:   ${stab_noi:>12,.0f}",
        f"Unlevered IRR:    {irr_val*100:>11.1f}%",
        f"Exit Value:       ${exit_value:>12,.0f}",
        "─" * 52,
        "Full USALI P&L available — ask for year-by-year breakdown.",
    ]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, help="JSON inputs string")
    args = parser.parse_args()

    inputs = json.loads(args.inputs)
    asset_type = inputs.get("profile", {}).get("asset_type", "multifamily")
    asset_name = inputs.get("asset_name", "Asset")

    if asset_type == "hotel":
        annual, exit_value, size = build_hotel_dcf(inputs)
    elif asset_type in ("office", "industrial", "retail"):
        annual, exit_value, size = build_commercial_dcf(inputs)
    else:
        annual, exit_value, size = build_multifamily_dcf(inputs)

    # Build unlevered cashflows for IRR: [initial_equity, cf1, cf2, ..., cfN+exit]
    # For unlevered IRR we need the purchase price — use going-in NOI / going-in cap rate
    going_in_noi = annual[0]["noi"]
    exit_cap_rate = inputs.get("exit_cap_rate", 0.05)
    implied_purchase = going_in_noi / exit_cap_rate
    cfs = [-implied_purchase] + [yr["unlevered_cf"] for yr in annual]
    cfs[-1] += exit_value  # add exit proceeds to final year

    irr_val = irr(cfs) or 0.0
    # Equity multiple = total distributions / initial investment
    em = sum(c for c in cfs[1:]) / implied_purchase if implied_purchase else 1.0

    going_in_noi_val = annual[0]["noi"]
    stab_noi_val = annual[-1]["noi"]

    if asset_type == "hotel":
        card = format_hotel_card(annual, exit_value, irr_val, em, size, asset_name)
    elif asset_type in ("office", "industrial", "retail"):
        card = format_commercial_card(annual, exit_value, irr_val, em, size,
                                       asset_type, asset_name)
    else:
        card = format_multifamily_card(annual, exit_value, irr_val, em, size, asset_name)

    output = {
        "annual": annual,
        "going_in_noi": going_in_noi_val,
        "stabilized_noi": stab_noi_val,
        "exit_value": exit_value,
        "unlevered_irr": round(irr_val, 6),
        "equity_multiple": round(em, 4),
        "summary_card": card,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
