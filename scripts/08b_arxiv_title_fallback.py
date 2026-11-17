"""Stage B step 4b: for records still NOT RETRIEVED, look for an open preprint (arXiv) version by title.
Lookup goes through OpenAlex title search (the arXiv API rate-limited this client with HTTP 429 on 2026-10-07);
any OpenAlex location whose PDF/landing URL is on arxiv.org is downloaded from arxiv.org/pdf/<id>.
Accepts a match only if normalised title similarity >= 0.93. The arXiv version is used for the full-text
assessment and is flagged as 'open access (arXiv preprint version)' (content may differ from the
published version; the published version is cited). Then rewrites retrieval_status.csv and
needs_institutional_access.csv.
"""
import os
import csv, difflib, json, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FT = Path(__file__).resolve().parent.parent / "fulltext"
CONTACT = os.environ.get("SLR_CONTACT_EMAIL", "")  # optional polite-pool contact; never hard-coded
UA = {"User-Agent": "SLR-SafeRL-AV/1.0" + (f" (mailto:{CONTACT})" if CONTACT else "")}
ns = {"a": "http://www.w3.org/2005/Atom"}
norm = lambda t: re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def search(title):
    q = re.sub(r"[^A-Za-z0-9 ]+", " ", title)
    stop = {"with", "using", "for", "the", "and", "via", "from", "based", "towards", "toward", "under", "into", "through", "its", "of", "on", "in", "an"}
    words = [w for w in q.split() if len(w) > 2 and w.lower() not in stop]
    words = sorted(words, key=len, reverse=True)[:6]  # arXiv returns nothing for long AND chains / stopwords
    q = " AND ".join(f"ti:{w}" for w in words)
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": q, "max_results": 5})
    for i in range(3):
        try:
            return ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except Exception:
            time.sleep(5 * (i + 1))
    return None


def openalex_arxiv(title):
    q = urllib.parse.urlencode({"search": title, "per_page": 5, **({"mailto": CONTACT} if CONTACT else {})})
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://api.openalex.org/works?" + q, headers=UA), timeout=40))
    except Exception:
        return None
    for w in d.get("results", []):
        if difflib.SequenceMatcher(None, norm(w.get("title")), norm(title)).ratio() < 0.93:
            continue
        for loc in w.get("locations") or []:
            for u in (loc.get("pdf_url") or "", loc.get("landing_page_url") or ""):
                m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", u)
                if m:
                    return m.group(1)
    return None


def main():
    status = list(csv.DictReader(open(FT / "retrieval_status.csv")))
    need = {r["study_id"]: r for r in csv.DictReader(open(FT / "needs_institutional_access.csv"))}
    for s in status:
        if s["status"] != "NOT RETRIEVED":
            continue
        r = need[s["study_id"]]
        aid = openalex_arxiv(r["title"])
        if not aid:
            continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers=UA), timeout=60).read()
            if data[:5] == b"%PDF-":
                (FT / "open_access" / f"{s['study_id']}.pdf").write_bytes(data)
                s["status"] = "open access (arXiv preprint version)"; s["arxiv"] = aid
                del need[s["study_id"]]
                print(s["study_id"], "->", aid, flush=True)
        except Exception:
            pass
        time.sleep(1)
    with open(FT / "retrieval_status.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(status[0])); w.writeheader(); w.writerows(status)
    with open(FT / "needs_institutional_access.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["study_id", "title", "year", "venue", "doi", "link", "save_as"])
        w.writeheader(); w.writerows(need.values())
    print(f"still not retrieved: {len(need)}")


if __name__ == "__main__":
    main()
