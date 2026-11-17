"""Reviewer aid: print sentences of an included study's full text that match a regex.
Usage: python3 scripts/13b_lookup.py <StudyID> '<regex>' [max]"""
import csv, re, sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[2]; W = Path(__file__).resolve().parent.parent
idx = {r["study_id"]: r for r in csv.DictReader(open(W / "extraction" / "packet_index.csv"))}
idx.update({r["study_id"]: r for r in csv.DictReader(open(W / "fulltext" / "dossier_index.csv")) if r["study_id"] not in idx})
for sub in ("stageC_institutional", "stageC"):          # citation-search reports not yet in an index
    for f in (W / "fulltext" / sub).glob("C*.pdf"):
        idx.setdefault(f.stem, {"path": str(f.relative_to(ROOT))})
sid, pat = sys.argv[1], sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 8
txt = "".join(p.get_text() for p in pymupdf.open(ROOT / idx[sid]["path"]))
flat = re.sub(r"\s+", " ", re.sub(r"-\n(?=[a-z])", "", txt))
hits = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat) if re.search(pat, s, re.I)]
print(f"== {sid}: {len(hits)} hits")
for s in hits[:k]: print(" -", s[:400])
