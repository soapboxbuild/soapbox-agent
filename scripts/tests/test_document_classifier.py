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
