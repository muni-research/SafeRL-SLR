#!/usr/bin/env python3
"""Write manuscript/included_studies.bib: one BibTeX entry per included study, keyed by its study ID
(e.g. B0761), from the bibliographic fields of extraction/evidence_db.csv (title, authors, year, venue,
DOI, publication type), which were taken from Crossref/OpenAlex metadata during screening.

Volume, issue and page numbers are not stored in the evidence database; they are added in the Phase 8
citation audit (Crossref lookup by DOI). Nothing is invented here.
"""
import csv
import re
import unicodedata
from pathlib import Path

W = Path(__file__).resolve().parent.parent
R = list(csv.DictReader(open(W / "extraction" / "evidence_db.csv")))

TEX = {"\u2010": "-", "\u2011": "-", "\u2012": "--", "\u2013": "--", "\u2014": "---", "\u2212": "-",   # hyphens and dashes (were dropped)
       "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": "", "}": "", "~": r"\~{}",
       "^": r"\^{}", "\\": ""}
OK = set(range(0x20, 0x7F)) | set(range(0xC0, 0x180)) - {0xD7, 0xF7}   # ASCII + Latin-1/Extended-A letters


def clean(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\$(\w)\$", r"\1", s)        # inline math of one symbol, e.g. "Level-$K$" -> "Level-K"
    out = []
    for ch in s:
        if ch in TEX:
            out.append(TEX[ch])
        elif ord(ch) in OK:
            out.append(ch)
        else:   # math-alphanumeric, Greek, dashes etc.: fall back to the closest ASCII form
            a = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            out.append(a if a else {"–": "--", "—": "---", "’": "'", "‘": "'",
                                    "“": "``", "”": "''"}.get(ch, ""))
    return "".join(out)


# Author lists whose index metadata disagrees with the paper; corrected from the first page of the PDF
# (checked with scripts/13b_lookup.py on 2026-10-09).
AUTHOR_FIX = {
    "E035": "Xuepei Yang; Mingtao Feng; Weisheng Dong; Lin Chen; Jie Feng; Fangfang Wu; Yufan Zhu; Ajmal Saeed Mian",  # first author in Chinese characters in metadata; name from the paper
    "B0716": "Zeqiao Li; Yijing Wang; Haoyu Wang; Zheng Li; Peng Li; Zhiqiang Zuo",   # metadata had inverted names
    "B1002": "Saeed Rahmani; Gözde Körpe; Zhenlin Xu; Bruno Brito; Simeon C. Calvert; Bart van Arem",
    "B1653": "Letian Kang; Jiandong Xing; Zhiyong Cui; Zhengxing Lan; Zihe Wang; Yilong Ren; Haiyang Yu",
    "B1686": "Xiaohui Hou; Minggang Gan; Wei Wu; Qianzhao Ma; Jie Chen",              # metadata had Chinese characters
    "B0209": "Bingqing Chen; Jonathan Francis; Jean Oh; Eric Nyberg; Sylvia L. Herbert",  # author list of arXiv v2
}


def authors(a):
    parts = [p.strip() for p in a.split(";") if p.strip()]
    parts = [re.sub(r"\s*\(\d+\)$", "", p) for p in parts]
    parts = [p.replace("Abderrafìâa", "Abderrafiâa") for p in parts]    # index encoding error          # index artefact, e.g. "Wenjie Huang (286015)"
    return " and ".join(clean(p) for p in parts) or "{Anonymous}"


import json
ENR = W / "manuscript" / "generated" / "bib_enrichment.json"      # from scripts/22_doi_audit.py (Crossref/DataCite)
ENRICH = json.loads(ENR.read_text()) if ENR.exists() else {}
TITLE_FIX = {"A140": "SRL-TR$^2$: A Safe Reinforcement Learning Based TRajectory TRacker Framework",
             # retitled in arXiv v2 (verified on arxiv.org 2026-10-17); the reference gives the current version
             "B0209": "Safe Autonomous Racing via Approximate Reachability on Ego-vision"}  # superscript lost in index

VENUE_FIX = {   # index artefacts (OpenAlex) -> journal/proceedings names as published
    'Proceedings - IEEE International Conference on Robotics and Automation/Proceedings': "IEEE International Conference on Robotics and Automation (ICRA)",
    "IEEE Conference on Cybernetics and Intelligent Systems": "IEEE International Conference on Cybernetics and Intelligent Systems (CIS) and Robotics, Automation and Mechatronics (RAM)",
    "Transportation Research Part C Emerging Technologies": "Transportation Research Part C: Emerging Technologies",
    "Transportation Research Part A Policy and Practice": "Transportation Research Part A: Policy and Practice",
    "IEEE Transactions on Systems Man and Cybernetics Systems": "IEEE Transactions on Systems, Man, and Cybernetics: Systems",
    "IEEE Intelligent Transportation Systems Conference (ITSC)": "IEEE International Conference on Intelligent Transportation Systems (ITSC)",
    "IEEE International Intelligent Transportation Systems Conference (ITSC)": "IEEE International Conference on Intelligent Transportation Systems (ITSC)",
    "Proceedings - International Conference on Tools with Artificial Intelligence, TAI": "IEEE International Conference on Tools with Artificial Intelligence (ICTAI)",
    "International Conference on Networking, Sensing and Control": "IEEE International Conference on Networking, Sensing and Control (ICNSC)",
    "IEEE Intelligent Vehicles Symposium": "IEEE Intelligent Vehicles Symposium (IV)",
    "Proceedings of the ... American Control Conference/Proceedings of the American Control Conference":
        "American Control Conference (ACC)",
    "Proceedings - IEEE International Conference on Robotics and Automation/Proceedings":
        "IEEE International Conference on Robotics and Automation (ICRA)",
    "Conference proceedings/Conference proceedings - IEEE International Conference on Systems, Man, and Cybernetics":
        "IEEE International Conference on Systems, Man, and Cybernetics (SMC)",
    "Proceedings of the IEEE Conference on Decision \\& Control, including the Symposium on Adaptive Processes":
        "IEEE Conference on Decision and Control (CDC)",
    "IEEE/ASME transactions on mechatronics": "IEEE/ASME Transactions on Mechatronics",
    "International Conference on Hybrid Systems: computation and control":
        "International Conference on Hybrid Systems: Computation and Control (HSCC)",
    "Physica A Statistical Mechanics and its Applications": "Physica A: Statistical Mechanics and its Applications",
    "EPTCS 411, 2024, pp. 160-177": "Electronic Proceedings in Theoretical Computer Science (EPTCS)",
}
LN = {"computer science", "intelligent transportation and infrastructure", "mechanical engineering"}


def venue_name(v):
    v = VENUE_FIX.get(v, v)
    m = re.match(r"Lecture notes in (.+)$", v)
    if m and m.group(1) in LN:
        v = "Lecture Notes in " + " ".join(w if w == "and" else w.capitalize() for w in m.group(1).split())
    v = re.sub(r"^\d{4} (IEEE )?(?:\d+(?:st|nd|rd|th) )?", r"\1", v)       # "2025 IEEE 28th ITSC" -> "IEEE ITSC"
    v = re.sub(r"^\d{4} \d+(?:st|nd|rd|th) ", "", v)
    return VENUE_FIX.get(v, v)


# arXiv identifiers from the bibliographic records (Stages A-C) or an arXiv DOI
import sys as _sys
csv.field_size_limit(_sys.maxsize)
ARXIV = {}
for _f in (W / "stageA" / "stageA_inventory.csv", W / "stageB" / "records_unique.csv", W / "stageC" / "records.csv", W / "stageE" / "records.csv"):
    for _r in csv.DictReader(open(_f)):
        if (_r.get("arxiv") or "").strip():
            ARXIV[_r["study_id"]] = re.sub(r"^arxiv[:.]", "", _r["arxiv"].strip(), flags=re.I)


def arxiv_id(r):
    m = re.search(r"10\.48550/arxiv\.(\S+)", r["doi"], re.I)
    return re.sub(r"^arxiv[:.]", "", ARXIV.get(r["study_id"]) or (m.group(1) if m else ""), flags=re.I)


# year of the cited (registered) version: Crossref "issued" year from the DOI cache (scripts/22). The analyses keep the
# year a study first appeared (e.g. early access); the reference list gives the year of the published version.
REG_YEAR = {}
for _f in (W / "fulltext" / "doi_cache").glob("*.json"):
    _d = json.load(open(_f)); _m = (_d.get("data") or {})
    _m = _m.get("message", _m) if isinstance(_m, dict) else {}
    try:
        REG_YEAR[_d["doi"].lower()] = str(_m["issued"]["date-parts"][0][0])
    except (KeyError, TypeError, IndexError):
        pass

# published versions without a DOI (PMLR; pages and URL verified on proceedings.mlr.press 2026-10-16)
PMLR = {"B0209": {"note": "First version titled ``Safety-aware Policy Optimisation for Autonomous Racing''"},
        "B1285": {"pages": "2445--2455", "url": "https://proceedings.mlr.press/v139/das21a.html"},
        "C0083": {"pages": "1078--1093", "url": "https://proceedings.mlr.press/v100/tang20a.html"}}

entries = []
for r in R:
    key, t = r["study_id"], r["pub_type"]
    ttl = TITLE_FIX.get(key) or clean(r["title"])
    f = {"author": authors(AUTHOR_FIX.get(key, r["authors"])), "title": "{" + ttl + "}", "year": r["year"]}
    venue = venue_name(clean(r["venue"])) or "Unpublished"
    if t == "journal":
        typ, f["journal"] = "article", venue
    elif t == "conference":
        typ, f["booktitle"] = "inproceedings", venue
    else:
        ax = arxiv_id(r)
        if ax:
            typ, f["howpublished"] = "misc", "arXiv preprint arXiv:" + re.sub(r"v\d+$", "", ax)
        elif re.search("arxiv", venue, re.I):
            typ, f["howpublished"] = "misc", "arXiv preprint"
        else:
            typ, f["howpublished"] = "misc", venue + (" preprint" if "preprint" not in venue.lower() else "")
    e = ENRICH.get(key, {})
    if typ in ("article", "inproceedings"):
        if e.get("volume") and typ == "article":
            f["volume"] = clean(e["volume"])
        if e.get("issue") and typ == "article":
            f["number"] = clean(e["issue"])
        if e.get("pages"):
            f["pages"] = clean(e["pages"]).replace("-", "--") if re.fullmatch(r"[\w]+-[\w]+", e["pages"]) else clean(e["pages"])
    if e.get("publisher") and typ == "inproceedings":
        f["publisher"] = clean(e["publisher"])
    if r["doi"]:
        f["doi"] = r["doi"]
    if typ == "misc" and f.get("howpublished", "").startswith("arXiv preprint arXiv:"):
        f["doi"] = "10.48550/arXiv." + f["howpublished"].split("arXiv:")[1]     # canonical arXiv DOI (DataCite)
    f.update(PMLR.get(key, {}))
    ry = REG_YEAR.get(r["doi"].lower()) if r["doi"] and not r["doi"].lower().startswith("10.48550/") else None
    if ry and ry != f["year"] and typ in ("article", "inproceedings"):
        f["year"] = ry
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f.items())
    entries.append(f"@{typ}{{{key},\n{body}\n}}")

out = W / "manuscript" / "included_studies.bib"
out.write_text("% generated by scripts/19_included_bib.py from extraction/evidence_db.csv -- do not edit\n\n"
               + "\n\n".join(entries) + "\n")
print(f"wrote {len(entries)} entries to {out.relative_to(W)}")
