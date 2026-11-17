"""Stage A step 4: build the inventory workbook, duplicate log, PRISMA Stage-A counts and
the 20% consistency-check sample.

Inputs : stageA/raw_extract.json, stageA/resolved_metadata.json, stageA/fulltext_indicators.csv,
         stageA/screening_decisions.csv
Outputs: stageA/stageA_inventory.xlsx (+ stageA_inventory.csv), stageA/duplicate_log.csv,
         logs/prisma_counts.txt (Stage A block), stageA/consistency_sample.csv
"""
import csv, html, json, random, re
from collections import Counter
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

ROOT = Path(__file__).resolve().parents[2]
A = Path(__file__).resolve().parent.parent / "stageA"
LOGS = Path(__file__).resolve().parent.parent / "logs"

raw = {r["study_id"]: r for r in json.loads((A / "raw_extract.json").read_text())}
meta = {r["study_id"]: r for r in json.loads((A / "resolved_metadata.json").read_text())}
ind = {r["study_id"]: r for r in csv.DictReader(open(A / "fulltext_indicators.csv"))}
scr = {r["study_id"]: r for r in csv.DictReader(open(A / "screening_decisions.csv"))}
assert set(raw) == set(meta) == set(ind) == set(scr), "ID sets differ between inputs"

DUP_OF = {"A067": ("A066", "identical file (same DOI)"),
          "A083": ("A082", "identical file (same DOI)"),
          "A107": ("A106", "identical file (same DOI)"),
          "A154": ("A037", "conference version (IEEE ITSC 2024) superseded by extended journal version (IEEE T-ITS 2025); same first author and method line"),
          "A208": ("A077", "conference version superseded by extended journal version (Neurocomputing 2024); same authors and method")}

COLS = ["study_id", "decision", "reason_code", "domain", "domain_uncertain", "screening_note",
        "title", "authors", "year", "venue", "publisher", "type", "doi", "arxiv",
        "metadata_source", "title_similarity", "metadata_status",
        "pages", "keywords", "abstract",
        "ft_av_mentions", "ft_driving_task_mentions", "ft_carla", "ft_sumo", "ft_highway_env", "ft_metadrive",
        "duplicate_of", "subfolder", "filename", "rel_path"]

def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t or ""))).strip()


rows = []
for sid in sorted(raw):
    r, m, i, s = raw[sid], meta[sid], ind[sid], scr[sid]
    rows.append({
        "study_id": sid, "decision": s["decision"], "reason_code": s["reason_code"], "domain": s["domain"],
        "domain_uncertain": s["domain_uncertain"], "screening_note": s["screening_note"],
        "title": clean(m.get("title") or r["filename_title"]), "authors": m.get("authors", ""), "year": m.get("year", ""),
        "venue": clean(m.get("venue", "")), "publisher": m.get("publisher", ""), "type": m.get("type", ""),
        "doi": m.get("doi", ""), "arxiv": m.get("arxiv", "") or r["arxiv_id"],
        "metadata_source": m["metadata_source"], "title_similarity": m["title_similarity"],
        "metadata_status": m["metadata_status"], "pages": r["pages"], "keywords": r["keywords"],
        "abstract": r["abstract"] or m.get("abstract_cr", ""),
        "ft_av_mentions": i["av"], "ft_driving_task_mentions": i["driving_task"], "ft_carla": i["carla"],
        "ft_sumo": i["sumo"], "ft_highway_env": i["highway_env"], "ft_metadrive": i["metadrive"],
        "duplicate_of": DUP_OF.get(sid, ("", ""))[0], "subfolder": r["subfolder"],
        "filename": r["filename"], "rel_path": r["rel_path"],
    })

# ---- consistency check checks ----
for sid, (keep, _) in DUP_OF.items():
    assert scr[sid]["decision"] == "Duplicate" and scr[keep]["decision"] != "Duplicate", sid
assert {s for s in scr if scr[s]["decision"] == "Duplicate"} == set(DUP_OF)

# ---- counts (all derived) ----
n_id = len(rows)
n_dup = sum(r["decision"] == "Duplicate" for r in rows)
screened = [r for r in rows if r["decision"] != "Duplicate"]
c = Counter(r["decision"] for r in screened)
bg_dom = Counter(r["domain"] for r in screened if r["decision"] == "Background")
exc = Counter(r["reason_code"] for r in screened if r["decision"] == "Exclude")
to_ft = c["Include"] + c["Unsure"]

# ---- CSV outputs ----
with open(A / "stageA_inventory.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
with open(A / "duplicate_log.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["removed_id", "kept_id", "relationship", "removed_title", "removed_doi", "kept_doi"])
    for sid, (keep, why) in sorted(DUP_OF.items()):
        w.writerow([sid, keep, why, meta[sid].get("title") or raw[sid]["filename_title"],
                    meta[sid].get("doi", ""), meta[keep].get("doi", "")])

random.seed(20261007)
sample = sorted(random.sample([r["study_id"] for r in screened], k=round(0.2 * len(screened))))
with open(A / "consistency_sample.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["study_id", "title", "second_screener_decision", "second_screener_reason", "notes"])
    for sid in sample:
        w.writerow([sid, next(r["title"] for r in rows if r["study_id"] == sid), "", "", ""])

# ---- PRISMA (Stage A block) ----
block = f"""# PRISMA 2020 counts — generated by scripts/04_build_inventory.py (do not edit by hand)
[STAGE_A]  # supplied seed corpus, inventoried 2026-10-07
records_identified_supplied_corpus = {n_id}
duplicates_removed = {n_dup}            # {', '.join(f'{k}->{v[0]}' for k, v in sorted(DUP_OF.items()))}
records_screened = {len(screened)}
records_excluded_title_abstract = {c['Background'] + c['Exclude']}
  excluded_background_pool_EC1 = {c['Background']}   # Safe-RL outside road vehicles; by domain: {dict(bg_dom)}
  excluded_other = {c['Exclude']}   # {dict(exc)}
reports_sought_for_full_text = {to_ft}   # Include={c['Include']} + Unsure={c['Unsure']}
reports_not_retrieved = 0   # all seed PDFs are on disk
# Full-text eligibility (Phase 3) and Stage B blocks are appended later.
"""
LOGS.mkdir(exist_ok=True)
(LOGS / "prisma_counts.txt").write_text(block)

# ---- workbook ----
wb = Workbook()
hdr_font, hdr_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
fills = {"Include": "D9F2D9", "Unsure": "FFF2CC", "Background": "E7EEF7", "Exclude": "F8D7DA", "Duplicate": "EDEDED"}


def sheet(ws, header, data, widths=None):
    ws.append(header)
    for cell in ws[1]:
        cell.font, cell.fill = hdr_font, hdr_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for row in data:
        ws.append([ILLEGAL_CHARACTERS_RE.sub('', v) if isinstance(v, str) else v for v in row])
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    for k, wdt in enumerate(widths or [], 1):
        ws.column_dimensions[get_column_letter(k)].width = wdt


ws = wb.active; ws.title = "Inventory"
widths = [8, 11, 8, 10, 6, 50, 60, 40, 6, 40, 20, 14, 28, 12, 15, 8, 9, 6, 30, 80, 6, 6, 6, 6, 6, 6, 8, 9, 50, 50]
sheet(ws, COLS, [[r[k] for k in COLS] for r in rows], widths)
for rr in range(2, ws.max_row + 1):
    ws.cell(rr, 2).fill = PatternFill("solid", fgColor=fills[ws.cell(rr, 2).value])

summary = [["Metric", "Count", "Note"],
           ["Records identified (supplied corpus)", n_id, "PDFs found in 'Articles for Review' (subfolder names imply 220)"],
           ["Duplicates removed", n_dup, "3 identical copies + 2 superseded conference versions"],
           ["Records screened", len(screened), ""],
           ["Include", c["Include"], "to full-text assessment"],
           ["Unsure", c["Unsure"], "to full-text assessment"],
           ["Background pool (EC1)", c["Background"], "Safe RL outside road vehicles; cited for foundations only"],
           ["Excluded (other reasons)", c["Exclude"], str(dict(exc))],
           ["Reports sought for full text", to_ft, ""]]
summary += [[f"Background: {k}", v, ""] for k, v in bg_dom.most_common()]
ws2 = wb.create_sheet("Summary"); sheet(ws2, summary[0], summary[1:], [40, 10, 70])

ws3 = wb.create_sheet("Duplicates")
sheet(ws3, ["removed_id", "kept_id", "relationship"], [[k, v[0], v[1]] for k, v in sorted(DUP_OF.items())], [12, 10, 100])

crit = [l.split("|")[1:3] for l in (LOGS / "protocol.md").read_text().splitlines()
        if l.startswith("| IC") or l.startswith("| EC")]
ws4 = wb.create_sheet("Criteria"); sheet(ws4, ["Code", "Criterion"], [[a.strip(), b.strip()] for a, b in crit], [8, 120])

ws5 = wb.create_sheet("Consistency sample")
sheet(ws5, ["study_id", "title", "second_screener_decision", "second_screener_reason", "notes"],
      [[s, next(r["title"] for r in rows if r["study_id"] == s), "", "", ""] for s in sample], [10, 80, 18, 18, 40])

wb.save(A / "stageA_inventory.xlsx")
print((LOGS / "prisma_counts.txt").read_text())
print("metadata:", Counter(r["metadata_status"] for r in rows), Counter(r["metadata_source"] for r in rows))
