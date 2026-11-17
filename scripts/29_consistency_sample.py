#!/usr/bin/env python3
"""Phase 8: draw the samples for the human consistency checks reported in the manuscript.

1. Screening consistency: a stratified random 20% of all title/abstract-screened records (seed corpus A,
   database records B, citation-search records C; duplicates excluded), fixed seed. The human author
   re-screens the blind worksheet against the eligibility criteria without seeing the first decision.
2. Extraction consistency: a stratified random 10% of included studies; the human author codes six
   key fields from the full text without seeing the first coding.

Outputs in logs/consistency/:
  screening_sample_blind.xlsx   worksheet for the human screener (no first decisions)
  screening_sample_key.csv      first decisions (do not open before re-screening is finished)
  extraction_sample_blind.xlsx  worksheet for the second coder (codes and definitions on sheet 2)
  extraction_sample_key.csv     first coding (do not open before coding is finished)
Agreement and Cohen's kappa are computed by scripts/30_consistency_kappa.py.
"""
import csv
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

W = Path(__file__).resolve().parent.parent
OUT = W / "logs" / "consistency"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20261010
SCREEN_FRAC, EXTRACT_FRAC = 0.20, 0.10

# ---------------------------------------------------------------- screening frame
frame = []
for r in csv.DictReader(open(W / "stageA" / "stageA_inventory.csv")):
    if r["decision"] != "Duplicate":
        frame.append(dict(id=r["study_id"], stage="A", title=r["title"], year=r["year"], venue=r["venue"],
                          abstract=r["abstract"], decision=r["decision"], code=r["reason_code"]))
babs = {r["study_id"]: r for r in csv.DictReader(open(W / "stageB" / "records_unique.csv"))}
for r in csv.DictReader(open(W / "stageB" / "screening_decisions.csv")):
    if r["decision"] != "Duplicate":
        m = babs.get(r["study_id"], {})
        frame.append(dict(id=r["study_id"], stage="B", title=m.get("title", ""), year=m.get("year", ""),
                          venue=m.get("venue", ""), abstract=m.get("abstract", ""), decision=r["decision"],
                          code=r["reason_code"]))
cabs = {r["cid"]: r for r in csv.DictReader(open(W / "stageC" / "candidates.csv"))}
for r in csv.DictReader(open(W / "stageC" / "screening_decisions.csv")):
    if r["decision"] != "Duplicate":
        m = cabs.get(r["cid"], {})
        frame.append(dict(id=r["cid"], stage="C", title=r["title"], year=r["year"], venue=r["venue"],
                          abstract=m.get("abstract", ""), decision=r["decision"], code=r["code"]))

rng = random.Random(SEED)
sample = []
for st in "ABC":
    stratum = sorted((x for x in frame if x["stage"] == st), key=lambda x: x["id"])
    sample += rng.sample(stratum, round(SCREEN_FRAC * len(stratum)))
rng.shuffle(sample)                      # mix strata so the screener cannot infer the source

wb = Workbook()
ws = wb.active
ws.title = "rescreen"
head = ["n", "record_id", "title", "year", "venue", "abstract", "decision", "exclusion_code", "comment"]
ws.append(head)
for i, x in enumerate(sample, 1):
    ws.append([i, x["id"], x["title"], x["year"], x["venue"], (x["abstract"] or "")[:3000], "", "", ""])
for c, wdt in zip("ABCDEFGHI", (5, 10, 50, 6, 28, 90, 13, 13, 30)):
    ws.column_dimensions[c].width = wdt
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
for cell in ws[1]:
    cell.font = Font(bold=True)
ws.freeze_panes = "C2"
dv = DataValidation(type="list", formula1='"Include,Unsure,Exclude,Background"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"G2:G{len(sample) + 1}")
dv2 = DataValidation(type="list", formula1='"EC2,EC3,EC4,EC6,EC8,EC9,EC10,EC11,EC1"', allow_blank=True)
ws.add_data_validation(dv2); dv2.add(f"H2:H{len(sample) + 1}")
ins = wb.create_sheet("instructions")
for line in [
    "Re-screen each record from its title and abstract only, using Table 1 (eligibility criteria) and the protocol (supplementary S5).",
    "Decision: Include = eligible; Unsure = cannot decide from the abstract (would go to full text); Exclude = fails a criterion;",
    "Background = a Safe RL method study outside road vehicles (EC1 with a Safe RL method).",
    "For Exclude, give the exclusion code (EC1 non-road, EC2 not RL, EC3 safety superficial, EC4 non-research item, EC6 insufficient detail,",
    "EC8 thesis, EC9 review/survey, EC10 RL used to test AVs, EC11 not English).",
    "Do not look at screening_sample_key.csv or any project decision file until every row is complete.",
    f"Sample: stratified random {int(SCREEN_FRAC * 100)}% of {len(frame)} screened records (seed {SEED}); {len(sample)} records.",
]:
    ins.append([line])
ins.column_dimensions["A"].width = 140
wb.save(OUT / "screening_sample_blind.xlsx")
with open(OUT / "screening_sample_key.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["n", "record_id", "stage", "first_decision", "first_code"])
    for i, x in enumerate(sample, 1):
        w.writerow([i, x["id"], x["stage"], x["decision"], x["code"]])

# ---------------------------------------------------------------- extraction sample
FIELDS = {
    "safety_level": "L0 L1 L2 L3 L4 L5",
    "mech_primary": "A B C D E F G H I J K L M N O P Q R S T U V W X",
    "rl_output": "ACT DEC PARAM TRAJ RES",
    "safety_integration": "NONE FILTER CORRECT EMBED MASK",
    "validation_tier": "SIM-LOW SIM-HIFI SIM-DATA HIL SCALED CLOSED ROAD DEPLOY",
    "algorithm_family": "value-based on-policy off-policy-AC constrained offline model-based generic-AC other",
}
R = list(csv.DictReader(open(W / "extraction" / "evidence_db.csv")))
pk = {r["study_id"]: r["path"] for r in csv.DictReader(open(W / "extraction" / "packet_index.csv"))}
rng = random.Random(SEED + 1)
ex = []
for st in "ABC":
    stratum = sorted((r for r in R if r["study_id"][0] == st), key=lambda r: r["study_id"])
    ex += rng.sample(stratum, max(1, round(EXTRACT_FRAC * len(stratum))))
ex.sort(key=lambda r: r["study_id"])

wb = Workbook()
ws = wb.active
ws.title = "second_coding"
ws.append(["study_id", "title", "year", "pdf"] + list(FIELDS) + ["comment"])
for r in ex:
    ws.append([r["study_id"], r["title"], r["year"], pk.get(r["study_id"], "")] + [""] * len(FIELDS) + [""])
for i, (fld, codes) in enumerate(FIELDS.items()):
    col = chr(ord("E") + i)
    dv = DataValidation(type="list", formula1='"' + ",".join(codes.split()) + '"', allow_blank=True)
    ws.add_data_validation(dv); dv.add(f"{col}2:{col}{len(ex) + 1}")
    ws.column_dimensions[col].width = 16
ws.column_dimensions["B"].width = 60; ws.column_dimensions["D"].width = 45
for cell in ws[1]:
    cell.font = Font(bold=True)
ws.freeze_panes = "B2"
cb = wb.create_sheet("codes")
for line in [
    "Code each study from its full text (path in column D, relative to the project root) using the codebook (supplementary S3, extraction/codebook.md).",
    "safety_level (review-derived): L0 safety mentioned, not evaluated; L1 empirical evaluation; L2 constraint-based (expected-cost or penalty constraints);",
    "  L3 run-time enforcement (shield, filter, mask, fallback, embedded constrained optimiser acting on every executed action); L4 formal/provable property;",
    "  L5 real-vehicle evidence with a reported safety analysis. Training-time-only interventions give L1.",
    "mech_primary: A reward design, B constrained RL (CMDP), C safety critic, D shielding/masking, E safety filter/layer, F CBF, G Lyapunov/CLF,",
    "  H CBF-CLF-QP/optimisation layer, I MPC-RL hybrid, J reachability, K robust/adversarial, L risk-sensitive, M distributionally robust, N uncertainty-aware,",
    "  O multi-agent safe RL, P offline safe RL, Q model-based safe RL, R hierarchical safe RL, S runtime assurance/fallback, T formal verification,",
    "  U sim-to-real, V human-aware/in-the-loop, W rule-based intervention, X foundation-model-assisted.",
    "rl_output: ACT control action, DEC high-level decision, PARAM controller parameters, TRAJ trajectory/reference, RES residual on a base controller.",
    "safety_integration: NONE, FILTER (action projected/filtered), CORRECT (overridden/switched), EMBED (RL inside an optimisation layer), MASK (unsafe actions masked).",
    "validation_tier: SIM-LOW, SIM-HIFI (CARLA/LGSVL-class), SIM-DATA (replayed real data), HIL, SCALED, CLOSED (full-size closed course), ROAD, DEPLOY.",
    "algorithm_family: value-based, on-policy (PPO/TRPO/A2C), off-policy-AC (DDPG/TD3/SAC), constrained (CPO/Lagrangian), offline, model-based, generic-AC, other.",
    "Do not look at extraction_sample_key.csv or extraction/evidence_db.* until every row is complete.",
    f"Sample: stratified random {int(EXTRACT_FRAC * 100)}% of {len(R)} included studies (seed {SEED + 1}); {len(ex)} studies.",
]:
    cb.append([line])
cb.column_dimensions["A"].width = 150
wb.save(OUT / "extraction_sample_blind.xlsx")


def family(r):
    """first-coder algorithm family, using the mapping in scripts/15_stats.py"""
    src = (W / "scripts" / "15_stats.py").read_text()
    start = src.index("VB, ONP"); end = src.index("\n}\n", src.index("ALG = {")) + 3
    ns = {}; exec(src[start:end], ns)
    lab = {ns["VB"]: "value-based", ns["ONP"]: "on-policy", ns["OFFP"]: "off-policy-AC", ns["CON"]: "constrained",
           ns["OFFL"]: "offline", ns["MB"]: "model-based", ns["GEN"]: "generic-AC", ns["OTH"]: "other"}
    fams = sorted({lab[ns["ALG"][a.strip()][1]] for a in r["algorithm"].split(";") if a.strip()})
    return ";".join(fams)


with open(OUT / "extraction_sample_key.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["study_id"] + list(FIELDS))
    for r in ex:
        w.writerow([r["study_id"]] + [r[k] for k in list(FIELDS)[:-1]] + [family(r)])

print(f"screening frame {len(frame)} -> sample {len(sample)} "
      f"({', '.join(f'{s}: {sum(1 for x in sample if x["stage"] == s)}' for s in 'ABC')}); "
      f"extraction sample {len(ex)} of {len(R)}")
