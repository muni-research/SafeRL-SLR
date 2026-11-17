#!/usr/bin/env python3
"""Phase 8: full-text eligibility dossiers for retrieved citation-search candidates (same layout and
evidence patterns as scripts/11_fulltext_dossiers.py). Output: stageC/dossiers/batchNN.txt (25 each)."""
import csv, importlib.util, re
from pathlib import Path

W = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("d11", W / "scripts" / "11_fulltext_dossiers.py")
d11 = importlib.util.module_from_spec(spec); spec.loader.exec_module(d11)
OUT = W / "stageC" / "dossiers"; OUT.mkdir(exist_ok=True)
cands = {r["cid"]: r for r in csv.DictReader(open(W / "stageC" / "candidates.csv"))}
done = set()
for f in (W / "stageC" / "ft_decisions_raw").glob("batch*.txt") if (W / "stageC" / "ft_decisions_raw").exists() else []:
    done |= {l.split()[0] for l in open(f) if l.strip() and not l.startswith("#")}
items = []
for sub in ("stageC_institutional", "stageC"):
    for p in sorted((W / "fulltext" / sub).glob("C*.pdf")):
        if p.stem not in done and p.stem not in {i[0] for i in items}:
            items.append((p.stem, p))
items.sort()
n = max([int(p.stem[5:]) for p in OUT.glob("batch*.txt")] or [0])
batch = []
for cid, path in items:
    c = cands[cid]
    try:
        txt, pages = d11.body_text(path)
    except Exception:
        txt, pages = "", 0
    sents = d11.sentences(txt)
    heads = [l.strip() for l in txt.splitlines() if d11.HEAD.match(l)][:25]
    m = re.search(r"\n\s*(?:[IVX]+\.|\d+\.?)?\s*(?:CONCLUSIONS?|Conclusions?|CONCLUDING REMARKS|Concluding remarks)\s*\n(.{0,700})", txt, re.S)
    concl = re.sub(r"\s+", " ", m.group(1)) if m else ""
    k = {key: d11.counts(txt, v) for key, v in d11.PAT.items()}
    lines = [f"### {cid} {c['year']} | {c['venue'][:60]} | {pages}p | counts V{k['VEHICLE']} RL{k['RL']} S{k['SAFETY']} X{k['EXPERIMENT']}",
             f"TITLE: {c['title']}", f"ABSTRACT: {c['abstract'][:900]}", f"HEADINGS: {' | '.join(heads)[:600]}"]
    for key, kk in (("VEHICLE", 2), ("SAFETY", 4), ("RL", 2), ("EXPERIMENT", 3)):
        for s in d11.evidence(sents, d11.PAT[key], kk):
            lines.append(f"  [{key[:3]}] {s[:330]}")
    if concl:
        lines.append(f"CONCL: {concl[:450]}")
    batch.append("\n".join(lines))
    if len(batch) == 25:
        n += 1; (OUT / f"batch{n:02d}.txt").write_text("\n\n".join(batch)); batch = []
if batch:
    n += 1; (OUT / f"batch{n:02d}.txt").write_text("\n\n".join(batch))
print(len(items), "new dossiers; last batch", n)
