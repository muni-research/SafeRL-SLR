#!/usr/bin/env python3
"""Phase 8: reconciliation worksheet for the screening consistency check.

Lists every record of the blind re-screening sample where the human decision and the first-pass decision differ on
forwarding to full text (Include/Unsure vs Exclude/Background), plus rows left blank, with title, abstract, both
decisions and the first-pass reason. The screener records an AGREED decision per row
(logs/consistency/screening_disagreements_reconcile.xlsx). The original re-screening decisions stay unchanged and
are the basis of the agreement statistic (scripts/30_consistency_kappa.py).
"""
import csv
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

csv.field_size_limit(sys.maxsize)
W = Path(__file__).resolve().parent.parent
D = W / "logs" / "consistency"
OUT = D / "screening_disagreements_reconcile.xlsx"
if OUT.exists():
    sys.exit(f"{OUT.name} already exists; it may contain agreed decisions. Move it away before regenerating.")

ws = load_workbook(D / "screening_sample_blind.xlsx")["rescreen"]
rows = {str(r[1]): r for r in ws.iter_rows(min_row=2, values_only=True)}
key = {r["record_id"]: r for r in csv.DictReader(open(D / "screening_sample_key.csv"))}
note = {}
for r in csv.DictReader(open(W / "stageA" / "stageA_inventory.csv")):
    note[r["study_id"]] = r.get("screening_note", "")
for r in csv.DictReader(open(W / "stageB" / "screening_decisions.csv")):
    note[r["study_id"]] = r.get("screening_note", "")
for r in csv.DictReader(open(W / "stageC" / "screening_decisions.csv")):
    note[r["cid"]] = r.get("note", "")
EC = {"EC1": "non-road domain", "EC2": "not RL", "EC3": "safety superficial (no role in method or evaluation)",
      "EC4": "non-research item", "EC6": "insufficient detail", "EC8": "thesis/dissertation",
      "EC9": "review or survey (not a primary study)", "EC10": "RL used to test AVs, not to drive",
      "EC11": "not in English"}
fwd = lambda d: d in ("Include", "Unsure")
out = []
for rid, k in key.items():
    r = rows[rid]
    sec = (r[6] or "").strip()
    if sec not in ("Include", "Unsure", "Exclude", "Background") or fwd(sec) != fwd(k["first_decision"]):
        code = k["first_code"] or ("EC1" if k["first_decision"] == "Background" else "")
        out.append([rid, r[2], r[5] or "", sec or "(blank)", k["first_decision"],
                    (code + ": " + EC.get(code, "")) if code else "", note.get(rid, ""), "", ""])
out.sort(key=lambda x: (x[5], x[0]))

wb = Workbook()
w = wb.active
w.title = "reconcile"
w.append(["record_id", "title", "abstract", "your decision", "first-pass decision", "first-pass reason",
          "first-pass note", "AGREED decision", "comment"])
for x in out:
    w.append(x)
for c, wd in zip("ABCDEFGHI", (10, 50, 80, 13, 13, 32, 30, 14, 30)):
    w.column_dimensions[c].width = wd
for row in w.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
for cell in w[1]:
    cell.font = Font(bold=True)
w.freeze_panes = "D2"
dv = DataValidation(type="list", formula1='"Include,Unsure,Exclude,Background"', allow_blank=True)
w.add_data_validation(dv)
dv.add(f"H2:H{len(out) + 1}")
ins = wb.create_sheet("how to use")
for line in [
    "Step 2 of the consistency check: resolve each disagreement (PRISMA: 'disagreements were resolved by discussion').",
    "For each row, read the first-pass reason and set the AGREED decision using the eligibility criteria (Table 4) and the protocol rules:",
    "  - a study qualifies only if (IC1) it uses RL, (IC2) safety is an explicit objective, constraint, mechanism, metric or evaluation "
    "criterion, and (IC3) road vehicles are a substantive application;",
    "  - reviews/surveys (EC9) and theses (EC8) are not primary studies, even when on topic; traffic-signal control in which RL does not "
    "control a vehicle is excluded;",
    "  - Safe RL method papers outside road vehicles go to the Background pool, not Include.",
    "Include or Unsure = goes to full-text assessment. Records that end up Include/Unsure after a first-pass exclusion will be retrieved, "
    "assessed in full text, and the review updated.",
    "Rows with '(blank)' were left empty in the first sheet; please give a decision.",
    f"Rows: {len(out)}. Your original decisions in screening_sample_blind.xlsx stay unchanged for the agreement statistic.",
]:
    ins.append([line])
ins.column_dimensions["A"].width = 150
wb.save(OUT)
print(f"{len(out)} rows -> {OUT.relative_to(W)}")
