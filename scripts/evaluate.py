#!/usr/bin/env python3
"""Reproducible retrieval evaluation over the synthetic seed dataset."""
import csv, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.database import SessionLocal
from app.models import Listing, ListingStatus
from app.services.matching import score_pair

OUT = ROOT / "docs" / "evaluation"
OUT.mkdir(parents=True, exist_ok=True)

def ranking_for(db, lost, found_rows, mode):
    scored = []
    for found in found_rows:
        result = score_pair(db, lost, found)
        if mode == "text": score = result["components"].get("text")
        elif mode == "image": score = result["components"].get("image")
        else: score = result["score"] / 100.0
        scored.append((float(score or 0), found.id, result))
    return sorted(scored, reverse=True)

def metrics(ranks, truth):
    relevant = 0; reciprocal = 0.0; precision_sum = 0.0
    for lost_id, ranking in ranks.items():
        expected = truth.get(lost_id, set())
        if not expected: continue
        top5 = [item[1] for item in ranking[:5]]
        hits = len(set(top5) & expected)
        precision_sum += hits / 5
        relevant += hits
        first_rank = next((i + 1 for i, item in enumerate(ranking) if item[1] in expected), None)
        if first_rank: reciprocal += 1 / first_rank
    n = max(1, len([k for k,v in truth.items() if v]))
    total_relevant = sum(len(v) for v in truth.values()) or 1
    return {"precision_at_5": round(precision_sum / n, 4), "recall_at_5": round(relevant / total_relevant, 4), "mrr": round(reciprocal / n, 4)}

db = SessionLocal()
try:
    lost_rows = db.query(Listing).filter(Listing.status == ListingStatus.LOST, Listing.is_synthetic.is_(True)).all()
    found_rows = db.query(Listing).filter(Listing.status == ListingStatus.FOUND, Listing.is_synthetic.is_(True)).all()
    known_pairs = {"Black wireless earbuds": "黑色蓝牙耳机盒", "Blue wallet": "蓝色钱包", "Small key ring": "钥匙串"}
    title_to_id = {row.title: row.id for row in found_rows}
    truth = {lost.id: ({title_to_id[known_pairs[lost.title]]} if lost.title in known_pairs and known_pairs[lost.title] in title_to_id else set()) for lost in lost_rows}
    results = {}
    detailed = []
    for mode in ["text", "image", "hybrid"]:
        ranks = {lost.id: ranking_for(db, lost, found_rows, mode) for lost in lost_rows}
        results[mode] = metrics(ranks, truth)
        for lost in lost_rows:
            for rank, (score, found_id, detail) in enumerate(ranks[lost.id], start=1):
                found = next(item for item in found_rows if item.id == found_id)
                detailed.append({"mode": mode, "lost_title": lost.title, "found_title": found.title, "rank": rank,
                                 "retrieval_score": round(score, 4), "hybrid_score": detail["score"],
                                 "text_method": detail["methods"].get("text"), "image_method": detail["methods"].get("image")})
    cross = []
    for lost in lost_rows:
        if lost.title not in known_pairs: continue
        ranking = ranking_for(db, lost, found_rows, "text")
        expected_id = title_to_id.get(known_pairs[lost.title])
        rank = next((i+1 for i, item in enumerate(ranking) if item[1] == expected_id), None)
        cross.append({"lost_title": lost.title, "found_title": known_pairs[lost.title], "rank": rank,
                      "top1_retrieved": rank == 1, "text_method": ranking[0][2]["methods"].get("text") if ranking else None})
    methods = sorted({row["text_method"] for row in detailed if row["text_method"]} | {row["image_method"] for row in detailed if row["image_method"]})
    report = {"dataset": "synthetic demo seed", "lost_records": len(lost_rows), "found_records": len(found_rows),
              "known_positive_pairs": sum(len(v) for v in truth.values()), "methods_observed": methods,
              "metrics": results, "cross_language_retrieval": cross,
              "limitations": ["Synthetic records only; not real campus data.", "Fallback embeddings are not equivalent to OpenCLIP or multilingual E5.", "Metrics are descriptive for this small demonstration set and are not generalizable."]}
    (OUT / "evaluation_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "retrieval_rankings.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(detailed[0].keys()) if detailed else ["mode"])
        writer.writeheader(); writer.writerows(detailed)
    with (OUT / "cross_language_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(cross[0].keys()) if cross else ["lost_title"])
        writer.writeheader(); writer.writerows(cross)
    labels = list(results); values = [results[k]["mrr"] for k in labels]
    plt.figure(figsize=(7, 4)); plt.bar(labels, values); plt.ylim(0, 1); plt.ylabel("Mean Reciprocal Rank")
    plt.title("Synthetic Retrieval Evaluation — MRR"); plt.tight_layout(); plt.savefig(OUT / "mrr_comparison.png", dpi=160); plt.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    db.close()
