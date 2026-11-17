#!/usr/bin/env python3
"""Phase 8: DOI audit and bibliographic enrichment of the included studies.

For every included study with a DOI, fetch the registration-agency record (Crossref API; DataCite API for
DOIs that Crossref does not hold, e.g. arXiv 10.48550/*) and cache it in fulltext/doi_cache/. Then:
  * report DOIs that do not resolve, and titles that disagree with the evidence database
    (logs/doi_audit.csv, logs/doi_audit_summary.txt);
  * write manuscript/generated/bib_enrichment.json with volume, issue, pages, container title and
    publisher, which scripts/19_included_bib.py merges into included_studies.bib.
Nothing is invented: fields are copied only from the agency record.
"""
import csv
import difflib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

W = Path(__file__).resolve().parent.parent
CACHE = W / "fulltext" / "doi_cache"
CACHE.mkdir(parents=True, exist_ok=True)
R = list(csv.DictReader(open(W / "extraction" / "evidence_db.csv")))
UA = {"User-Agent": "SLR-SafeRL-AV/1.0 (systematic review DOI audit)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch(doi):
    f = CACHE / (re.sub(r"[^A-Za-z0-9._-]", "_", doi) + ".json")
    if f.exists():
        return json.loads(f.read_text())
    rec = {"doi": doi, "agency": None, "data": None}
    try:
        rec["data"] = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
        rec["agency"] = "crossref"
    except Exception:
        try:
            rec["data"] = get("https://api.datacite.org/dois/" + urllib.parse.quote(doi))["data"]["attributes"]
            rec["agency"] = "datacite"
        except Exception as e:
            rec["error"] = str(e)
    f.write_text(json.dumps(rec))
    time.sleep(0.15)
    return rec


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"<[^>]+>", "", t.lower())).strip()


rows, enrich = [], {}
for r in R:
    doi = r["doi"].strip()
    if not doi:
        rows.append({"study_id": r["study_id"], "doi": "", "status": "no DOI", "title_similarity": ""})
        continue
    rec = fetch(doi)
    d = rec.get("data")
    if not d:
        rows.append({"study_id": r["study_id"], "doi": doi, "status": "UNRESOLVED", "title_similarity": ""})
        continue
    if rec["agency"] == "crossref":
        title = (d.get("title") or [""])[0]
        e = {"container": (d.get("container-title") or [""])[0], "volume": d.get("volume", ""),
             "issue": d.get("issue", ""), "pages": d.get("page", "") or d.get("article-number", ""),
             "publisher": d.get("publisher", ""), "type": d.get("type", "")}
    else:
        title = (d.get("titles") or [{"title": ""}])[0].get("title", "")
        e = {"container": (d.get("container") or {}).get("title", ""), "volume": "", "issue": "", "pages": "",
             "publisher": d.get("publisher", "") if isinstance(d.get("publisher"), str) else "",
             "type": (d.get("types") or {}).get("resourceTypeGeneral", "")}
    sim = difflib.SequenceMatcher(None, norm(title), norm(r["title"])).ratio()
    status = "ok" if sim >= 0.85 else ("title differs" if sim >= 0.5 else "TITLE MISMATCH")
    rows.append({"study_id": r["study_id"], "doi": doi, "status": status, "title_similarity": f"{sim:.2f}",
                 "agency": rec["agency"], "agency_title": title[:200], "db_title": r["title"][:200]})
    enrich[r["study_id"]] = {k: v for k, v in e.items() if v}

with open(W / "logs" / "doi_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["study_id", "doi", "status", "title_similarity", "agency", "agency_title",
                                      "db_title"])
    w.writeheader()
    w.writerows(rows)
(W / "manuscript" / "generated" / "bib_enrichment.json").write_text(json.dumps(enrich, indent=1))
from collections import Counter
c = Counter(x["status"] for x in rows)
pg = sum(1 for v in enrich.values() if v.get("pages"))
vol = sum(1 for v in enrich.values() if v.get("volume"))
summary = (f"DOI audit {time.strftime('%Y-%m-%d')}: {len(R)} included studies; status {dict(c)}; "
           f"records with volume {vol}, with pages/article number {pg}.")
(W / "logs" / "doi_audit_summary.txt").write_text(summary + "\n")
print(summary)
