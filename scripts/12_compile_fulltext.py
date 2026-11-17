"""Phase 3: compile full-text eligibility decisions (fulltext/ft_decisions_raw/batch*.txt) into
fulltext/fulltext_decisions.csv and the final included-study list, and check completeness against
the retrieved reports (dossier_index.csv).
Codes: FI include, FX:<EC> exclude with reason, FB background pool (EC1), FD:<id> additional report of an
included study (counted as a report, not a separate study).
"""
import csv, glob, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FT = Path(__file__).resolve().parent.parent / "fulltext"
idx = {r["study_id"]: r for r in csv.DictReader(open(FT / "dossier_index.csv"))}
# citation-search reports (Phase 8): every retrieved stageC PDF, T/A decision Unsure
SC = Path(__file__).resolve().parent.parent / "stageC"
for sub in ("stageC", "stageC_institutional"):
    for p in (FT / sub).glob("C*.pdf"):
        idx[p.stem] = {"study_id": p.stem, "ta_decision": "Unsure"}
# second update search (stageE, 2026-11-13): every retrieved report, with its title/abstract decision
SE = Path(__file__).resolve().parent.parent / "stageE"
if (SE / "screening_decisions.csv").exists():
    _ta = {r["eid"]: r["decision"] for r in csv.DictReader(open(SE / "screening_decisions.csv"))}
    for p in (SE / "fulltext").glob("E*.pdf"):
        idx[p.stem] = {"study_id": p.stem, "ta_decision": _ta[p.stem]}
rows = {}
files = sorted(glob.glob(str(FT / "ft_decisions_raw" / "batch*.txt"))) + sorted(glob.glob(str(SC / "ft_decisions_raw" / "batch*.txt"))) + sorted(glob.glob(str(SE / "ft_decisions_raw" / "batch*.txt")))
for f in files:
    for line in open(f):
        if not line.strip() or line.startswith("#"):
            continue
        sid, code, note = (line.rstrip("\n").split(" ", 2) + [""])[:3]
        assert sid not in rows, f"duplicate decision for {sid}"
        assert sid in idx, f"{sid} not a retrieved report"
        kind, _, arg = code.partition(":")
        dec = {"FI": "Include", "FX": "Exclude", "FB": "Background", "FD": "Additional report"}[kind]
        reason = arg if kind == "FX" else ("EC1" if kind == "FB" else ("EC5" if kind == "FD" else ""))
        rows[sid] = {"study_id": sid, "ta_decision": idx[sid]["ta_decision"], "ft_decision": dec,
                     "reason_code": reason, "linked_to": arg if kind == "FD" else "", "note": note,
                     "assessed_on": {"C": "2026-10-10", "E": "2026-11-13"}.get(sid[0], "2026-10-07")}
missing = sorted(set(idx) - set(rows))
for r in rows.values():
    if r["linked_to"]:
        assert rows.get(r["linked_to"], {}).get("ft_decision") == "Include" or r["linked_to"] not in rows, r
with open(FT / "fulltext_decisions.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(next(iter(rows.values())))); w.writeheader()
    w.writerows(sorted(rows.values(), key=lambda r: r["study_id"]))
inc = sorted(s for s, r in rows.items() if r["ft_decision"] == "Include")
(FT / "included_studies.txt").write_text("\n".join(inc) + "\n")
c = Counter(r["ft_decision"] for r in rows.values())
print(f"assessed {len(rows)} of {len(idx)} retrieved reports; missing: {missing}")
print(dict(c))
print("exclusion reasons:", dict(Counter(r["reason_code"] for r in rows.values() if r["ft_decision"] in ("Exclude", "Background"))))
print("by TA decision:", dict(Counter((r["ta_decision"], r["ft_decision"]) for r in rows.values())))
