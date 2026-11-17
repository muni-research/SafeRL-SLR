#!/usr/bin/env python3
"""RQ10 screening aid: scan each included study's full text (excluding the reference list) for
explainability/trust vocabulary and write extraction/xai_scan.csv with hit counts and the strongest
sentences. The scan only proposes candidates; the `explainability` code itself is assigned by the
reviewer in extraction/raw/xai_codes.txt (codebook v1.5)."""
import csv
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent.parent
PAT = re.compile(r"explainab|interpretab|explanation|saliency|attention (map|weight|visuali)|transparen|"
                 r"human[- ]understandable|decision rationale|\btrust(worth)?", re.I)
STRONG = re.compile(r"explainab|interpretab|saliency|attention (map|weight|visuali)|rationale", re.I)

rows = []
for r in csv.DictReader(open(W / "extraction" / "packet_index.csv")):
    txt = "".join(p.get_text() for p in pymupdf.open(ROOT / r["path"]))
    flat = re.sub(r"\s+", " ", re.sub(r"-\n(?=[a-z])", "", txt))
    body = re.split(r"\b(References|REFERENCES|Bibliography)\b", flat)[0]
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body)
    hits = [s for s in sents if PAT.search(s)]
    strong = [s for s in hits if STRONG.search(s)]
    rows.append({"study_id": r["study_id"], "hits": len(hits), "strong_hits": len(strong),
                 "examples": " || ".join(s[:220] for s in (strong or hits)[:3])})
rows.sort(key=lambda x: (-x["strong_hits"], -x["hits"]))
with open(W / "extraction" / "xai_scan.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["study_id", "hits", "strong_hits", "examples"])
    w.writeheader()
    w.writerows(rows)
print(sum(1 for x in rows if x["strong_hits"]), "studies with strong hits;", sum(1 for x in rows if x["hits"]), "with any hit")
