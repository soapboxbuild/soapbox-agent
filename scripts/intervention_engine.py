#!/usr/bin/env python3
"""
intervention_engine.py — Real estate capex intervention impact calculator.

Layers one intervention onto a base DCF model and computes:
  - NOI delta by year
  - Yield on Cost (YOC) = stabilized NOI uplift / total capex
  - Investment Spread = YOC - market cap rate
  - Payback period
  - IRR delta (approximation via base IRR + NPV of incremental cashflows)
  - Exit value delta

Usage:
    python3 intervention_engine.py \
        --base '<base_model_json>' \
        --intervention '<intervention_json>' \
        --market-cap-rate 0.05

Intervention types:
  solar             capex, annual_savings, start_year
  ev_charging       capex, annual_revenue, start_year
  smart_hvac        capex, annual_savings, start_year
  ppa               annual_savings (no capex), start_year
  unit_renovation   capex_per_unit, units, rent_premium_per_unit_monthly,
                    absorption_months, vacancy_days_per_unit, start_year
  amenity_upgrade   capex, annual_noi_uplift, start_year
  tech_package      capex_per_unit, units, rent_premium_per_unit_monthly, start_year
  utility_reduction annual_savings, program_cost, start_year
  mgmt_fee_change   new_fee_pct (applied to base EGI — no capex)
"""

import argparse
import json

DAYS_PER_YEAR = 365
MONTHS_PER_YEAR = 12


# ─── IRR approximation ────────────────────────────────────────────────────────

def _npv(rate: float, cashflows: list[float]) -> float:
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def _npv_deriv(rate: float, cashflows: list[float]) -> float:
    return sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows))


def irr(cashflows: list[float], guess: float = 0.10) -> float | None:
    rate = guess
    for _ in range(1000):
        npv = _npv(rate, cashflows)
        d = _npv_deriv(rate, cashflows)
        if abs(d) < 1e-14:
            return None
        new_rate = rate - npv / d
        if abs(new_rate - rate) < 1e-8:
            return new_rate
        rate = max(-0.99, min(new_rate, 10.0))
    return None


# ─── Intervention models ──────────────────────────────────────────────────────

def model_solar(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    """Returns (total_capex, noi_delta_by_year)."""
    capex = intervention["capex"]
    savings = intervention["annual_savings"]
    start = intervention.get("start_year", 1)
    deltas = []
    for year in range(1, hold_years + 1):
        deltas.append(savings if year >= start else 0.0)
    return capex, deltas


def model_ev_charging(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    capex = intervention["capex"]
    revenue = intervention.get("annual_revenue", 0)
    start = intervention.get("start_year", 1)
    deltas = [revenue if year >= start else 0.0 for year in range(1, hold_years + 1)]
    return capex, deltas


def model_smart_hvac(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    return model_solar(intervention, hold_years)  # same structure


def model_ppa(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    """No upfront capex — just annual savings."""
    savings = intervention["annual_savings"]
    start = intervention.get("start_year", 1)
    deltas = [savings if year >= start else 0.0 for year in range(1, hold_years + 1)]
    return 0.0, deltas


def model_unit_renovation(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    capex_per_unit = intervention["capex_per_unit"]
    units = intervention["units"]
    rent_premium_monthly = intervention["rent_premium_per_unit_monthly"]
    absorption_months = intervention.get("absorption_months", 12)
    vacancy_days = intervention.get("vacancy_days_per_unit", 14)
    start_year = intervention.get("start_year", 1)

    total_capex = capex_per_unit * units
    annual_premium_full = rent_premium_monthly * MONTHS_PER_YEAR * units

    # Vacancy cost during reno (lost rent at full premium for vacancy_days per unit)
    daily_premium = rent_premium_monthly / 30
    vacancy_cost = daily_premium * vacancy_days * units

    deltas = []
    for year in range(1, hold_years + 1):
        if year < start_year:
            deltas.append(0.0)
        elif year == start_year:
            # Phase in over absorption_months in this year
            # Assume linear absorption within the year
            months_in_year = min(absorption_months, MONTHS_PER_YEAR)
            avg_units_rented = units * (months_in_year / absorption_months) * 0.5
            noi_uplift = avg_units_rented * rent_premium_monthly * months_in_year
            deltas.append(round(noi_uplift - vacancy_cost, 0))
        else:
            # Fully absorbed in subsequent years
            deltas.append(round(annual_premium_full, 0))

    return total_capex, deltas


def model_amenity_upgrade(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    capex = intervention["capex"]
    annual_uplift = intervention["annual_noi_uplift"]
    start = intervention.get("start_year", 1)
    deltas = [annual_uplift if year >= start else 0.0 for year in range(1, hold_years + 1)]
    return capex, deltas


def model_tech_package(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    capex = intervention.get("capex_per_unit", 0) * intervention.get("units", 0)
    premium_monthly = intervention["rent_premium_per_unit_monthly"]
    units = intervention.get("units", 0)
    annual_uplift = premium_monthly * MONTHS_PER_YEAR * units
    start = intervention.get("start_year", 1)
    deltas = [annual_uplift if year >= start else 0.0 for year in range(1, hold_years + 1)]
    return capex, deltas


def model_utility_reduction(intervention: dict, hold_years: int) -> tuple[float, list[float]]:
    program_cost = intervention.get("program_cost", 0)
    annual_savings = intervention["annual_savings"]
    start = intervention.get("start_year", 1)
    deltas = [annual_savings if year >= start else 0.0 for year in range(1, hold_years + 1)]
    return program_cost, deltas


def model_mgmt_fee_change(intervention: dict, base_model: dict,
                           hold_years: int) -> tuple[float, list[float]]:
    """Recomputes management fee delta across all years."""
    new_pct = intervention["new_fee_pct"]
    deltas = []
    for year_data in base_model["annual"]:
        # Approximate EGI from NOI (EGI ≈ NOI / (1 - total_opex_pct))
        # Conservative: assume old fee was 2.5% of EGI ≈ NOI * 0.027
        estimated_egi = year_data["noi"] / 0.73
        old_fee = estimated_egi * 0.025
        new_fee = estimated_egi * new_pct
        deltas.append(round(old_fee - new_fee, 0))
    return 0.0, deltas


# ─── Dispatch ─────────────────────────────────────────────────────────────────

INTERVENTION_MODELS = {
    "solar": model_solar,
    "ev_charging": model_ev_charging,
    "smart_hvac": model_smart_hvac,
    "ppa": model_ppa,
    "unit_renovation": model_unit_renovation,
    "amenity_upgrade": model_amenity_upgrade,
    "tech_package": model_tech_package,
    "utility_reduction": model_utility_reduction,
}


def compute_intervention(base_model: dict, intervention: dict,
                          market_cap_rate: float) -> dict:
    hold_years = len(base_model["annual"])
    intervention_type = intervention["type"]

    if intervention_type == "mgmt_fee_change":
        total_capex, noi_deltas = model_mgmt_fee_change(intervention, base_model, hold_years)
    elif intervention_type in INTERVENTION_MODELS:
        total_capex, noi_deltas = INTERVENTION_MODELS[intervention_type](
            intervention, hold_years
        )
    else:
        raise ValueError(f"Unknown intervention type: {intervention_type}")

    # Stabilised NOI uplift = delta in final year (fully phased in)
    stabilised_noi_uplift = noi_deltas[-1] if noi_deltas else 0.0

    # Yield on Cost
    yoc = stabilised_noi_uplift / total_capex if total_capex > 0 else 0.0

    # Investment Spread
    investment_spread = yoc - market_cap_rate

    # Payback period (simple)
    if stabilised_noi_uplift <= 0 or total_capex <= 0:
        payback_years = float("inf")
    else:
        payback_years = total_capex / stabilised_noi_uplift

    # Exit value delta: stabilised NOI uplift capitalized at market cap rate
    exit_cap_rate = base_model.get("exit_cap_rate",
                    base_model["going_in_noi"] / base_model["exit_value"]
                    if base_model.get("exit_value") else market_cap_rate)
    exit_value_delta = stabilised_noi_uplift / exit_cap_rate if exit_cap_rate > 0 else 0.0

    # IRR delta: blended asset IRR (original purchase + intervention capex,
    # original + delta cashflows, original + delta exit value)
    base_irr = base_model.get("unlevered_irr", 0.08)
    purchase = base_model.get("implied_purchase", 0)
    # Fallback: derive implied purchase from going-in NOI and exit cap rate
    if not purchase and base_model.get("going_in_noi") and exit_cap_rate:
        purchase = base_model["going_in_noi"] / exit_cap_rate
    if purchase > 0:
        # Re-derive base IRR from actual cashflows so delta is internally consistent
        base_cfs = [-purchase] + [yr["unlevered_cf"] for yr in base_model["annual"]]
        base_cfs[-1] += base_model.get("exit_value", 0)
        computed_base_irr = irr(base_cfs)
        if computed_base_irr is not None:
            base_irr = computed_base_irr

        blended_cfs = [-(purchase + total_capex)]
        for i, yr in enumerate(base_model["annual"]):
            blended_cfs.append(yr["unlevered_cf"] + (noi_deltas[i] if i < len(noi_deltas) else 0))
        blended_cfs[-1] += base_model.get("exit_value", 0) + exit_value_delta
        new_irr = irr(blended_cfs)
        irr_delta = (new_irr - base_irr) if new_irr else 0.0
    else:
        irr_delta = 0.0

    # Summary card
    total_capex_fmt = f"${total_capex:,.0f}"
    yoc_fmt = f"{yoc*100:.1f}%"
    spread_sign = "+" if investment_spread >= 0 else ""
    spread_fmt = f"{spread_sign}{investment_spread*100:.1f}pp"
    payback_fmt = f"{payback_years:.1f} years" if payback_years != float("inf") else "N/A (no savings)"
    irr_base_fmt = f"{base_irr*100:.1f}%"
    irr_new_fmt = f"{(base_irr + irr_delta)*100:.1f}%"
    irr_delta_sign = "+" if irr_delta >= 0 else ""
    exit_delta_fmt = f"${exit_value_delta:+,.0f}"
    noi_yr1 = noi_deltas[0] if noi_deltas else 0
    noi_stab = stabilised_noi_uplift

    card_lines = [
        f"{base_model.get('asset_name', 'Asset')} — {intervention_type.replace('_', ' ').title()}",
        "─" * 52,
        f"Capex:              {total_capex_fmt:>15}",
        f"NOI Delta (Year 1): ${noi_yr1:>14,.0f}",
        f"NOI Delta (Stab.):  ${noi_stab:>14,.0f}",
        f"Yield on Cost:      {yoc_fmt:>15}",
        f"Investment Spread:  {spread_fmt:>15}  (vs {market_cap_rate*100:.1f}% mkt cap)",
        f"Payback Period:     {payback_fmt:>15}",
        f"Unlevered IRR:      {irr_base_fmt} → {irr_new_fmt}  ({irr_delta_sign}{irr_delta*100:.2f}pp)",
        f"Exit Value Delta:   {exit_delta_fmt:>15}",
        "─" * 52,
    ]
    card = "\n".join(card_lines)

    return {
        "noi_delta_by_year": [round(d, 0) for d in noi_deltas],
        "total_capex": round(total_capex, 0),
        "yoc": round(yoc, 6),
        "investment_spread": round(investment_spread, 6),
        "payback_years": round(payback_years, 2) if payback_years != float("inf") else None,
        "irr_delta": round(irr_delta, 6),
        "exit_value_delta": round(exit_value_delta, 0),
        "summary_card": card,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Base model JSON")
    parser.add_argument("--intervention", required=True, help="Intervention JSON")
    parser.add_argument("--market-cap-rate", type=float, default=0.05)
    args = parser.parse_args()

    base_model = json.loads(args.base)
    intervention = json.loads(args.intervention)

    result = compute_intervention(base_model, intervention, args.market_cap_rate)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
