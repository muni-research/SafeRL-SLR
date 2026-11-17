"""Stage B step 3: compile per-batch reviewer decisions into stageB/screening_decisions.csv.

Each stageB/screening_decisions_raw/batchN.txt lists, for one batch of records shown in
stageB/screening_batches/batchN.txt, every record whose decision differs from the batch default
(stated in the file header). Every record in the batch was read; the default is only a typing aid.
Codes: I include, U unsure, R review (EC9), B background (EC1), E1..E11 exclusion codes, D:<id> duplicate.
"""
import csv, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent.parent / "stageB"
NAMES = {"I": "Include", "U": "Unsure", "R": "Exclude", "B": "Background"}
REASON = {"R": "EC9", "B": "EC1", "E1": "EC1", "E2": "EC2", "E3": "EC3", "E4": "EC4", "E8": "EC8",
          "E10": "EC10", "E11": "EC11"}

rows, seen = [], set()
for bf in sorted((B / "screening_batches").glob("batch*.txt"), key=lambda p: int(p.stem[5:])):
    ids = [l.split("|", 1)[0] for l in bf.read_text().splitlines() if l.strip()]
    df = B / "screening_decisions_raw" / bf.name
    txt = df.read_text()
    default = re.search(r"default for unlisted IDs in this batch: (\S+)", txt).group(1)
    dec = {}
    for line in txt.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        assert parts[0] in ids, f"{parts[0]} not in {bf.name}"
        assert parts[0] not in dec, f"duplicate decision {parts[0]}"
        dec[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
    for sid in ids:
        code, note = dec.get(sid, (default, ""))
        if code.startswith("D:"):
            d, r = "Duplicate", "EC5:" + code[2:]
        elif code in NAMES:
            d, r = NAMES[code], REASON.get(code, "")
        else:
            d, r = "Exclude", REASON[code]
        rows.append({"study_id": sid, "decision": d, "reason_code": r, "screening_note": note,
                     "batch": bf.stem, "screened_on": "2026-10-07", "stage": "title/abstract"})
        seen.add(sid)

uniq = [r for r in csv.DictReader(open(B / "records_unique.csv")) if not r["in_stageA"]]
missing = {u["study_id"] for u in uniq} - seen
assert not missing, f"unscreened: {sorted(missing)[:10]}"
with open(B / "screening_decisions.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "records screened")
print(Counter(r["decision"] for r in rows))
print(Counter(r["reason_code"] for r in rows if r["decision"] == "Exclude"))
