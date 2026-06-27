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
    assert "asset_name" in m and "score" in m and "ambiguous" in m
