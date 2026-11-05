"""Evaluate the actual retriever. --live sends synthetic data to Gemini.

Default: BM25 only, temporary database, no model calls. Labels are at document
level. Generation checks remain a separate human-reviewed task.
"""
import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from lens import config, store, pipeline


def evaluate(live=False):
    queries = json.loads((config.ROOT / "evaluation/queries.json").read_text())
    truth = json.loads((config.ROOT / "evaluation/ground_truth.json").read_text())
    modes = ["keyword", "semantic", "hybrid"] if live else ["keyword"]
    report = {"executed_at": datetime.now(timezone.utc).isoformat(), "label_level": "document",
              "dataset": "12 synthetic development queries, not a held-out benchmark",
              "live_models_used": live, "generation_evaluated": False, "modes": {}}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "eval.sqlite3"
        store.seed(path)
        if live:
            while pipeline.build_index(path=path)["remaining"]:
                pass
        for mode in modes:
            details = []
            for query in queries:
                result = pipeline.ask(query["query"], mode=mode, top_k=4, path=path)
                ranked = []
                for source in result["sources"]:
                    doc = Path(source["filename"]).stem
                    if doc not in ranked:
                        ranked.append(doc)
                relevant = set(truth[query["id"]])
                hits = set(ranked) & relevant
                rank = next((r for r, doc in enumerate(ranked, 1) if doc in relevant), None)
                details.append({"id": query["id"], "retrieved_documents": ranked,
                                "recall": len(hits)/len(relevant), "precision": len(hits)/len(ranked) if ranked else 0,
                                "reciprocal_rank": 1/rank if rank else 0, "hit": bool(hits)})
            n = len(details)
            report["modes"][mode] = {"chunk_budget": 4,
                "metric_note": "Deduplicate documents after retrieving 4 chunks; precision uses returned distinct-document count, not fixed document k.",
                "document_recall": sum(d["recall"] for d in details)/n,
                "document_precision": sum(d["precision"] for d in details)/n,
                "mrr": sum(d["reciprocal_rank"] for d in details)/n,
                "hit_rate": sum(d["hit"] for d in details)/n, "queries": details}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Make real embedding calls; quota/billing may apply.")
    parser.add_argument("--output", default="evaluation/application-baseline.json")
    args = parser.parse_args()
    result = evaluate(args.live)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for mode, metrics in result["modes"].items():
        print(f"{mode}: document recall={metrics['document_recall']:.3f}, MRR={metrics['mrr']:.3f}, hit rate={metrics['hit_rate']:.3f}")
    print("Generation quality: NOT evaluated by this retrieval-only run.")
