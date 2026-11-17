"""Stage A step 1: extract text-level metadata from the seed-corpus PDFs.

Output: SLR_Workspace/stageA/raw_extract.json
Study IDs (A001...) are assigned in sorted order of subfolder (numeric range) then filename,
and are frozen in stageA/study_ids.csv on first run so they never change afterwards.
"""
import csv, json, re
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Articles for Review"
OUT = Path(__file__).resolve().parent.parent / "stageA"
OUT.mkdir(parents=True, exist_ok=True)

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>,;]+)", re.I)


def folder_key(p):
    m = re.match(r"(\d+)", p.parent.name)
    return (int(m.group(1)) if m else 9999, p.name.lower())


def clean_doi(d):
    d = d.rstrip(".)]}").strip()
    d = re.sub(r"(\.pdf|\.html?)$", "", d, flags=re.I)
    return d


def find_abstract(text):
    m = re.search(r"(?is)\babstract\b[\s:—–.-]*(.{200,3000}?)(?:\n\s*(?:index terms|keywords?|key words|1\.?\s*introduction|i\.\s*introduction|introduction)\b)", text)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def find_keywords(text):
    m = re.search(r"(?is)\b(?:index terms|keywords?|key words)\b[\s:—–-]*(.{5,400}?)(?:\n\s*\n|\n\s*(?:1\.?\s*)?introduction|\n\s*i\.\s)", text)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main():
    pdfs = sorted(SRC.glob("*/*.pdf"), key=folder_key)
    id_file = OUT / "study_ids.csv"
    ids = {}
    if id_file.exists():
        with open(id_file) as f:
            ids = {r["rel_path"]: r["study_id"] for r in csv.DictReader(f)}
    nxt = max([int(v[1:]) for v in ids.values()] or [0]) + 1
    for p in pdfs:
        rel = str(p.relative_to(ROOT))
        if rel not in ids:
            ids[rel] = f"A{nxt:03d}"
            nxt += 1
    with open(id_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["study_id", "rel_path"])
        for rel, sid in sorted(ids.items(), key=lambda x: x[1]):
            w.writerow([sid, rel])

    recs = []
    for p in pdfs:
        rel = str(p.relative_to(ROOT))
        doc = pymupdf.open(p)
        head = "".join(doc[i].get_text() for i in range(min(3, doc.page_count)))
        p1 = doc[0].get_text()
        dois = [clean_doi(d) for d in DOI_RE.findall(head)]
        meta = doc.metadata or {}
        recs.append({
            "study_id": ids[rel],
            "rel_path": rel,
            "subfolder": p.parent.name,
            "filename": p.name,
            "filename_title": p.stem,
            "pages": doc.page_count,
            "pdf_meta_title": (meta.get("title") or "").strip(),
            "pdf_meta_author": (meta.get("author") or "").strip(),
            "doi_candidates": list(dict.fromkeys(dois)),
            "arxiv_id": (re.search(r"arXiv:(\d{4}\.\d{4,5})", head) or [None, ""])[1],
            "abstract": find_abstract(head),
            "keywords": find_keywords(head),
            "page1_text": p1[:4000],
        })
    (OUT / "raw_extract.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False))
    print(f"{len(recs)} PDFs; with DOI candidate: {sum(bool(r['doi_candidates']) for r in recs)}; "
          f"with abstract: {sum(bool(r['abstract']) for r in recs)}")


if __name__ == "__main__":
    main()
