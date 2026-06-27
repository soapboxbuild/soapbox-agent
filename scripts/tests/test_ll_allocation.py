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
