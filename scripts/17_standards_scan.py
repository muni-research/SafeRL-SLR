#!/usr/bin/env python3
"""Synthesis check (G15): list included studies whose full text (before the reference list) mentions
automotive safety standards, functional safety, safety cases or certification. Usage: python3 scripts/17_standards_scan.py > analysis/standards_scan.txt"""
import csv,re
from pathlib import Path
import pymupdf
W=Path(__file__).resolve().parent.parent; ROOT=W.parent
P=re.compile(r"ISO ?26262|SOTIF|21448|UL ?4600|ISO ?34502|functional safety|safety case|certif",re.I)
for r in csv.DictReader(open(W/"extraction"/"packet_index.csv")):
    t="".join(p.get_text() for p in pymupdf.open(ROOT/r["path"]))
    flat=re.sub(r"\s+"," ",t); body=re.split(r"\b(References|REFERENCES)\b",flat)[0]
    hits=[s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])",body) if P.search(s)]
    if hits: print(r["study_id"],len(hits),"|"," || ".join(h[:200] for h in hits[:3]))
