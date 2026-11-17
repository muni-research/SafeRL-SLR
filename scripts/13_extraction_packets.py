"""Phase 4 step 1: build an extraction packet for every included study.

A packet condenses one full text for evidence extraction: header (affiliations), abstract, section
headings, the problem-formulation passage, the experimental-setup passage, the conclusion, and
sentences matching extraction cues (algorithms, safety terms, simulators, metrics, reproducibility).
'AUTO' lines list keywords found by regex; they are hints only, every value is verified by reading.
Output: extraction/packets/batchNN.txt (20 studies each), extraction/packet_index.csv
"""
import csv, re
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent.parent
OUT = W / "extraction" / "packets"
OUT.mkdir(parents=True, exist_ok=True)
BATCH = 20

AUTO = {
    "simulators": r"\bCARLA\b|\bSUMO\b|highway[- ]env|MetaDrive|SMARTS|\bFlow\b|TORCS|AirSim|LGSVL|SVL Simulator|CarSim|PreScan|Simulink|Gazebo|Webots|Unity|nuPlan|Waymax|CommonRoad|Safety[- ]Gym\w*|PyBullet|F1TENTH",
    "datasets": r"\bNGSIM\b|\bhighD\b|\binD\b|\brounD\b|\bexiD\b|INTERACTION dataset|Waymo Open|nuScenes|Argoverse",
    "algorithms": r"\b(?:Q-learning|DQN|DDQN|D3QN|Double DQN|Dueling|Rainbow|DRQN|PPO|TRPO|A2C|A3C|SAC|TD3|DDPG|REINFORCE|CPO|PCPO|FOCOPS|CUP|P3O|RCPO|WCSAC|PPO-Lag\w*|SAC-Lag\w*|MAPPO|MADDPG|IPPO|QMIX|BCQ|CQL|IQL|Decision Transformer|MBPO|Dreamer\w*|MCTS)\b",
    "safety": r"control barrier|\bHOCBF\b|\bCBF\b|\bCLF\b|Lyapunov|shield\w*|safety (?:filter|layer|critic|cost)|constrained Markov|\bCMDP\b|chance[- ]constrain\w*|\bCVaR\b|distributional|Hamilton[- ]Jacobi|reachab\w*|invariant set|model predictive|\bMPC\b|runtime (?:assurance|monitor)|simplex|formal verif\w*|temporal logic|\bLTL\b|\bSTL\b|action mask\w*|Lagrang\w*|\bRSS\b|adversarial|ensemble|Bayesian|dropout|uncertaint\w*",
    "metrics": r"collision rate|success rate|time[- ]to[- ]collision|\bTTC\b|\bPET\b|constraint violation|cost rate|jerk|comfort|travel time|throughput|intervention|headway|off-road|lane departure",
    "repro": r"github\.com/\S+|gitlab\.com/\S+|code (?:is|will be) (?:publicly )?available|random seeds?|\d+ (?:random )?seeds|hyper-?parameters?|GPU|NVIDIA \w+|training time|standard deviation|confidence interval|p-value|t-test",
    "real": r"real[- ]world (?:vehicle|experiment|test)|real vehicle|test track|proving ground|hardware[- ]in[- ]the[- ]loop|\bHIL\b|vehicle[- ]in[- ]the[- ]loop|scaled (?:car|vehicle)|F1TENTH|robot car|field test|public road|ISO 26262|SOTIF|ISO 21448|UL 4600",
}
CUE = {k: re.compile(v, 0 if k in ("algorithms",) else re.I) for k, v in AUTO.items()}
ENV = re.compile(r"simulator|simulation platform|simulation environment|experiments? (?:are|were|is|was) (?:conducted|carried out|performed)|we (?:compare|evaluate)|compared (?:with|to|against)|baselines?|test scenarios?|unseen|out-of-distribution|generali[sz]", re.I)
HEAD = re.compile(r"^\s*(?:[IVX]+\.|\d+(?:\.\d+)?\.?)\s+[A-Z][A-Za-z ,:&\-]{3,60}$")
SEC_FORM = re.compile(r"(?:PROBLEM (?:FORMULATION|STATEMENT|DEFINITION)|Problem (?:formulation|statement|definition)|PRELIMINAR\w*|Preliminar\w*|METHOD\w*|Method\w*|PROPOSED|Proposed)")
SEC_EXP = re.compile(r"(?:EXPERIMENT\w*|Experiment\w*|SIMULATION\w*|Simulation\w*|EVALUATION|Evaluation|IMPLEMENTATION|Implementation|CASE STUD\w*|Case stud\w*|RESULTS|Results)")


def body_text(path):
    doc = pymupdf.open(path)
    pages = [p.get_text() for p in doc]
    txt = "".join(pages)
    cut = max(txt.rfind("\nReferences\n"), txt.rfind("\nREFERENCES\n"), txt.rfind("\nReferences \n"), txt.rfind("\nBibliography\n"))
    return (txt[:cut] if cut > len(txt) * 0.4 else txt), pages[0] if pages else "", doc.page_count


def flat(s):
    s = re.sub(r"-\n(?=[a-z])", "", s)
    return re.sub(r"\s+", " ", s).strip()


def section_after(txt, rx, n):
    """Text following the first heading line matching rx (skipping the first 8% = front matter)."""
    start = int(len(txt) * 0.08)
    for m in re.finditer(r"\n([^\n]{0,80})\n", txt[start:]):
        line = m.group(1)
        if HEAD.match(line) and rx.search(line):
            p = start + m.end()
            return line.strip() + " :: " + flat(txt[p:p + n * 2])[:n]
    return ""


def sentences(txt):
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat(txt))


def main():
    A = {r["study_id"]: r for r in csv.DictReader(open(W / "stageA" / "stageA_inventory.csv"))}
    B = {r["study_id"]: r for r in csv.DictReader(open(W / "stageB" / "records_unique.csv"))}
    B.update({r["study_id"]: r for r in csv.DictReader(open(W / "stageC" / "records.csv"))})
    if (W / "stageE" / "records.csv").exists():
        B.update({r["study_id"]: r for r in csv.DictReader(open(W / "stageE" / "records.csv"))})
    links = {}
    for r in csv.DictReader(open(W / "fulltext" / "fulltext_decisions.csv")):
        if r["ft_decision"] == "Additional report":
            links.setdefault(r["linked_to"], []).append(r["study_id"])
    inc = [l.strip() for l in open(W / "fulltext" / "included_studies.txt") if l.strip()]
    # studies that already have packets keep their batch; newly included studies go to new batches
    old = []
    if (W / "extraction" / "packet_index.csv").exists():
        old = [r for r in csv.DictReader(open(W / "extraction" / "packet_index.csv")) if r["study_id"] in inc]
    have = {r["study_id"] for r in old}
    nb = max([int(r["batch"]) for r in old] or [0])
    inc = [sid for sid in inc if sid not in have]
    idx, batch = list(old), []
    for i, sid in enumerate(inc):
        if sid.startswith("A"):
            m = A[sid]; path = ROOT / m["rel_path"]
        else:
            m = B[sid]
            path = next((p for p in (W / "fulltext" / d / f"{sid}.pdf" for d in ("institutional", "open_access", "stageC_institutional", "stageC")) if p.exists()), None)
        txt, first, pages = body_text(path)
        sents = sentences(txt)
        out = [f"### {sid} | {m['year']} | {m['venue']} | {pages}p | linked: {';'.join(links.get(sid, [])) or '-'}",
               f"TITLE: {m['title']}", f"AUTHORS: {m['authors'][:200]}",
               f"HEADER: {flat(first)[:900]}", f"ABSTRACT: {flat(m.get('abstract') or '')[:1500]}"]
        heads = [l.strip() for l in txt.splitlines() if HEAD.match(l)][:30]
        out.append("HEADINGS: " + " | ".join(heads))
        for k in AUTO:
            found = sorted({(x if isinstance(x, str) else x[0]) for x in CUE[k].findall(txt)}, key=str.lower)
            found = sorted({f.lower(): f for f in found}.values(), key=str.lower)
            out.append(f"AUTO {k}: " + (", ".join(found[:25]) if found else "-"))
        out.append("FORMULATION: " + (section_after(txt, SEC_FORM, 2200) or "-"))
        out.append("EXPERIMENT: " + (section_after(txt, SEC_EXP, 2600) or "-"))
        env = [s for s in sents if 40 < len(s) < 450 and ENV.search(s)]
        out.append("ENV:\n  " + "\n  ".join(env[:14]))
        cues = []
        for s in sents:
            if 40 < len(s) < 450 and (CUE["repro"].search(s) or CUE["real"].search(s) or re.search(r"limitation|future work|does not|cannot guarantee|assum", s, re.I)):
                cues.append(s)
        out.append("CUES:\n  " + "\n  ".join(cues[:22]))
        mc = re.search(r"\n\s*(?:[IVX]+\.|\d+\.?)?\s*(?:CONCLUSIONS?|Conclusions?|CONCLUDING REMARKS|Concluding remarks|Conclusion and [Ff]uture [Ww]ork|CONCLUSION AND FUTURE WORK)[^\n]{0,30}\n(.{0,1400})", txt, re.S)
        out.append("CONCLUSION: " + (flat(mc.group(1)) if mc else "-"))
        batch.append("\n".join(out))
        idx.append({"study_id": sid, "batch": nb + 1, "pages": pages, "path": str(path.relative_to(ROOT))})
        if len(batch) == BATCH or i == len(inc) - 1:
            nb += 1
            (OUT / f"batch{nb:02d}.txt").write_text("\n\n".join(batch) + "\n")
            batch = []
    with open(W / "extraction" / "packet_index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(idx[0])); w.writeheader(); w.writerows(idx)
    print(f"{len(idx)} packets in {nb} batches ({len(inc)} new)")


if __name__ == "__main__":
    main()
