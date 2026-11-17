"""Phase 3 step 1: build full-text eligibility dossiers for every retrieved report.

A dossier condenses one full text for the reviewer: bibliographic header, abstract, section headings,
evidence sentences for each eligibility criterion (vehicle/domain, RL, safety mechanism, experiments),
and the opening of the conclusion. Decisions are made by reading the dossier (and the PDF when the
dossier is ambiguous); keyword counts are only an aid.
Output: fulltext/dossiers/batchNN.txt (25 reports each), fulltext/dossier_index.csv
"""
import csv, re
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent.parent
OUT = W / "fulltext" / "dossiers"
OUT.mkdir(parents=True, exist_ok=True)

PAT = {
    "VEHICLE": r"autonomous (?:vehicle|driving|car)|self-driving|automated (?:vehicle|driving)|connected (?:and )?(?:automated|autonomous)|\bCAVs?\b|lane[- ]chang|lane[- ]keep|car[- ]following|platoon|on-ramp|merging|intersection|adaptive cruise|racing|parking|highway|pedestrian|ego[- ]vehicle|bicycle model",
    "RL": r"\b(?:PPO|TRPO|SAC|TD3|DDPG|DQN|D3QN|DDQN|A2C|A3C|MAPPO|MADDPG|QMIX|CPO|PPO-Lag|SAC-Lag|Q-learning|actor[- ]critic|policy gradient|Lagrang\w*|primal[- ]dual|model-based RL|offline RL|multi-agent)\b",
    "SAFETY": r"control barrier|CBF|CLF|Lyapunov|shield|safety (?:filter|layer|constraint|critic|cost|set|guarantee|certificate)|constrained Markov|CMDP|chance[- ]constrain|CVaR|risk[- ](?:sensitive|aware)|reachab|invarian|model predictive|MPC|runtime|formal verif|action mask|projection|safe set|time[- ]to[- ]collision|TTC|RSS",
    "EXPERIMENT": r"\bCARLA\b|\bSUMO\b|highway[- ]env|MetaDrive|Safety[- ]Gym|\bGym\b|Prescan|CarSim|MATLAB|Simulink|Webots|AirSim|Apollo|LGSVL|NGSIM|highD|inD|real[- ]vehicle|real[- ]world (?:test|experiment)|hardware[- ]in[- ]the[- ]loop|\bHIL\b|test track|field test|scaled (?:car|vehicle)|F1TENTH|DonkeyCar|Jackal",
}
HEAD = re.compile(r"^\s*(?:[IVX]+\.|\d+(?:\.\d+)?\.?)\s+[A-Z][A-Za-z ,:&\-]{3,60}$")


def body_text(path):
    doc = pymupdf.open(path)
    txt = "".join(p.get_text() for p in doc)
    cut = max(txt.rfind("\nReferences\n"), txt.rfind("\nREFERENCES\n"), txt.rfind("\nReferences \n"))
    return (txt[:cut] if cut > len(txt) * 0.4 else txt), doc.page_count


def sentences(txt):
    flat = re.sub(r"-\n(?=[a-z])", "", txt)
    flat = re.sub(r"\s+", " ", flat)
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat)


def evidence(sents, pat, k):
    rx = re.compile(pat)
    scored = sorted(((len(rx.findall(s)), i, s) for i, s in enumerate(sents) if 40 < len(s) < 400 and rx.search(s)),
                    key=lambda x: (-x[0], x[1]))[:k]
    return [s for _, _, s in sorted(scored, key=lambda x: x[1])]


def counts(txt, pat):
    return len(re.findall(pat, txt))


def main():
    A = {r["study_id"]: r for r in csv.DictReader(open(W / "stageA" / "stageA_inventory.csv"))}
    Bu = {r["study_id"]: r for r in csv.DictReader(open(W / "stageB" / "records_unique.csv"))}
    items = []
    for sid, r in sorted(A.items()):
        if r["decision"] in ("Include", "Unsure"):
            items.append((sid, r["decision"], r["title"], r["year"], r["venue"], ROOT / r["rel_path"], r["abstract"]))
    for r in csv.DictReader(open(W / "fulltext" / "retrieval_status.csv")):
        if r["status"] == "NOT RETRIEVED":
            continue
        sid = r["study_id"]
        p = W / "fulltext" / ("institutional" if r["status"].startswith("institutional") else "open_access") / f"{sid}.pdf"
        if not p.exists():
            continue
        u = Bu[sid]
        items.append((sid, r["decision"], u["title"], u["year"], u["venue"], p, u["abstract"]))

    # reports already assessed keep their existing dossier batch; new reports go to new batches
    decided = set()
    if (W / "fulltext" / "fulltext_decisions.csv").exists():
        decided = {r["study_id"] for r in csv.DictReader(open(W / "fulltext" / "fulltext_decisions.csv"))}
    n = max([int(p.stem[5:]) for p in OUT.glob("batch*.txt")] or [0]) if decided else 0
    first_new = n + 1
    idx, batch = [], []
    for sid, dec, title, year, venue, path, abstract in items:
        try:
            txt, pages = body_text(path)
        except Exception as e:
            txt, pages = "", 0
        sents = sentences(txt)
        heads = [l.strip() for l in txt.splitlines() if HEAD.match(l)][:25]
        concl = ""
        m = re.search(r"\n\s*(?:[IVX]+\.|\d+\.?)?\s*(?:CONCLUSIONS?|Conclusions?|CONCLUDING REMARKS|Concluding remarks)\s*\n(.{0,700})", txt, re.S)
        if m:
            concl = re.sub(r"\s+", " ", m.group(1))
        c = {k: counts(txt, v) for k, v in PAT.items()}
        lines = [f"### {sid} [{dec}] {year} | {venue[:60]} | {pages}p | counts V{c['VEHICLE']} RL{c['RL']} S{c['SAFETY']} X{c['EXPERIMENT']}",
                 f"TITLE: {title}",
                 f"ABSTRACT: {re.sub(chr(10), ' ', (abstract or '')[:900])}",
                 f"HEADINGS: {' | '.join(heads)[:600]}"]
        for k, kk in (("VEHICLE", 2), ("SAFETY", 4), ("RL", 2), ("EXPERIMENT", 3)):
            for s in evidence(sents, PAT[k], kk):
                lines.append(f"  [{k[:3]}] {s[:330]}")
        if concl:
            lines.append(f"CONCL: {concl[:450]}")
        idx.append({"study_id": sid, "ta_decision": dec, "pages": pages, "path": str(path.relative_to(ROOT)), **c})
        if sid in decided:
            continue
        batch.append("\n".join(lines))
        if len(batch) == 25:
            n += 1; (OUT / f"batch{n:02d}.txt").write_text("\n\n".join(batch)); batch = []
    if batch:
        n += 1; (OUT / f"batch{n:02d}.txt").write_text("\n\n".join(batch))
    with open(W / "fulltext" / "dossier_index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(idx[0])); w.writeheader(); w.writerows(idx)
    print(len(idx), "reports indexed;", len(idx) - len(decided & {i["study_id"] for i in idx}),
          f"new dossiers in batches {first_new:02d}-{n:02d}")


if __name__ == "__main__":
    main()
