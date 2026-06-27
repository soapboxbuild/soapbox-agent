#!/usr/bin/env python3
"""
document_classifier.py — Infer document type from filename and text sample.

Usage:
    python3 document_classifier.py --inputs '<json>'

Input JSON keys:
    filename    str  Original filename (e.g. "Landmark_PCA_2024.pdf")
    text        str  First ~500 words of extracted document text (may be empty)

Output JSON keys:
    doc_type       str    pca | audit | utility | capex | lease | other
    confidence     float  0.0–1.0
    signals_found  list   keyword strings that triggered the classification
"""
import argparse
import json
import sys

DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "pca": [
        "property condition assessment", "property condition report", "pca",
        "capital needs assessment", "building survey", "physical condition",
        "deferred maintenance", "immediate needs", "short-term needs",
        "long-term needs", "capital reserve",
    ],
    "audit": [
        "energy audit", "energy assessment", "retro-commissioning", "ashrae",
        "green rock", "energy efficiency", "audit report", "level i", "level ii",
        "level iii", "eui", "energy use intensity", "energy conservation measure",
        "ecm", "retro commissioning", "benchmarking",
    ],
    "utility": [
        "utility bill", "utility invoice", "electric bill", "gas bill",
        "interval data", "meter data", "kwh", "therms", "consumption data",
        "utility account", "billing period", "energy usage", "electricity invoice",
        "natural gas invoice", "water bill",
    ],
    "capex": [
        "capital plan", "capital expenditure", "capex", "reserve study",
        "five-year plan", "10-year plan", "capital budget", "renovation budget",
        "improvement plan", "capital improvement", "replacement schedule",
    ],
    "lease": [
        "lease abstract", "rent roll", "lease agreement", "landlord", "tenant",
        "lessee", "lessor", "lease term", "base rent", "triple net", "nnn",
        "gross lease", "modified gross", "common area maintenance", "cam charges",
        "lease commencement", "lease expiration",
    ],
}


def classify_document(filename: str, text_sample: str) -> dict:
    # Normalize: replace underscores and hyphens with spaces for matching
    normalized_filename = filename.lower().replace('_', ' ').replace('-', ' ')
    normalized_text = text_sample.lower().replace('_', ' ').replace('-', ' ')
    combined = normalized_filename + " " + normalized_text

    scores: dict[str, int] = {}
    signals: dict[str, list[str]] = {}

    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        found = [kw for kw in keywords if kw in combined]
        scores[doc_type] = len(found)
        signals[doc_type] = found

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        return {"doc_type": "other", "confidence": 0.0, "signals_found": []}

    # Confidence: hitting 30% of a type's keywords = full confidence
    max_possible = len(DOC_TYPE_KEYWORDS[best_type])
    confidence = min(best_score / max(max_possible * 0.3, 1), 1.0)

    return {
        "doc_type": best_type,
        "confidence": round(confidence, 2),
        "signals_found": signals[best_type],
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

    filename = inputs.get("filename", "")
    text = inputs.get("text", "")
    result = classify_document(filename, text)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
