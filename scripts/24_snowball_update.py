#!/usr/bin/env python3
"""Phase 8: citation searching (backward and forward snowballing) and update search.

* Backward: all works referenced by the included studies (OpenAlex `referenced_works`).
* Forward: all works that cite an included study (OpenAlex `cites:` filter).
* Update search: the three OpenAlex queries of 05_search.py restricted to records created after the
  original search date (2026-10-07), by publication date (the created-date filter needs a paid OpenAlex key).
Candidates must match an RL term, a safety term and a road-vehicle term in title or abstract (the concept
blocks of the database search), and are de-duplicated against every record already screened (Stage A
inventory and Stage B unique records) by DOI and normalised title. Output: stageC/candidates.csv and
stageC/run_log.txt. Responses are cached in stageC/raw/.
"""
import csv
import datetime
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

W = Path(__file__).resolve().parent.parent
C = W / "stageC"; RAW = C / "raw"; RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "SLR-SafeRL-AV/1.0 (systematic review citation searching)"}
SEARCH_DATE = "2026-10-07"
SEL = "id,doi,title,publication_year,type,abstract_inverted_index,primary_location,referenced_works"


def get(url):
    f = RAW / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                d = json.loads(r.read().decode())
            f.write_text(json.dumps(d)); time.sleep(0.12)
            return d
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (i + 1)); continue
            raise
    raise RuntimeError(url)


def works(filter_, extra="", keep_refs=False):
    out, cursor = [], "*"
    while cursor:
        url = (f"https://api.openalex.org/works?filter={urllib.parse.quote(filter_, safe=':|,.')}"
               f"&select={SEL}&per-page=200&cursor={cursor}{extra}")
        d = get(url)
        for w in d["results"]:
            if not keep_refs:
                w.pop("referenced_works", None)   # not needed for candidates; saves memory
        out += d["results"]
        cursor = d["meta"].get("next_cursor") if d["results"] else None
    return out


def abstract(w):
    inv = w.get("abstract_inverted_index") or {}
    pos = sorted((p, t) for t, ps in inv.items() for p in ps)
    return " ".join(t for _, t in pos)


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


RL = re.compile(r"reinforcement learning|\bRL\b|policy optimi[sz]ation|actor-critic|q-learning|\bDQN\b|\bPPO\b|\bSAC\b", re.I)
SAFE = re.compile(r"safe|safety|constrain|risk|shield|barrier|lyapunov|collision|reachab|verif|runtime assurance", re.I)
VEH = re.compile(r"vehicle|driving|driver|self-driving|car\b|cars\b|lane|merging|intersection|platoon|cruise control|"
                 r"racing|parking|traffic|automated driving|autonomous driving", re.I)

log = [f"run {datetime.date.today().isoformat()}"]
# seeds = studies included by the database search (Stage A/B IDs); citation-search studies (C IDs) are not re-seeded
inc = [r for r in csv.DictReader(open(W / "extraction" / "evidence_db.csv")) if not r["study_id"].startswith("C")]
dois = [r["doi"].lower() for r in inc if r["doi"]]
seed = []
for i in range(0, len(dois), 50):
    seed += works("doi:" + "|".join(dois[i:i + 50]), keep_refs=True)
seed_ids = [w["id"].split("/")[-1] for w in seed]
log.append(f"included studies with DOI: {len(dois)}; found in OpenAlex: {len(seed)}")

# backward
refs = sorted({r.split("/")[-1] for w in seed for r in (w.get("referenced_works") or [])})
back = []
for i in range(0, len(refs), 50):
    back += works("openalex:" + "|".join(refs[i:i + 50]))
log.append(f"backward: {len(refs)} referenced works, {len(back)} retrieved")
# forward
fwd = []
for i in range(0, len(seed_ids), 40):
    fwd += works("cites:" + "|".join(seed_ids[i:i + 40]))
log.append(f"forward: {len(fwd)} citing works")
# update search (same strings as 05_search.py)
import importlib.util
spec = importlib.util.spec_from_file_location("s05", W / "scripts" / "05_search.py")
src = (W / "scripts" / "05_search.py").read_text()
ns = {"__file__": str(W / "scripts" / "05_search.py")}
exec(src[:src.index("runs = []")].replace('MAIL = "', 'MAIL_UNUSED = "'), ns)
upd = []
for qid, (field, q) in ns["OPENALEX"].items():
    res = works(f"{field}:{q},from_publication_date:{SEARCH_DATE}")
    log.append(f"update {qid}: {len(res)} records published since {SEARCH_DATE}")
    upd += res

# de-duplicate against everything already screened
seen_doi, seen_t = set(), set()
for r in csv.DictReader(open(W / "stageB" / "records_unique.csv")):
    seen_doi.add((r["doi"] or "").lower()); seen_t.add(norm(r["title"]))
for r in csv.DictReader(open(W / "stageA" / "stageA_inventory.csv")):
    seen_doi.add((r["doi"] or "").lower()); seen_t.add(norm(r["title"]))
seen_doi.discard("")

cand, kept = {}, {"backward": 0, "forward": 0, "update": 0}
flow = {"raw": 0, "already_screened": 0, "duplicate_within_citation_results": 0, "keyword_filter": 0}
seen_c = set()
for src_name, ws in (("backward", back), ("forward", fwd), ("update", upd)):
    for w in ws:
        flow["raw"] += 1
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        t = w.get("title") or ""
        if (doi and doi in seen_doi) or norm(t) in seen_t:
            flow["already_screened"] += 1
            continue
        key = doi or norm(t)
        ab = abstract(w)
        text = t + " " + ab
        if not (RL.search(text) and SAFE.search(text) and VEH.search(text)):
            flow["duplicate_within_citation_results" if key in seen_c else "keyword_filter"] += 1
            seen_c.add(key)
            continue
        seen_c.add(key)
        if key in cand:
            flow["duplicate_within_citation_results"] += 1
            cand[key]["source"] = ";".join(sorted(set(cand[key]["source"].split(";")) | {src_name}))
            continue
        kept[src_name] += 1
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        cand[key] = {"cid": "", "source": src_name, "doi": doi, "title": t, "year": w.get("publication_year", ""),
                     "type": w.get("type", ""), "venue": venue, "openalex": w["id"].split("/")[-1], "abstract": ab[:3000]}
rows = sorted(cand.values(), key=lambda r: (str(r["year"]), r["title"]))
for i, r in enumerate(rows, 1):
    r["cid"] = f"C{i:04d}"
with open(C / "candidates.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["cid"])
    w.writeheader(); w.writerows(rows)
log.append(f"new candidates after keyword filter and de-duplication: {len(rows)} (first found via {kept})")
log.append("record flow: " + json.dumps(flow))
(C / "record_flow.json").write_text(json.dumps({**flow, "candidates": len(rows), "first_found_via": kept}, indent=1))
(C / "run_log.txt").write_text("\n".join(log) + "\n")
print("\n".join(log))
