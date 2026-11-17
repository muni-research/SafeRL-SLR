#!/usr/bin/env python3
"""Phase 8: agreement and Cohen's kappa for the human consistency checks (samples from scripts/29).

Reads the completed worksheets in logs/consistency/ and their keys, and writes
logs/consistency/consistency_results.txt. Screening agreement is reported for
  (a) the forwarding decision that matters for the review: to full text (Include/Unsure) vs not (Exclude/Background);
  (b) the four categories Include / Unsure / Exclude / Background.
Extraction agreement is reported per field (a multi-valued first coding counts as agreement when the
second code is one of its values). Rows left blank are reported and skipped.
"""
import csv
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

W = Path(__file__).resolve().parent.parent
D = W / "logs" / "consistency"


def kappa(pairs):
    n = len(pairs)
    if not n:
        return float("nan"), float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


out = []
ws = load_workbook(D / "screening_sample_blind.xlsx")["rescreen"]
VALID = {"Include", "Unsure", "Exclude", "Background"}
second = {str(r[1]): (r[6] or "").strip() for r in ws.iter_rows(min_row=2, values_only=True)}
invalid = sorted(k for k, v in second.items() if v and v not in VALID)
second = {k: v for k, v in second.items() if v in VALID}       # blanks and invalid entries are skipped and listed
key = list(csv.DictReader(open(D / "screening_sample_key.csv")))
done = [k for k in key if second.get(k["record_id"])]
fwd = lambda d: "full text" if d in ("Include", "Unsure") else "not forwarded"
for label, f in (("forwarded to full text vs not", fwd), ("four categories", lambda d: d)):
    po, k = kappa([(f(x["first_decision"]), f(second[x["record_id"]])) for x in done])
    out.append(f"Screening ({label}): n = {len(done)} of {len(key)}; agreement {po:.1%}; Cohen's kappa {k:.2f}")
for st in "ABC":
    sub = [x for x in done if x["stage"] == st]
    po, k = kappa([(fwd(x["first_decision"]), fwd(second[x["record_id"]])) for x in sub])
    out.append(f"  stage {st}: n = {len(sub)}; agreement {po:.1%}; kappa {k:.2f}")
out.append(f"  skipped: {len(key) - len(done)} rows (blank or invalid; invalid: {', '.join(invalid) or 'none'})")
dis = [x for x in done if fwd(x["first_decision"]) != fwd(second[x["record_id"]])]
out.append(f"  forwarding disagreements: {', '.join(x['record_id'] for x in dis) or 'none'}")
po_f, k_f = kappa([(fwd(x["first_decision"]), fwd(second[x["record_id"]])) for x in done])
po_4, k_4 = kappa([(x["first_decision"], second[x["record_id"]]) for x in done])
RES = {"screen_sampled": len(key), "screen_decided": len(done), "screen_frame": sum(1 for f, c in ((W / "stageA" / "stageA_inventory.csv", "decision"), (W / "stageB" / "screening_decisions.csv", "decision"), (W / "stageC" / "screening_decisions.csv", "decision")) for r in csv.DictReader(open(f)) if r[c] != "Duplicate"),
       "screen_agree_fwd_pct": round(100 * po_f, 1), "screen_kappa_fwd": round(k_f, 2),
       "screen_agree_4_pct": round(100 * po_4, 1), "screen_kappa_4": round(k_4, 2),
       "screen_disagreements": len(dis), "screen_undecided": len(key) - len(done)}
# reconciliation (logs/consistency/screening_disagreements_reconcile.xlsx, AGREED decision column)
rec_path = D / "screening_disagreements_reconcile.xlsx"
if rec_path.exists():
    rr = list(load_workbook(rec_path)["reconcile"].iter_rows(min_row=2, values_only=True))
    agreed = [(r[0], r[4], (r[7] or "").strip()) for r in rr]
    filled = [a for a in agreed if a[2]]
    changed = [a for a in filled if fwd(a[1]) != fwd(a[2])]
    upheld_excl = sum(1 for a in filled if fwd(a[1]) == fwd(a[2]) == "not forwarded")
    upheld_fwd = sum(1 for a in filled if fwd(a[1]) == fwd(a[2]) == "full text")
    RES.update({"rec_rows": len(agreed), "rec_filled": len(filled), "rec_changed": len(changed),
                "rec_upheld_exclusions": upheld_excl, "rec_upheld_forwarded": upheld_fwd})
    out.append(f"Reconciliation: {len(filled)} of {len(agreed)} rows agreed; first-pass exclusions upheld {upheld_excl}, "
               f"first-pass forwarding upheld {upheld_fwd}; records whose forwarding status changed: {len(changed)} "
               f"({', '.join(a[0] for a in changed) or 'none'})")

ws = load_workbook(D / "extraction_sample_blind.xlsx")["second_coding"]
rows = list(ws.iter_rows(values_only=True))
head = list(rows[0])
sec = {str(r[0]): dict(zip(head, r)) for r in rows[1:]}
key = list(csv.DictReader(open(D / "extraction_sample_key.csv")))
for fld in head[4:-1]:
    pairs = []
    for x in key:
        v = (sec.get(x["study_id"], {}).get(fld) or "").strip()
        if not v:
            continue
        first = [c.strip() for c in x[fld].split(";")]
        pairs.append((v if v in first else first[0], v))
    po, k = kappa(pairs)
    out.append(f"Extraction {fld}: n = {len(pairs)} of {len(key)}; agreement {po:.1%}; Cohen's kappa {k:.2f}")

(D / "consistency_results.txt").write_text("\n".join(out) + "\n")
import json
json.dump(RES, open(D / "consistency_results.json", "w"), indent=1)
print("\n".join(out))
