#!/usr/bin/env python3
"""Phase 8: retrieve full texts of citation-search candidates that passed title/abstract screening (Unsure).

Sources, in order: OpenAlex open-access locations (best_oa_location, locations), then arXiv (by arXiv id in
the OpenAlex record or exact-title search). PDFs go to fulltext/stageC/<cid>.pdf; PDFs the authors add go to
fulltext/stageC_institutional/<cid>.pdf and are picked up on the next run.
Output: stageC/retrieval_status.csv and stageC/needs_institutional_access.csv
"""
import csv, json, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path(__file__).resolve().parent.parent
C = W / "stageC"
OUT = W / "fulltext" / "stageC"; INST = W / "fulltext" / "stageC_institutional"
OUT.mkdir(parents=True, exist_ok=True); INST.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (SLR-SafeRL-AV/1.0 systematic review full-text retrieval)"}


def get_json(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(2 * (i + 1))
    return {}


def fetch(url, dest):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
            data = r.read()
        if data[:5] != b"%PDF-":
            return False
        dest.write_bytes(data); return True
    except Exception:
        return False


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def arxiv_by_title(title):
    q = urllib.parse.quote(f'ti:"{title}"')
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"http://export.arxiv.org/api/query?search_query={q}&max_results=5", headers=UA), timeout=40) as r:
            xml = r.read().decode()
    except Exception:
        return None
    for entry in xml.split("<entry>")[1:]:
        t = re.search(r"<title>(.*?)</title>", entry, re.S).group(1)
        if norm(t) == norm(title):
            return re.search(r"<id>http://arxiv.org/abs/(.*?)</id>", entry).group(1)
    return None


def retrieve(r):
    cid = r["cid"]; dest = OUT / f"{cid}.pdf"
    if (INST / f"{cid}.pdf").exists():
        return cid, "institutional (added by authors)", ""
    if dest.exists():
        return cid, "open access", ""
    d = get_json(f"https://api.openalex.org/works/{r['openalex']}?select=best_oa_location,locations,ids")
    urls = []
    for l in [d.get("best_oa_location")] + (d.get("locations") or []):
        for k in ("pdf_url",):
            u = (l or {}).get(k)
            if u and u not in urls:
                urls.append(u)
    for u in urls:
        if fetch(u, dest):
            return cid, "open access", u
    ax = None
    for l in d.get("locations") or []:
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$", (l or {}).get("landing_page_url") or "")
        if m:
            ax = m.group(1); break
    if not ax:
        ax = arxiv_by_title(r["title"]); time.sleep(3)
    if ax and fetch(f"https://arxiv.org/pdf/{ax}", dest):
        return cid, "open access (arXiv)", f"arXiv:{ax}"
    return cid, "not retrieved", ""


cands = {r["cid"]: r for r in csv.DictReader(open(C / "candidates.csv"))}
sought = [cands[r["cid"]] for r in csv.DictReader(open(C / "screening_decisions.csv")) if r["decision"] in ("Include", "Unsure")]
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(retrieve, sought))
with open(C / "retrieval_status.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["cid", "status", "source_url"]); w.writerows(res)
with open(C / "needs_institutional_access.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["study_id", "title", "year", "venue", "doi", "link", "save_as", "Downloaded"])
    for cid, s, _ in res:
        if s == "not retrieved":
            c = cands[cid]; w.writerow([cid, c["title"], c["year"], c["venue"], c["doi"], f"https://doi.org/{c['doi']}" if c["doi"] else "", f"SLR_Workspace/fulltext/stageC_institutional/{cid}.pdf", ""])
from collections import Counter
print(len(sought), Counter(s for _, s, _ in res))
