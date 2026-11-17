"""Stage B step 4: retrieve full texts for records that passed title/abstract screening.

For each Stage B record with decision Include/Unsure (stageB/screening_decisions.csv):
  1. already in Stage A -> use the seed PDF (no download)
  2. arXiv id           -> https://arxiv.org/pdf/<id>
  3. DOI                -> Unpaywall open-access PDF locations, then OpenAlex open-access URLs
  4. otherwise          -> listed in fulltext/needs_institutional_access.csv for the authors to obtain
PDFs are saved as fulltext/open_access/<study_id>.pdf. PDFs the authors add go to
fulltext/institutional/<study_id>.pdf and are detected on the next run.
Outputs: fulltext/retrieval_status.csv, fulltext/needs_institutional_access.csv
"""
import os
import csv, json, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent.parent / "stageB"
FT = Path(__file__).resolve().parent.parent / "fulltext"
OA, INST = FT / "open_access", FT / "institutional"
OA.mkdir(parents=True, exist_ok=True); INST.mkdir(parents=True, exist_ok=True)
MAIL = os.environ.get("SLR_CONTACT_EMAIL", "")  # optional polite-pool contact; never hard-coded
UA = {"User-Agent": "SLR-SafeRL-AV/1.0" + (f" (mailto:{MAIL})" if MAIL else "")}


def fetch(url, dest):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if data[:5] != b"%PDF-":
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def unpaywall(doi):
    if not MAIL:          # Unpaywall requires a contact e-mail; skipped unless SLR_CONTACT_EMAIL is set
        return []
    try:
        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={MAIL}"
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40))
        locs = [d.get("best_oa_location") or {}] + (d.get("oa_locations") or [])
        return [l.get("url_for_pdf") for l in locs if l and l.get("url_for_pdf")]
    except Exception:
        return []


def openalex_oa(doi):
    try:
        url = f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}" + (f"?mailto={MAIL}" if MAIL else "")
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        urls = [(l or {}).get("pdf_url") for l in [d.get("best_oa_location")] + (d.get("locations") or [])]
        return [u for u in dict.fromkeys(urls) if u]
    except Exception:
        return []


def retrieve(r, dest):
    if r["arxiv"] and fetch(f"https://arxiv.org/pdf/{r['arxiv']}", dest):
        return "open access (arXiv)"
    if r["doi"]:
        for u in unpaywall(r["doi"]):
            if fetch(u, dest):
                return "open access (Unpaywall)"
        for u in openalex_oa(r["doi"]):
            if fetch(u, dest):
                return "open access (OpenAlex)"
    return ""


def main():
    recs = {r["study_id"]: r for r in csv.DictReader(open(B / "records_unique.csv"))}
    dec = [r for r in csv.DictReader(open(B / "screening_decisions.csv")) if r["decision"] in ("Include", "Unsure")]
    status, need = [], []
    def work(d):
        r = recs[d["study_id"]]
        sid, dest = r["study_id"], OA / f"{r['study_id']}.pdf"
        if r["in_stageA"]:
            return d, r, f"seed corpus ({r['in_stageA']})"
        if (INST / f"{sid}.pdf").exists():
            return d, r, "institutional (added by authors)"
        if dest.exists():
            return d, r, "open access (cached)"
        return d, r, retrieve(r, dest)

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(work, dec))
    # keep the authors' tracking list stable: every report that needed institutional access stays listed,
    # with its `Downloaded` value (Yes once the PDF is in institutional/)
    prev = {}
    if (FT / "needs_institutional_access.csv").exists():
        prev = {x["study_id"]: x.get("Downloaded", "") for x in csv.DictReader(open(FT / "needs_institutional_access.csv"))}
    for d, r, how in results:
        sid = r["study_id"]
        if not how or how.startswith("institutional"):
            need.append({"study_id": sid, "title": r["title"], "year": r["year"], "venue": r["venue"],
                         "doi": r["doi"], "link": f"https://doi.org/{r['doi']}" if r["doi"] else r["url"],
                         "save_as": f"SLR_Workspace/fulltext/institutional/{sid}.pdf",
                         "Downloaded": "Yes" if how else prev.get(sid, "")})
        status.append({"study_id": sid, "decision": d["decision"], "status": how or "NOT RETRIEVED",
                       "doi": r["doi"], "arxiv": r["arxiv"]})
    with open(FT / "retrieval_status.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(status[0])); w.writeheader(); w.writerows(status)
    with open(FT / "needs_institutional_access.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["study_id", "title", "year", "venue", "doi", "link", "save_as", "Downloaded"])
        w.writeheader(); w.writerows(need)
    n_missing = sum(1 for x in status if x["status"] == "NOT RETRIEVED")
    print(f"retrieved {len(status) - n_missing}/{len(status)}; still not retrieved: {n_missing}")


if __name__ == "__main__":
    main()
