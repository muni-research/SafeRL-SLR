#!/usr/bin/env python3
"""Pre-submission update search (second update; the first was part of 24_snowball_update.py on 2026-10-10).

Re-runs the final database strings of 05_search.py without a date filter, so that records indexed after the
original search are found whatever their publication date (OpenAlex's created-date filter needs a paid key):
  * OpenAlex OA-Q1v2, OA-Q2v2, OA-Q3v2 (all years, all types)
  * arXiv: the same S x V and M x V phrase queries
Every record already handled by the review (Stage A inventory, Stage B unique records, Stage C candidates) is
removed by DOI, arXiv id and normalised title. The remainder passes the same concept filter as the citation search
(RL term + safety term + road-vehicle term in title or abstract). Output: stageE/candidates.csv (E-IDs),
stageE/run_log.txt, stageE/record_flow.json; raw responses cached in stageE/raw/ (one folder per run date).
"""
import csv
import datetime
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

W = Path(__file__).resolve().parent.parent
E = W / "stageE"
TODAY = datetime.date.today().isoformat()
RAW = E / "raw" / TODAY
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "SLR-SafeRL-AV/1.0 (systematic review update search)"}

src = (W / "scripts" / "05_search.py").read_text()
ns = {"__file__": str(W / "scripts" / "05_search.py")}
exec(src[:src.index("runs = []")], ns)                       # search strings only, nothing is run
OPENALEX, AX_S, AX_V, AX_M = ns["OPENALEX"], ns["ARXIV_S"], ns["ARXIV_V"], ns["ARXIV_M"]


def get(url, pause=0.15, raw=False):
    f = RAW / (hashlib.md5(url.encode()).hexdigest() + (".xml" if raw else ".json"))
    if f.exists():
        t = f.read_text()
        return t if raw else json.loads(t)
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                t = r.read().decode("utf-8", "ignore")
            f.write_text(t); time.sleep(pause)
            return t if raw else json.loads(t)
        except urllib.error.HTTPError as e:
            time.sleep((10 if e.code in (429, 503) else 3) * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    raise RuntimeError(url)


def abstract(w):
    inv = w.get("abstract_inverted_index") or {}
    return " ".join(t for _, t in sorted((p, t) for t, ps in inv.items() for p in ps))


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


RL = re.compile(r"reinforcement learning|\bRL\b|policy optimi[sz]ation|actor-critic|q-learning|\bDQN\b|\bPPO\b|\bSAC\b", re.I)
SAFE = re.compile(r"safe|safety|constrain|risk|shield|barrier|lyapunov|collision|reachab|verif|runtime assurance", re.I)
VEH = re.compile(r"vehicle|driving|driver|self-driving|car\b|cars\b|lane|merging|intersection|platoon|cruise control|"
                 r"racing|parking|traffic|automated driving|autonomous driving", re.I)

log, runs, recs = [f"run {TODAY} (no date filter; de-duplicated against Stages A, B and C)"], [], []
SEL = "id,doi,title,publication_year,publication_date,type,abstract_inverted_index,primary_location,authorships"
for qid, (field, q) in OPENALEX.items():
    page, n, total = 1, 0, None
    while True:                          # page numbers: cursor paging needs an API key since late 2026
        url = ("https://api.openalex.org/works?" + urllib.parse.urlencode(
            {"filter": f"{field}:{q}", "select": SEL, "per_page": 200, "page": page}))
        d = get(url)
        total = d["meta"]["count"]
        for w in d["results"]:
            n += 1
            recs.append({"source": f"OpenAlex {qid}", "doi": (w.get("doi") or "").replace("https://doi.org/", "").lower(),
                         "arxiv": "", "title": w.get("title") or "", "year": w.get("publication_year", ""),
                         "date": w.get("publication_date", ""), "type": w.get("type", ""),
                         "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                         "authors": "; ".join(a["author"]["display_name"] for a in (w.get("authorships") or [])[:6]),
                         "id": w["id"].split("/")[-1], "abstract": abstract(w)})
        page += 1
        if not d["results"] or n >= total:
            break
    runs.append((TODAY, "OpenAlex", qid, total, n)); log.append(f"OpenAlex {qid}: {total} reported, {n} retrieved")

A = "{http://www.w3.org/2005/Atom}"
queries = {f"AX-S{i}V{j}": f"abs:{s} AND abs:{v}" for i, s in enumerate(AX_S) for j, v in enumerate(AX_V)}
queries |= {f"AX-M{i}V{j}": f'abs:"reinforcement learning" AND abs:{m} AND abs:{v}'
            for i, m in enumerate(AX_M) for j, v in enumerate(AX_V)}
ax_total = 0
for qid, q in queries.items():
    start, got = 0, 0
    while True:
        txt = get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"search_query": q, "start": start, "max_results": 200}), pause=3.1, raw=True)
        root = ET.fromstring(txt)
        total = int(root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults").text)
        ents = root.findall(A + "entry")
        for e in ents:
            d = e.find("{http://arxiv.org/schemas/atom}doi")
            j = e.find("{http://arxiv.org/schemas/atom}journal_ref")
            aid = re.sub(r"v\d+$", "", e.find(A + "id").text.rsplit("/abs/", 1)[-1])
            recs.append({"source": f"arXiv {qid}", "doi": (d.text if d is not None else "").lower(), "arxiv": aid,
                         "title": " ".join(e.find(A + "title").text.split()),
                         "year": e.find(A + "published").text[:4], "date": e.find(A + "published").text[:10],
                         "type": "preprint", "venue": j.text if j is not None else "arXiv",
                         "authors": "; ".join(a.find(A + "name").text for a in e.findall(A + "author")[:6]),
                         "id": aid, "abstract": " ".join(e.find(A + "summary").text.split())})
            got += 1
        start += 200
        if start >= total or not ents:
            break
    ax_total += got
    runs.append((TODAY, "arXiv", qid, total, got))
log.append(f"arXiv: {len(queries)} queries, {ax_total} records retrieved")

# everything already handled by the review
seen_doi, seen_t = set(), set()
for f, dk, tk in ((W / "stageA" / "stageA_inventory.csv", "doi", "title"),
                  (W / "stageB" / "records_unique.csv", "doi", "title"),
                  (W / "stageC" / "candidates.csv", "doi", "title")):
    for r in csv.DictReader(open(f)):
        d = (r.get(dk) or "").lower().strip()
        if d:
            seen_doi.add(d)
            m = re.search(r"arxiv\.(\d{4}\.\d{4,5})", d)
            if m:
                seen_doi.add("arxiv:" + m.group(1))
        seen_t.add(norm(r.get(tk)))
for r in csv.DictReader(open(W / "stageB" / "records_unique.csv")):     # arXiv ids recorded in Stage B
    for v in r.values():
        for m in re.findall(r"(\d{4}\.\d{4,5})", v or ""):
            seen_doi.add("arxiv:" + m)
seen_doi.discard(""); seen_t.discard("")

flow = {"raw": 0, "already_handled": 0, "duplicate_within_update": 0, "keyword_filter": 0}
cand, seen = {}, {}
for r in recs:
    flow["raw"] += 1
    doi, aid, t = r["doi"], r["arxiv"], norm(r["title"])
    m = re.search(r"arxiv\.(\d{4}\.\d{4,5})", doi)
    aid = aid or (m.group(1) if m else "")
    if (doi and doi in seen_doi) or (aid and "arxiv:" + aid in seen_doi) or t in seen_t:
        flow["already_handled"] += 1
        continue
    key = t
    if key in seen:
        flow["duplicate_within_update"] += 1
        c = cand.get(key)
        if c:
            c["source"] = "; ".join(sorted(set(c["source"].split("; ")) | {r["source"].split()[0]}))
            c["doi"] = c["doi"] or doi
        continue
    seen[key] = 1
    if not (RL.search(r["title"] + " " + r["abstract"]) and SAFE.search(r["title"] + " " + r["abstract"])
            and VEH.search(r["title"] + " " + r["abstract"])):
        flow["keyword_filter"] += 1
        continue
    cand[key] = {**r, "source": r["source"].split()[0], "abstract": r["abstract"][:3000]}

rows = sorted(cand.values(), key=lambda r: (r["date"], r["title"]))
for i, r in enumerate(rows, 1):
    r["eid"] = f"E{i:03d}"
fields = ["eid", "source", "doi", "arxiv", "title", "authors", "year", "date", "type", "venue", "id", "abstract"]
with open(E / "candidates.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
with open(E / "search_runs.csv", "a", newline="") as f:
    w = csv.writer(f)
    if f.tell() == 0:
        w.writerow(["date", "source", "query_id", "hits_reported", "records_retrieved"])
    w.writerows(runs)
log.append(f"record flow: {json.dumps(flow)}; new candidates: {len(rows)}")
(E / "record_flow.json").write_text(json.dumps({**flow, "candidates": len(rows), "date": TODAY}, indent=1))
(E / "run_log.txt").write_text("\n".join(log) + "\n")
print("\n".join(log))
