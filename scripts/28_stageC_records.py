#!/usr/bin/env python3
"""Phase 8: bibliographic records (same columns as stageB/records_unique.csv) for every citation-search
candidate sought for retrieval, with author lists from OpenAlex. Output: stageC/records.csv"""
import csv, json, time, urllib.request
from pathlib import Path

W = Path(__file__).resolve().parent.parent
C = W / "stageC"
UA = {"User-Agent": "SLR-SafeRL-AV/1.0 (systematic review)"}
cands = {r["cid"]: r for r in csv.DictReader(open(C / "candidates.csv"))}
sought = [r["cid"] for r in csv.DictReader(open(C / "screening_decisions.csv")) if r["decision"] in ("Include", "Unsure")]
out = []
for cid in sought:
    c = cands[cid]
    ids = c["openalex"]
    d = {}
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://api.openalex.org/works/{ids}?select=authorships,ids,primary_location", headers=UA), timeout=40) as r:
                d = json.loads(r.read().decode()); break
        except Exception:
            time.sleep(3 * (i + 1))
    authors = "; ".join(a["author"]["display_name"] for a in d.get("authorships", []))
    arxiv = ""
    for v in (d.get("ids") or {}).values():
        if "arxiv" in str(v).lower():
            arxiv = str(v).rsplit("/", 1)[-1]
    out.append({"study_id": cid, "in_stageA": "", "title": c["title"], "authors": authors, "year": c["year"],
                "venue": c["venue"], "doi": c["doi"], "arxiv": arxiv, "type": c["type"], "sources": "citation searching (" + c["source"] + ")",
                "query_ids": "", "abstract": c["abstract"], "url": f"https://doi.org/{c['doi']}" if c["doi"] else f"https://openalex.org/{ids}"})
    time.sleep(0.1)
with open(C / "records.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(out), "records;", sum(1 for r in out if not r["authors"]), "without authors")
