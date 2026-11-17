"""Stage A step 2: resolve authoritative bibliographic metadata.

Order of resolution per record:
  1. DOI found in the PDF -> Crossref (accepted only if title matches the file/PDF title, sim >= 0.85,
     because the first pages can also contain DOIs of cited works).
  2. Crossref bibliographic title query (best of 5, sim >= 0.90).
  3. OpenAlex title search (sim >= 0.90) -> venue/year/authors/DOI.
     (Semantic Scholar was tried first on 2026-10-07 but returned HTTP 429 rate limits.)
  4. arXiv API by arXiv id found in the PDF.
Unresolved records are flagged metadata_status=manual.
All HTTP responses are cached in stageA/cache/ so the script is re-runnable offline.
Output: stageA/resolved_metadata.json
"""
import os
import difflib, hashlib, json, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent.parent / "stageA"
CACHE = OUT / "cache"
CACHE.mkdir(exist_ok=True)
CONTACT = os.environ.get("SLR_CONTACT_EMAIL", "")  # optional polite-pool contact; never hard-coded
UA = "SLR-SafeRL-AV/1.0" + (f" (mailto:{CONTACT})" if CONTACT else "")


def get(url, pause=0.4, tries=4):
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".txt")
    if key.exists():
        return key.read_text()
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                txt = r.read().decode("utf-8", "ignore")
            key.write_text(txt)
            time.sleep(pause)
            return txt
        except urllib.error.HTTPError as e:
            if e.code == 404:
                key.write_text("")
                return ""
            time.sleep(3 * (i + 1) + (10 if e.code == 429 else 0))
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def norm(t):
    t = (t or "").lower().replace("‐", "-")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return max(min(len(a), len(b)) / max(len(a), len(b)), 0.9 if min(len(a), len(b)) > 40 else 0)
    return difflib.SequenceMatcher(None, a, b).ratio()


def ref_titles(r):
    ts = [r["filename_title"]]
    if len(r["pdf_meta_title"]) > 15:
        ts.append(r["pdf_meta_title"])
    return ts


def best_sim(r, title):
    return max(sim(t, title) for t in ref_titles(r))


def from_crossref(m):
    return {
        "title": (m.get("title") or [""])[0],
        "authors": "; ".join(f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in m.get("author", [])),
        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "venue": (m.get("container-title") or [""])[0],
        "publisher": m.get("publisher", ""),
        "type": m.get("type", ""),
        "doi": m.get("DOI", ""),
        "abstract_cr": re.sub(r"<[^>]+>", " ", m.get("abstract", "")).strip(),
    }


def crossref_doi(doi):
    t = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if not t:
        return None
    try:
        return from_crossref(json.loads(t)["message"])
    except Exception:
        return None


def crossref_query(title):
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5})
    t = get("https://api.crossref.org/works?" + q)
    if not t:
        return []
    try:
        return [from_crossref(m) for m in json.loads(t)["message"]["items"]]
    except Exception:
        return []


def s2_match(title):
    fields = "title,authors,year,venue,publicationVenue,externalIds,abstract,publicationTypes"
    q = urllib.parse.urlencode({"query": title, "fields": fields})
    t = get("https://api.semanticscholar.org/graph/v1/paper/search/match?" + q, pause=1.2)
    if not t:
        return None
    try:
        d = json.loads(t)["data"][0]
    except Exception:
        return None
    ext = d.get("externalIds") or {}
    pv = d.get("publicationVenue") or {}
    return {
        "title": d.get("title", ""),
        "authors": "; ".join(a["name"] for a in d.get("authors", [])),
        "year": d.get("year"),
        "venue": pv.get("name") or d.get("venue", ""),
        "publisher": "",
        "type": ",".join(d.get("publicationTypes") or []),
        "doi": ext.get("DOI", ""),
        "arxiv": ext.get("ArXiv", ""),
        "abstract_cr": d.get("abstract") or "",
    }


def openalex_search(title):
    q = urllib.parse.urlencode({"search": title, "per_page": 5, **({"mailto": CONTACT} if CONTACT else {})})
    t = get("https://api.openalex.org/works?" + q, pause=0.3)
    if not t:
        return []
    out = []
    try:
        for d in json.loads(t)["results"]:
            src = ((d.get("primary_location") or {}).get("source") or {})
            out.append({
                "title": d.get("title") or "",
                "authors": "; ".join(a["author"]["display_name"] for a in d.get("authorships", [])),
                "year": d.get("publication_year"),
                "venue": src.get("display_name") or "",
                "publisher": src.get("host_organization_name") or "",
                "type": d.get("type", ""),
                "doi": (d.get("doi") or "").replace("https://doi.org/", ""),
                "abstract_cr": "",
            })
    except Exception:
        pass
    return out


def arxiv_lookup(aid):
    t = get(f"http://export.arxiv.org/api/query?id_list={aid}", pause=3)
    if not t:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    try:
        e = ET.fromstring(t).find("a:entry", ns)
        jr = e.find("x:journal_ref", ns)
        doi = e.find("x:doi", ns)
        return {
            "title": re.sub(r"\s+", " ", e.find("a:title", ns).text),
            "authors": "; ".join(a.find("a:name", ns).text for a in e.findall("a:author", ns)),
            "year": int(e.find("a:published", ns).text[:4]),
            "venue": jr.text if jr is not None else f"arXiv preprint arXiv:{aid}",
            "publisher": "arXiv",
            "type": "preprint",
            "doi": doi.text if doi is not None else "",
            "arxiv": aid,
            "abstract_cr": re.sub(r"\s+", " ", e.find("a:summary", ns).text).strip(),
        }
    except Exception:
        return None


def main():
    recs = json.loads((OUT / "raw_extract.json").read_text())
    out = []
    for r in recs:
        res, how, score = None, "", 0.0
        for d in r["doi_candidates"][:6]:
            m = crossref_doi(d)
            if m:
                s = best_sim(r, m["title"])
                if s >= 0.85:
                    res, how, score = m, "crossref_doi", s
                    break
        if not res:
            cands = [(best_sim(r, m["title"]), m) for m in crossref_query(r["filename_title"])]
            cands.sort(key=lambda x: -x[0])
            if cands and cands[0][0] >= 0.90:
                score, res = cands[0]
                how = "crossref_title"
        if not res:
            cands = [(best_sim(r, m["title"]), m) for m in openalex_search(r["filename_title"])]
            cands.sort(key=lambda x: -x[0])
            if cands and cands[0][0] >= 0.90:
                score, res = cands[0]
                how = "openalex_title"
        if not res and r["arxiv_id"]:
            m = arxiv_lookup(r["arxiv_id"])
            if m and best_sim(r, m["title"]) >= 0.80:
                res, how, score = m, "arxiv", best_sim(r, m["title"])
        rec = {"study_id": r["study_id"], "metadata_source": how or "none",
               "title_similarity": round(score, 3), "metadata_status": "ok" if res else "manual"}
        rec.update(res or {})
        out.append(rec)
        print(r["study_id"], rec["metadata_status"], how, round(score, 2), (rec.get("title") or r["filename_title"])[:70], flush=True)
    (OUT / "resolved_metadata.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    from collections import Counter
    print(Counter(x["metadata_source"] for x in out))


if __name__ == "__main__":
    main()
