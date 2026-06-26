#!/usr/bin/env python3
"""Tests for dcf_engine.py"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "dcf_engine.py"

PROSE_FRONTIER_INPUTS = {
    "profile": {
        "asset_type": "multifamily",
        "region": "us",
        "currency": "USD"
    },
    "unit_mix": [
        {"type": "1BR-A1", "count": 120, "avg_sf": 731, "market_rent": 1540},
        {"type": "1BR-A2", "count": 42,  "avg_sf": 818, "market_rent": 1625},
        {"type": "2BR-B1", "count": 36,  "avg_sf": 1105, "market_rent": 2000},
        {"type": "2BR-B2", "count": 126, "avg_sf": 1191, "market_rent": 2100}
    ],
    "going_in_occupancy": 0.95,
    "loss_to_lease_pct": 0.02,
    "vacancy_pct": 0.05,
    "concessions_pct": 0.01,
    "bad_debt_pct": 0.0015,
    "other_income_per_unit": 2049,
    "opex": {
        "payroll_per_unit": 1400,
        "om_per_unit": 700,
        "marketing_per_unit": 300,
        "ga_per_unit": 275,
        "utilities_per_unit": 835,
        "management_fee_pct": 0.025,
        "insurance_per_unit": 600,
        "taxes_per_unit": 2200,
        "reserves_per_unit": 150
    },
    "growth": {
        "rent":    [0.04, 0.04, 0.03, 0.03, 0.03],
        "expense": [0.03, 0.03, 0.03, 0.03, 0.03]
    },
    "hold_period_years": 5,
    "exit_cap_rate": 0.05,
    "sale_costs_pct": 0.015
}


def run_engine(inputs: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--inputs", json.dumps(inputs)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Engine failed: {result.stderr}"
    return json.loads(result.stdout)


def test_multifamily_returns_five_years():
    out = run_engine(PROSE_FRONTIER_INPUTS)
    assert len(out["annual"]) == 5


def test_multifamily_noi_is_positive():
    out = run_engine(PROSE_FRONTIER_INPUTS)
    assert out["going_in_noi"] > 0
    assert out["stabilized_noi"] > out["going_in_noi"]


def test_multifamily_exit_value_reasonable():
    # Prose Frontier: ~$72M acquisition price, exit should be in range
    out = run_engine(PROSE_FRONTIER_INPUTS)
    assert 50_000_000 < out["exit_value"] < 200_000_000


def test_multifamily_irr_reasonable():
    out = run_engine(PROSE_FRONTIER_INPUTS)
    # Unlevered IRR for stabilised multifamily typically 5-12%
    assert 0.04 < out["unlevered_irr"] < 0.15


def test_multifamily_equity_multiple():
    out = run_engine(PROSE_FRONTIER_INPUTS)
    assert out["equity_multiple"] > 1.0


def test_annual_noi_grows_each_year():
    out = run_engine(PROSE_FRONTIER_INPUTS)
    nois = [yr["noi"] for yr in out["annual"]]
    assert all(nois[i] < nois[i+1] for i in range(len(nois)-1))


def test_summary_card_contains_key_fields():
    out = run_engine(PROSE_FRONTIER_INPUTS)
    card = out["summary_card"]
    assert "NOI" in card
    assert "IRR" in card
    assert "Exit" in card


def test_hotel_uses_revpar_structure():
    hotel_inputs = {
        "profile": {"asset_type": "hotel", "region": "us", "currency": "USD"},
        "rooms": 200,
        "adr": 180.0,
        "going_in_occupancy": 0.72,
        "rooms_expense_pct": 0.28,
        "undistributed_expense_pct": 0.28,
        "management_fee_pct": 0.03,
        "ffe_reserve_pct": 0.04,
        "insurance_per_room": 800,
        "taxes_per_room": 2500,
        "other_revenue_pct": 0.18,
        "growth": {"revpar": [0.03, 0.03, 0.025, 0.025, 0.025],
                   "expense": [0.03, 0.03, 0.03, 0.03, 0.03]},
        "hold_period_years": 5,
        "exit_cap_rate": 0.065,
        "sale_costs_pct": 0.015
    }
    out = run_engine(hotel_inputs)
    assert out["going_in_noi"] > 0
    assert "RevPAR" in out["summary_card"]


def test_commercial_uses_lease_roll():
    commercial_inputs = {
        "profile": {"asset_type": "office", "region": "us",
                    "lease_structure": "gross", "currency": "USD"},
        "total_sf": 100_000,
        "current_occupancy": 0.88,
        "passing_rent_psf": 42.0,
        "market_rent_psf": 45.0,
        "opex_psf": 18.0,
        "management_fee_pct": 0.03,
        "capex_psf": 1.5,
        "ti_psf_at_renewal": 35.0,
        "lc_pct_of_lease_value": 0.04,
        "avg_lease_term_years": 5,
        "renewal_probability": 0.65,
        "growth": {"rent": [0.025]*5, "expense": [0.03]*5},
        "hold_period_years": 5,
        "exit_cap_rate": 0.065,
        "sale_costs_pct": 0.015
    }
    out = run_engine(commercial_inputs)
    assert out["going_in_noi"] > 0
    assert "WAULT" in out["summary_card"] or "SF" in out["summary_card"]
