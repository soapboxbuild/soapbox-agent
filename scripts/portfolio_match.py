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
    asset = inputs.get("asset")
    if asset is None:
        print(json.dumps({"error": "Missing required key: asset"}), file=sys.stderr)
        sys.exit(1)
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
