"""Stage B step 2: normalise, merge and de-duplicate search results; link them to Stage A.

Inputs : stageB/raw/{OA-Q1,OA-Q2,arxiv,s2}.json and any files in stageB/manual_exports/
         (RIS, Scopus CSV, IEEE CSV, Web of Science tab-delimited/plain RIS, BibTeX).
Outputs: stageB/records_all.csv        every retrieved record, one row per (source, record)
         stageB/records_unique.csv     de-duplicated records with B### IDs (IDs frozen in stageB/study_ids.csv)
         stageB/duplicate_log.csv      every removed duplicate and the record it matched
         stageB/recall_check.txt       how many Stage A Include/Unsure records the searches retrieved
Matching: DOI (case-insensitive, arXiv DOIs mapped to arXiv id), then normalised title (exact), then
fuzzy title >= 0.93 with same first-author surname or |year diff| <= 1.
"""
import csv, difflib, html, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent.parent / "stageB"
A = Path(__file__).resolve().parent.parent / "stageA"
RAW, MAN = B / "raw", B / "manual_exports"


def norm_title(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def norm_doi(d):
    d = (d or "").lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d.rstrip(".")


def arxiv_key(s):
    m = re.search(r"(\d{4}\.\d{4,5})", s or "")
    return m.group(1) if m else ""


def oa_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idx in inv.items():
        for i in idx:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def rec(source, qid, title, authors, year, venue, doi, abstract, rtype, url="", arxiv=""):
    doi = norm_doi(doi)
    if doi.startswith("10.48550/arxiv."):
        arxiv = arxiv or doi.split("arxiv.")[1]
    return {"source": source, "query_id": qid, "title": " ".join(html.unescape(re.sub(r"<[^>]+>", "", title or "")).split()),
            "authors": authors, "year": str(year or ""), "venue": venue or "", "doi": doi,
            "arxiv": arxiv_key(arxiv) if arxiv else "", "type": rtype or "",
            "abstract": " ".join((abstract or "").split()), "url": url}


def load_openalex():
    out = []
    for qid in ("OA-Q1v2", "OA-Q2v2", "OA-Q3v2"):  # v1 pilot files (OA-Q1/OA-Q2) are kept for audit only
        f = RAW / f"{qid}.json"
        if not f.exists():
            continue
        for d in json.loads(f.read_text()):
            src = ((d.get("primary_location") or {}).get("source") or {})
            ax = ""
            for loc in d.get("locations") or []:
                lp = (loc.get("landing_page_url") or "")
                if "arxiv.org" in lp:
                    ax = lp
            out.append(rec("OpenAlex", qid, d.get("title"),
                           "; ".join(a["author"]["display_name"] for a in d.get("authorships", [])),
                           d.get("publication_year"), src.get("display_name"), d.get("doi"),
                           oa_abstract(d.get("abstract_inverted_index")), d.get("type"), d.get("id"), ax))
    return out


def load_arxiv():
    f = RAW / "arxiv.json"
    if not f.exists():
        return []
    return [rec("arXiv", "AX-*", d["title"], "; ".join(d["authors"]), d["published"][:4],
                d.get("journal_ref") or "arXiv", d.get("doi"), d["summary"], "preprint", d["id"], d["id"])
            for d in json.loads(f.read_text())]


def load_s2():
    f = RAW / "s2.json"
    if not f.exists():
        return []
    out = []
    for d in json.loads(f.read_text()):
        ext = d.get("externalIds") or {}
        out.append(rec("SemanticScholar", "S2-Q1", d.get("title"), "; ".join(a["name"] for a in d.get("authors") or []),
                       d.get("year"), d.get("venue"), ext.get("DOI"), d.get("abstract"), "", "", ext.get("ArXiv", "")))
    return out


# ---------- manual exports ----------
def parse_ris(path):
    recs, cur = [], defaultdict(list)
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", line)
        if not m:
            continue
        tag, val = m.groups()
        if tag == "ER":
            recs.append(cur); cur = defaultdict(list)
        else:
            cur[tag].append(val.strip())
    g = lambda r, *tags: next((r[t][0] for t in tags if r.get(t)), "")
    return [rec(f"manual:{path.stem}", path.stem, g(r, "TI", "T1"), "; ".join(r.get("AU", []) + r.get("A1", [])),
                g(r, "PY", "Y1")[:4], g(r, "T2", "JO", "JF", "SO"), g(r, "DO"), g(r, "AB", "N2"), g(r, "TY"))
            for r in recs]


def parse_bib(path):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    out = []
    for ent in re.split(r"\n@", "\n" + txt)[1:]:
        f = {k.lower(): v for k, v in re.findall(r"(\w+)\s*=\s*[{\"](.+?)[}\"]\s*,?\s*\n", ent, flags=re.S)}
        out.append(rec(f"manual:{path.stem}", path.stem, f.get("title", ""), f.get("author", "").replace(" and ", "; "),
                       f.get("year", ""), f.get("journal", f.get("booktitle", "")), f.get("doi", ""),
                       f.get("abstract", ""), ent.split("{", 1)[0]))
    return out


def parse_table(path):
    delim = "\t" if path.suffix.lower() in (".txt", ".tsv") else ","
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig", errors="ignore"), delimiter=delim))
    pick = lambda r, *ks: next((r[k] for k in ks if r.get(k)), "")
    return [rec(f"manual:{path.stem}", path.stem,
                pick(r, "Title", "Document Title", "TI", "Article Title"),
                pick(r, "Authors", "Author full names", "AU", "Author Full Names"),
                pick(r, "Year", "Publication Year", "PY"),
                pick(r, "Source title", "Publication Title", "SO", "Source Title"),
                pick(r, "DOI", "DI"), pick(r, "Abstract", "AB"),
                pick(r, "Document Type", "DT", "Document Identifier")) for r in rows]


def load_manual():
    out = []
    for p in sorted(MAN.glob("*")):
        sfx = p.suffix.lower()
        if sfx in (".ris", ".nbib"):
            out += parse_ris(p)
        elif sfx == ".bib":
            out += parse_bib(p)
        elif sfx in (".csv", ".tsv", ".txt"):
            out += parse_table(p)
    return out


# ---------- de-duplication ----------
def first_surname(a):
    a = (a or "").split(";")[0].strip()
    return (a.split(",")[0] if "," in a else (a.split()[-1] if a.split() else "")).lower()


def main():
    allrecs = load_openalex() + load_arxiv() + load_s2() + load_manual()
    allrecs = [r for r in allrecs if r["title"]]
    with open(B / "records_all.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrecs[0])); w.writeheader(); w.writerows(allrecs)

    # Stage A index (all 211 records; the review is cumulative)
    stageA = list(csv.DictReader(open(A / "stageA_inventory.csv")))
    a_doi = {norm_doi(r["doi"]): r["study_id"] for r in stageA if r["doi"]}
    a_ax = {arxiv_key(r["arxiv"]): r["study_id"] for r in stageA if arxiv_key(r["arxiv"])}
    a_tit = {norm_title(r["title"]): r["study_id"] for r in stageA}

    uniq, dup_log = [], []
    by_doi, by_ax, by_tit = {}, {}, {}

    def match_existing(r):
        if r["doi"] and r["doi"] in by_doi:
            return by_doi[r["doi"]], "doi"
        if r["arxiv"] and r["arxiv"] in by_ax:
            return by_ax[r["arxiv"]], "arxiv id"
        t = norm_title(r["title"])
        if t in by_tit:
            return by_tit[t], "title exact"
        if len(t) > 25:
            for u in uniq:
                ut = norm_title(u["title"])
                if abs(len(ut) - len(t)) >= 15:
                    continue
                sm = difflib.SequenceMatcher(None, t, ut)
                if sm.real_quick_ratio() >= 0.93 and sm.quick_ratio() >= 0.93 and sm.ratio() >= 0.93:
                    yd = abs(int(u["year"] or 0) - int(r["year"] or 0)) if (u["year"] and r["year"]) else 0
                    if first_surname(u["authors"]) == first_surname(r["authors"]) or yd <= 1:
                        return u, "title fuzzy"
        return None, ""

    # prefer peer-reviewed records first so they become the kept version
    order = sorted(allrecs, key=lambda r: (r["type"] in ("preprint", "posted-content") or "arxiv" in r["venue"].lower(), r["source"]))
    for r in order:
        m, how = match_existing(r)
        if m:
            m["sources"] = ";".join(sorted(set(m["sources"].split(";")) | {r["source"]}))
            m["query_ids"] = ";".join(sorted(set(m["query_ids"].split(";")) | {r["query_id"]}))
            if not m["abstract"] and r["abstract"]:
                m["abstract"] = r["abstract"]
            if not m["arxiv"] and r["arxiv"]:
                m["arxiv"] = r["arxiv"]; by_ax[r["arxiv"]] = m
            if how != "doi" or r["source"] != m["source"]:
                dup_log.append({"removed_source": r["source"], "removed_title": r["title"], "removed_doi": r["doi"],
                                "kept_title": m["title"], "kept_doi": m["doi"], "match": how})
            continue
        u = dict(r); u["sources"] = r["source"]; u["query_ids"] = r["query_id"]
        uniq.append(u)
        if u["doi"]:
            by_doi[u["doi"]] = u
        if u["arxiv"]:
            by_ax[u["arxiv"]] = u
        by_tit[norm_title(u["title"])] = u

    # link to Stage A
    for u in uniq:
        sid = a_doi.get(u["doi"]) or a_ax.get(u["arxiv"]) or a_tit.get(norm_title(u["title"]))
        if not sid:
            t = norm_title(u["title"])
            for at, s in a_tit.items():
                sm = difflib.SequenceMatcher(None, at, t)
                if abs(len(at) - len(t)) < 15 and sm.quick_ratio() >= 0.93 and sm.ratio() >= 0.93:
                    sid = s; break
        u["in_stageA"] = sid or ""

    # frozen B IDs
    idf = B / "study_ids.csv"
    ids = {}
    if idf.exists():
        ids = {r["key"]: r["study_id"] for r in csv.DictReader(open(idf))}
    nxt = max([int(v[1:]) for v in ids.values()] or [0]) + 1
    for u in sorted(uniq, key=lambda x: (x["year"], norm_title(x["title"]))):
        key = u["doi"] or ("arxiv:" + u["arxiv"] if u["arxiv"] else "t:" + norm_title(u["title"]))
        if key not in ids:
            ids[key] = f"B{nxt:04d}"; nxt += 1
        u["study_id"] = ids[key]
    with open(idf, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["study_id", "key"])
        for k, v in sorted(ids.items(), key=lambda x: x[1]):
            w.writerow([v, k])

    cols = ["study_id", "in_stageA", "title", "authors", "year", "venue", "doi", "arxiv", "type", "sources",
            "query_ids", "abstract", "url"]
    uniq.sort(key=lambda x: x["study_id"])
    with open(B / "records_unique.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(uniq)
    with open(B / "duplicate_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dup_log[0]) if dup_log else ["match"]); w.writeheader(); w.writerows(dup_log)

    # recall against Stage A Include/Unsure (known-relevant set)
    gold = [r for r in stageA if r["decision"] in ("Include", "Unsure")]
    found = {u["in_stageA"] for u in uniq if u["in_stageA"]}
    hit = [r for r in gold if r["study_id"] in found]
    miss = [r for r in gold if r["study_id"] not in found]
    inc = [r for r in gold if r["decision"] == "Include"]
    inc_hit = [r for r in inc if r["study_id"] in found]
    rep = [f"Records retrieved (all sources): {len(allrecs)}",
           f"Unique after de-duplication: {len(uniq)}  (duplicates removed: {len(allrecs) - len(uniq)})",
           f"Unique records already in Stage A: {sum(bool(u['in_stageA']) for u in uniq)}",
           f"Recall vs Stage A Include: {len(inc_hit)}/{len(inc)} = {len(inc_hit) / len(inc):.0%}",
           f"Recall vs Stage A Include+Unsure: {len(hit)}/{len(gold)} = {len(hit) / len(gold):.0%}",
           "Missed Stage A Include/Unsure records:"] + [f"  {r['study_id']} [{r['decision']}] {r['title'][:100]}" for r in miss]
    (B / "recall_check.txt").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))
    from collections import Counter
    print("by source (unique, first source):", Counter(u["sources"].split(";")[0] for u in uniq))


if __name__ == "__main__":
    main()
