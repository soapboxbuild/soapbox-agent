#!/usr/bin/env python3
"""Tests for intervention_engine.py"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "intervention_engine.py"

# Prose Frontier baseline (from dcf_engine output, simplified)
BASE_MODEL = {
    "asset_name": "Prose Frontier",
    "profile": {"asset_type": "multifamily"},
    "annual": [
        {"year": 1, "noi": 6_947_357, "unlevered_cf": 6_947_357},
        {"year": 2, "noi": 7_225_251, "unlevered_cf": 7_225_251},
        {"year": 3, "noi": 7_441_009, "unlevered_cf": 7_441_009},
        {"year": 4, "noi": 7_664_239, "unlevered_cf": 7_664_239},
        {"year": 5, "noi": 7_895_166, "unlevered_cf": 7_895_166},
    ],
    "exit_value": 148_000_000,
    "unlevered_irr": 0.082,
    "going_in_noi": 6_947_357,
}

SOLAR_INTERVENTION = {
    "type": "solar",
    "capex": 75_000,
    "annual_savings": 4_064,
    "start_year": 1,
}

UNIT_RENO_INTERVENTION = {
    "type": "unit_renovation",
    "capex_per_unit": 3_000,
    "units": 50,
    "rent_premium_per_unit_monthly": 150,
    "absorption_months": 10,
    "vacancy_days_per_unit": 14,
    "start_year": 1,
}

MARKET_CAP_RATE = 0.05


def run_engine(base_model: dict, intervention: dict,
               market_cap_rate: float = MARKET_CAP_RATE) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--base", json.dumps(base_model),
         "--intervention", json.dumps(intervention),
         "--market-cap-rate", str(market_cap_rate)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Engine failed: {result.stderr}"
    return json.loads(result.stdout)


def test_solar_produces_positive_noi_delta():
    out = run_engine(BASE_MODEL, SOLAR_INTERVENTION)
    assert all(d >= 0 for d in out["noi_delta_by_year"])
    assert out["noi_delta_by_year"][0] > 0


def test_solar_yoc_is_positive():
    out = run_engine(BASE_MODEL, SOLAR_INTERVENTION)
    assert out["yoc"] > 0


def test_solar_investment_spread():
    out = run_engine(BASE_MODEL, SOLAR_INTERVENTION)
    # YOC = 4064/75000 ≈ 5.4%. Spread = 5.4% - 5.0% = 0.4%
    assert abs(out["yoc"] - 4064 / 75_000) < 0.01
    assert abs(out["investment_spread"] - (out["yoc"] - MARKET_CAP_RATE)) < 1e-6


def test_solar_payback_period():
    out = run_engine(BASE_MODEL, SOLAR_INTERVENTION)
    # 75000 / 4064 ≈ 18.5 years
    assert 15 < out["payback_years"] < 25


def test_unit_reno_phased_absorption():
    out = run_engine(BASE_MODEL, UNIT_RENO_INTERVENTION)
    # NOI delta grows as units are renovated and re-leased
    assert out["noi_delta_by_year"][1] > out["noi_delta_by_year"][0]


def test_unit_reno_yoc():
    out = run_engine(BASE_MODEL, UNIT_RENO_INTERVENTION)
    # Annual premium: 50 units * 150/month * 12 = 90,000
    # Total capex: 50 * 3000 = 150,000
    # YOC ≈ 90000 / 150000 = 60%
    assert 0.50 < out["yoc"] < 0.70


def test_exit_value_delta_positive_for_noi_uplift():
    out = run_engine(BASE_MODEL, UNIT_RENO_INTERVENTION)
    assert out["exit_value_delta"] > 0


def test_irr_delta_positive_for_positive_noi_uplift():
    out = run_engine(BASE_MODEL, UNIT_RENO_INTERVENTION)
    assert out["irr_delta"] > 0


def test_summary_card_contains_yoc_and_spread():
    out = run_engine(BASE_MODEL, UNIT_RENO_INTERVENTION)
    assert "Yield on Cost" in out["summary_card"]
    assert "Investment Spread" in out["summary_card"]
