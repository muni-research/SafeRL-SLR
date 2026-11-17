"""Stage B step 1: run the database searches and store raw results.

Sources with open APIs are queried directly; every query string, date and hit count is appended to
stageB/search_runs.csv. Raw responses are kept in stageB/raw/ for audit.
  - OpenAlex  (title_and_abstract.search, boolean)          -> Q1, Q2
  - arXiv     (abs/ti fields, boolean, exact phrases)        -> Q1a..Q1d
  - DBLP      (title keyword search) -> attempted; on 2026-10-07 the API sat behind a bot check
  - Semantic Scholar bulk (boolean)                         -> attempted; logged if rate-limited
Publisher databases without open APIs (IEEE Xplore, Scopus, WoS, ScienceDirect, SpringerLink, ACM)
are searched manually by the authors with the strings in logs/search_strings.md, and their exports go
into stageB/manual_exports/ (handled by 06_merge.py).
Usage: python3 05_search.py [openalex] [dblp] [s2] [arxiv]   (default: all)
"""
import os
import csv, datetime, json, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent.parent / "stageB"
RAW = B / "raw"
RAW.mkdir(parents=True, exist_ok=True)
MAIL = os.environ.get("SLR_CONTACT_EMAIL", "")  # optional polite-pool contact; never hard-coded
TODAY = datetime.date.today().isoformat()

S = ('("safe reinforcement learning" OR "safe RL" OR "safety reinforcement learning" OR '
     '"constrained reinforcement learning" OR "risk-sensitive reinforcement learning" OR '
     '"risk-aware reinforcement learning" OR "safe policy optimization" OR "constrained policy optimization" OR '
     '"shielded reinforcement learning" OR "safety-critical reinforcement learning" OR "safe exploration" OR '
     '"safe deep reinforcement learning" OR "constrained Markov decision process" OR '
     '"safe multi-agent reinforcement learning" OR "safe MARL" OR "safety-aware reinforcement learning" OR "safe learning")')
V = ('("autonomous vehicle" OR "autonomous vehicles" OR "autonomous driving" OR "self-driving" OR '
     '"automated driving" OR "automated vehicle" OR "automated vehicles" OR "connected and automated vehicles" OR '
     '"connected autonomous vehicles" OR "intelligent vehicle" OR "intelligent vehicles" OR "autonomous car" OR '
     '"driverless" OR "connected vehicles" OR "autonomous racing" OR "autonomous parking" OR "vehicle platoon" OR '
     '"platooning" OR "driving policy" OR "driving policies" OR "kinematic bicycle model" OR "lane change" OR '
     '"lane changing" OR "adaptive cruise control" OR "car-following" OR "on-ramp merging" OR "unsignalized intersection")')
R = '("reinforcement learning")'
M = ('("control barrier function" OR "control barrier functions" OR "safety filter" OR "safety shield" OR '
     '"shielding" OR "safety layer" OR "Lyapunov" OR "reachability" OR "model predictive control" OR '
     '"runtime assurance" OR "formal verification" OR "safety constraint" OR "safety constraints" OR '
     '"safety guarantee" OR "safety guarantees")')
T3 = ('("reinforcement learning" OR "RL") AND (safe OR safety OR constrained OR risk OR shield OR barrier OR Lyapunov) '
      'AND (vehicle OR vehicles OR driving OR car OR platoon OR lane OR merging OR intersection OR racing OR parking)')
# v2 strings (2026-10-07): blocks extended after the pilot recall check (v1 recall vs Stage A includes = 74%).
OPENALEX = {"OA-Q1v2": ("title_and_abstract.search", f"{S} AND {V}"),
            "OA-Q2v2": ("title_and_abstract.search", f"{R} AND {M} AND {V}"),
            "OA-Q3v2": ("title.search", T3)}

ARXIV_S = ['"safe reinforcement learning"', '"constrained reinforcement learning"', '"safe RL"',
           '"risk-sensitive reinforcement learning"', '"safe exploration"', '"constrained policy optimization"']
ARXIV_V = ['"autonomous driving"', '"autonomous vehicle"', '"autonomous vehicles"', '"self-driving"',
           '"automated driving"', '"automated vehicles"', '"connected automated vehicles"']
ARXIV_M = ['"control barrier function"', '"safety filter"', '"shield"', '"safety layer"',
           '"model predictive control"', '"reachability"', '"Lyapunov"']

DBLP = ["safe reinforcement learning autonomous driving", "safe reinforcement learning autonomous vehicle",
        "safe reinforcement learning vehicle", "constrained reinforcement learning driving",
        "constrained reinforcement learning vehicle", "safe reinforcement learning lane change",
        "safe reinforcement learning merging", "safe reinforcement learning intersection",
        "safe reinforcement learning platoon", "safe reinforcement learning cruise control",
        "reinforcement learning control barrier function vehicle", "reinforcement learning control barrier function driving",
        "reinforcement learning safety shield driving", "reinforcement learning shielding vehicle",
        "risk-aware reinforcement learning driving", "risk-sensitive reinforcement learning driving",
        "safe deep reinforcement learning driving", "safety reinforcement learning automated vehicle"]

runs = []


def http(url, tries=5, pause=1.0):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SLR-SafeRL-AV/1.0" + (f" (mailto:{MAIL})" if MAIL else "")})
            with urllib.request.urlopen(req, timeout=90) as r:
                txt = r.read().decode("utf-8", "ignore")
            time.sleep(pause)
            return txt
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (i + 1))
                continue
            time.sleep(3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def log(source, qid, query, n_reported, n_retrieved, note=""):
    runs.append({"date": TODAY, "source": source, "query_id": qid, "query": query,
                 "hits_reported": n_reported, "records_retrieved": n_retrieved, "note": note})
    print(f"{source:10s} {qid:14s} reported={n_reported} retrieved={n_retrieved} {note}", flush=True)


def openalex():
    for qid, (field, q) in OPENALEX.items():
        cursor, out, total = "*", [], None
        while cursor:
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
                {"filter": f"{field}:" + q, "per_page": 200, "cursor": cursor, **({"mailto": MAIL} if MAIL else {})})
            d = json.loads(http(url, pause=0.2))
            total = d["meta"]["count"]
            out += d["results"]
            cursor = d["meta"].get("next_cursor") if d["results"] else None
        (RAW / f"{qid}.json").write_text(json.dumps(out))
        log("OpenAlex", qid, f"{field}: {q}", total, len(out), "all years, all types")


def arxiv():
    ns = {"a": "http://www.w3.org/2005/Atom"}
    queries = {}
    for s in ARXIV_S:
        for v in ARXIV_V:
            queries[f"AX-S{ARXIV_S.index(s)}V{ARXIV_V.index(v)}"] = f"abs:{s} AND abs:{v}"
    for m in ARXIV_M:
        for v in ARXIV_V:
            queries[f"AX-M{ARXIV_M.index(m)}V{ARXIV_V.index(v)}"] = f'abs:"reinforcement learning" AND abs:{m} AND abs:{v}'
    allrec = {}
    for qid, q in queries.items():
        start, got, total = 0, [], 0
        while True:
            url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
                {"search_query": q, "start": start, "max_results": 200})
            txt = http(url, pause=3.1)
            if txt is None:
                break
            root = ET.fromstring(txt)
            total = int(root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults").text)
            ents = root.findall("a:entry", ns)
            for e in ents:
                rec = {"id": e.find("a:id", ns).text, "title": " ".join(e.find("a:title", ns).text.split()),
                       "summary": " ".join(e.find("a:summary", ns).text.split()),
                       "published": e.find("a:published", ns).text,
                       "authors": [a.find("a:name", ns).text for a in e.findall("a:author", ns)]}
                d = e.find("{http://arxiv.org/schemas/atom}doi")
                j = e.find("{http://arxiv.org/schemas/atom}journal_ref")
                rec["doi"] = d.text if d is not None else ""
                rec["journal_ref"] = j.text if j is not None else ""
                got.append(rec)
                allrec[rec["id"]] = rec
            start += 200
            if start >= total or not ents:
                break
        log("arXiv", qid, q, total, len(got))
    (RAW / "arxiv.json").write_text(json.dumps(list(allrec.values())))


def dblp():
    allrec = {}
    for i, q in enumerate(DBLP):
        url = "https://dblp.org/search/publ/api?" + urllib.parse.urlencode({"q": q, "format": "json", "h": 1000})
        txt = http(url, pause=1.5)
        try:
            res = json.loads(txt)["result"]
        except Exception:
            log("DBLP", f"DB-{i:02d}", q, "n/a", 0, "blocked by bot-protection page (non-JSON response); source not used")
            if i == 0:
                return
            continue
        hits = res.get("hits", {}).get("hit", [])
        for h in hits:
            allrec[h["info"].get("key")] = h["info"]
        log("DBLP", f"DB-{i:02d}", q, res["hits"]["@total"], len(hits), "title keywords (implicit AND, prefix match)")
    (RAW / "dblp.json").write_text(json.dumps(list(allrec.values())))


def semantic_scholar():
    q = ('("safe reinforcement learning" | "constrained reinforcement learning" | "safe RL") + '
         '("autonomous driving" | "autonomous vehicle" | "self-driving" | "automated vehicle")')
    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + urllib.parse.urlencode(
        {"query": q, "fields": "title,year,externalIds,venue,abstract,authors"})
    txt = http(url, tries=4)
    if txt is None:
        log("SemScholar", "S2-Q1", q, "n/a", 0, "HTTP 429 rate limit without API key; source not used")
        return
    d = json.loads(txt)
    (RAW / "s2.json").write_text(json.dumps(d.get("data", [])))
    log("SemScholar", "S2-Q1", q, d.get("total"), len(d.get("data", [])), "first page only (1000)")


if __name__ == "__main__":
    import sys
    todo = sys.argv[1:] or ["openalex", "dblp", "s2", "arxiv"]
    for name, fn in [("openalex", openalex), ("dblp", dblp), ("s2", semantic_scholar), ("arxiv", arxiv)]:
        if name in todo:
            fn()
    f = B / "search_runs.csv"
    new = not f.exists()
    with open(f, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(runs[0]))
        if new:
            w.writeheader()
        w.writerows(runs)
