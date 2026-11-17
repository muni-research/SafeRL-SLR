#!/usr/bin/env python3
"""Second update search (stageE, 2026-11-13): compile the title/abstract screening decisions and build bibliographic
records (same columns as stageC/records.csv) for every record sought for retrieval, with author lists from OpenAlex.
Inputs: stageE/candidates.csv, stageE/decisions/batch*.txt
Outputs: stageE/screening_decisions.csv, stageE/records.csv"""
import csv, json, time, urllib.request
from pathlib import Path

W = Path(__file__).resolve().parent.parent
E = W / "stageE"
UA = {"User-Agent": "SLR-SafeRL-AV/1.0 (systematic review)"}
cands = {r["eid"]: r for r in csv.DictReader(open(E / "candidates.csv"))}
dec = {}
for f in sorted((E / "decisions").glob("batch*.txt")):
    for line in open(f):
        if not line.strip() or line.startswith("#"):
            continue
        eid, d, *rest = line.split(" ", 3)
        code = rest[0] if rest and rest[0].startswith("EC") else ""
        note = " ".join(rest[1:] if code else rest).strip()
        assert eid in cands and eid not in dec, eid
        dec[eid] = (d, code, note)
assert set(dec) == set(cands), sorted(set(cands) - set(dec))
with open(E / "screening_decisions.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["eid", "source", "doi", "title", "year", "type", "venue", "decision", "code", "note"])
    for eid in sorted(dec):
        c = cands[eid]
        w.writerow([eid, c["source"], c["doi"], c["title"], c["year"], c["type"], c["venue"], *dec[eid]])

out = []
for eid in sorted(e for e, (d, _, _) in dec.items() if d in ("Include", "Unsure")):
    c = cands[eid]
    d = {}
    if c["id"].startswith("W"):
        for i in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(
                        f"https://api.openalex.org/works/{c['id']}?select=authorships,ids", headers=UA), timeout=40) as r:
                    d = json.loads(r.read().decode()); break
            except Exception:
                time.sleep(3 * (i + 1))
    authors = "; ".join(a["author"]["display_name"] for a in d.get("authorships", [])) or c["authors"]
    arxiv = c["arxiv"]
    for v in (d.get("ids") or {}).values():
        if "arxiv" in str(v).lower():
            arxiv = str(v).rsplit("/", 1)[-1]
    out.append({"study_id": eid, "in_stageA": "", "title": c["title"], "authors": authors, "year": c["year"],
                "venue": c["venue"], "doi": c["doi"], "arxiv": arxiv, "type": c["type"],
                "sources": "update search 2026-11-13 (" + c["source"] + ")", "query_ids": "", "abstract": c["abstract"],
                "url": f"https://doi.org/{c['doi']}" if c["doi"] else f"https://openalex.org/{c['id']}"})
    time.sleep(0.1)
with open(E / "records.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(dec), "screened;", len(out), "records sought;", sum(1 for r in out if not r["authors"]), "without authors")
