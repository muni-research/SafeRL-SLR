#!/usr/bin/env python3
"""Phase 5 quantitative synthesis (CLAUDE.md §20-21, §26-28).

Reads extraction/evidence_db.csv only and writes:
  analysis/tables/*.csv        one table per statistic (counts, % of studies, study IDs)
  analysis/stats_summary.md    readable summary of every number used in the manuscript
  analysis/stats.json          the same numbers, machine readable
  manuscript/stats_macros.tex  \\newcommand macros so the manuscript never contains typed numbers

Percentages are of the number of included studies with an extraction record (N), unless a
table states another denominator. Multi-valued fields count a study once per distinct value,
so their percentages can sum to more than 100.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
OUT = W / "analysis"
TAB = OUT / "tables"
TAB.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------------------------
# Label dictionaries (from extraction/codebook.md)
MECH = {
    "A": "Safety-aware reward design", "B": "Constrained RL (CMDP)", "C": "Safety critic",
    "D": "Action shielding / masking", "E": "Safety filter / layer", "F": "Control barrier function",
    "G": "Lyapunov / CLF", "H": "CBF-CLF-QP / optimisation layer", "I": "MPC-RL hybrid",
    "J": "Reachability / invariant sets", "K": "Robust / adversarial RL", "L": "Risk-sensitive RL",
    "M": "Distributionally robust RL", "N": "Uncertainty-aware RL", "O": "Multi-agent safe RL",
    "P": "Offline safe RL", "Q": "Model-based safe RL", "R": "Hierarchical safe RL",
    "S": "Runtime assurance / fallback", "T": "Formal verification / specification",
    "U": "Sim-to-real safe RL", "V": "Human-aware / human-in-the-loop", "W": "Rule-based intervention",
    "X": "Foundation-model-assisted", "OTHER:benchmark": "Benchmark (no new mechanism)",
}
# Review-derived grouping of the mechanism categories (used for the taxonomy and trend analysis)
CLUSTER = {
    "A": "M1 Objective shaping", "B": "M1 Objective shaping", "C": "M1 Objective shaping",
    "L": "M1 Objective shaping", "M": "M1 Objective shaping",
    "D": "M2 Run-time intervention", "E": "M2 Run-time intervention", "S": "M2 Run-time intervention",
    "W": "M2 Run-time intervention",
    "F": "M3 Control-theoretic certificates", "G": "M3 Control-theoretic certificates",
    "H": "M3 Control-theoretic certificates", "I": "M3 Control-theoretic certificates",
    "J": "M3 Control-theoretic certificates",
    "T": "M4 Formal methods",
    "K": "M5 Robustness and uncertainty", "N": "M5 Robustness and uncertainty",
    "O": "M6 Learning-paradigm extensions", "P": "M6 Learning-paradigm extensions",
    "Q": "M6 Learning-paradigm extensions", "R": "M6 Learning-paradigm extensions",
    "U": "M6 Learning-paradigm extensions", "V": "M6 Learning-paradigm extensions",
    "X": "M6 Learning-paradigm extensions", "OTHER:benchmark": "M0 No mechanism (benchmark, representation, assurance case)",
    "OTHER:safety-oriented state representation": "M0 No mechanism (benchmark, representation, assurance case)",
    "OTHER:safety case (assurance argument)": "M0 No mechanism (benchmark, representation, assurance case)",
    "OTHER:learned risk-threshold monitor": "M0 No mechanism (benchmark, representation, assurance case)",
}
TASK = {"LK": "Lane keeping", "LC": "Lane changing", "MERGE": "On-ramp merging", "OVT": "Overtaking",
        "CF": "Car following / ACC", "INT": "Intersection", "RAB": "Roundabout", "CA": "Collision avoidance",
        "EMG": "Emergency manoeuvre", "PED": "Pedestrian interaction", "NAV": "Urban / route navigation",
        "MP": "Motion / trajectory planning", "TD": "Tactical decision making", "PLT": "Platooning",
        "COOP": "Cooperative driving", "RACE": "Autonomous racing", "PARK": "Parking", "E2E": "End-to-end driving"}
TIER = ["SIM-LOW", "SIM-HIFI", "SIM-DATA", "HIL", "SCALED", "CLOSED", "ROAD", "DEPLOY"]
TIER_LABEL = {"SIM-LOW": "Low-fidelity simulation", "SIM-HIFI": "High-fidelity simulation",
              "SIM-DATA": "Data-driven simulation", "HIL": "Hardware-in-the-loop", "SCALED": "Scaled vehicle",
              "CLOSED": "Closed course (full size)", "ROAD": "Public road", "DEPLOY": "Deployment"}
PHYSICAL = {"HIL", "SCALED", "CLOSED", "ROAD", "DEPLOY"}
LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]
SAFETY_METRICS = {"COLL", "VIOL", "TTC", "PET", "DIST", "RISK", "INTERV", "UNSAFE", "OFFROAD", "RULE"}
QUESTIONABLE = {"B0385", "B1149", "B1158", "B1342", "B1700"}   # codebook v1.3; B1700 is an additional report of B1149
PERIODS = [("2016-2020", 2016, 2020), ("2021-2022", 2021, 2022), ("2023-2024", 2023, 2024),
           ("2025-2026", 2025, 2026)]

# Every distinct `algorithm` value is mapped explicitly to (canonical name, family). A value that is
# not listed stops the script, so new batches force a deliberate mapping.
VB, ONP, OFFP, CON, OFFL, MB, GEN, OTH = ("Value-based", "On-policy policy gradient",
                                          "Off-policy actor-critic", "Constrained policy optimisation",
                                          "Offline RL", "Model-based RL", "Generic actor-critic", "Other / unspecified")
ALG = {
    "OTHER:TZMG Q-learning (Wolpertinger)": ("Q-learning", VB),
    "OTHER:DeepSet-Q with Gaussian mixture": ("DQN", VB), "OTHER:CQL dueling double DQN": ("CQL", OFFL),
    "OTHER:policy iteration (static output feedback)": ("Adaptive dynamic programming", MB),
    "OTHER:robust policy iteration (constrained zero-sum game)": ("Adaptive dynamic programming", MB),
    "OTHER:EQN": ("IQN", VB), "OTHER:constrained mixed policy gradient (CMPG)": ("Model-based AC", MB),
    "OTHER:safety value learning in world model": ("Model-based AC", MB),
    "MBPO": ("MBPO", MB), "OTHER:Bayesian DQN (NADM)": ("Bayesian DQN", VB),
    "OTHER:DACER++ (diffusion actor-critic, distributional)": ("Diffusion policy optimisation", OFFP),
    "OTHER:FPQN (fully parameterised quantile network)": ("Distributional DQN", VB),
    "OTHER:RL with MPC-embedded policy optimisation": ("Model-based RL + MPC", MB), "OTHER:SARSA": ("SARSA", VB),
    "OTHER:TD learning of collision probabilities": ("TD collision-probability learning", VB),
    "OTHER:adversarial actor-critic": ("Adversarial robust AC", GEN), "OTHER:bootstrapped DQN": ("Bootstrapped DQN", VB),
    "OTHER:constrained ADP (policy iteration)": ("Adaptive dynamic programming", MB),
    "OTHER:critic-only ADP": ("Adaptive dynamic programming", MB),
    "OTHER:distributional Q-learning (hierarchical)": ("Distributional DQN", VB),
    "OTHER:high-confidence policy improvement RL": ("High-confidence policy improvement", OTH),
    "OTHER:model-based RL with planning (IPL)": ("Model-based RL + MPC", MB),
    "OTHER:model-based offline RL with MPC planning (UMBRELLA)": ("Model-based offline RL", OFFL),
    "OTHER:receding-horizon multi-kernel ADP actor-critic": ("Adaptive dynamic programming", MB),
    "QL": ("Q-learning", VB), "Q-learning": ("Q-learning", VB), "DQN": ("DQN", VB), "DDQN": ("Double DQN", VB),
    "D3QN": ("Dueling double DQN", VB), "OTHER:QR-DQN": ("QR-DQN", VB), "OTHER:IQN": ("IQN", VB), "OTHER:IQN (implicit quantile network)": ("IQN", VB),
    "OTHER:Budgeted Fitted-Q (BFTQ)": ("Budgeted fitted-Q", CON), "OTHER:NFSP": ("NFSP", VB),
    "PPO": ("PPO", ONP), "TRPO": ("TRPO", ONP), "A2C": ("A2C", ONP), "MAPPO": ("MAPPO", ONP),
    "OTHER:GRPO": ("GRPO", ONP), "OTHER:episodic policy-search RL with curricula": ("Episodic policy search", ONP),
    "DDPG": ("DDPG", OFFP), "TD3": ("TD3", OFFP), "SAC": ("SAC", OFFP), "MADDPG": ("MADDPG", OFFP),
    "OTHER:DSAC (distributional SAC)": ("DSAC", OFFP), "OTHER:DSAC (ensemble distributional SAC)": ("DSAC", OFFP),
    "OTHER:DSAC with harmonic gradient": ("DSAC", OFFP),
    "OTHER:hybrid MPO (Maximum a Posteriori Policy Optimisation)": ("MPO", OFFP), "OTHER:hybrid MPO": ("MPO", OFFP),
    "OTHER:reward-free off-policy actor-critic with proxy values": ("Proxy-value actor-critic", OFFP),
    "OTHER:observation-robust actor-critic (discrete SAC-based)": ("SAC", OFFP),
    "OTHER:actor-critic with motion-planner actor": ("Actor-critic", GEN), "AC": ("Actor-critic", GEN),
    "SAC-Lag": ("SAC-Lagrangian", CON), "PPO-Lag": ("PPO-Lagrangian", CON), "TD3-Lag": ("TD3-Lagrangian", CON),
    # second update search (2026-11-13)
    "OTHER:policy-gradient attention encoder-decoder (sampling with greedy baseline)": ("REINFORCE-type policy gradient", ONP),
    "OTHER:constrained trust-region multi-agent policy optimisation (CARGO)": ("Constrained trust-region MARL", CON),
    "OTHER:constrained multi-objective policy gradient with constraint rectification (DSR-MOPO)": ("Constrained multi-objective policy gradient", CON),
    "OTHER:RISE-based adaptive critic (actor-critic NN)": ("Adaptive dynamic programming", MB),
    "OTHER:maximum-entropy actor-critic (SAC-type)": ("SAC", OFFP),
    "CPO": ("CPO", CON), "P3O": ("P3O", CON), "OTHER:PCPO (parallel constrained policy optimisation)": ("PCPO", CON),
    "OTHER:FOMI (trust-region constrained actor-critic)": ("FOMI", CON), "OTHER:OnCRPO": ("CRPO", CON),
    "OTHER:EPO": ("EPO", CON), "OTHER:FAC": ("FAC", CON), "OTHER:FAC-based safe actor-critic (SafeMR)": ("FAC", CON),
    "OTHER:TRPO-PID": ("TRPO-PID Lagrangian", CON), "OTHER:Safety Layer": ("Safety layer (Dalal)", CON),
    "OTHER:Recovery RL": ("Recovery RL", CON), "OTHER:dual-policy constrained actor-critic": ("Dual-policy constrained AC", CON),
    "OTHER:hybrid-action constrained actor-critic": ("Hybrid-action constrained AC", CON),
    "OTHER:IQN-Lagrangian with latent context encoder": ("IQN-Lagrangian", CON),
    "OTHER:IGCARL constrained adversarial policy optimisation": ("IGCARL", CON),
    "CQL": ("CQL", OFFL), "BCQ": ("BCQ", OFFL), "OTHER:CRR (critic regularised regression)": ("CRR", OFFL),
    "OTHER:causal-transformer offline safe RL": ("Transformer offline safe RL", OFFL),
    "OTHER:diffusion policy with DICE (3DICE)": ("Diffusion policy (DICE)", OFFL),
    "OTHER:SMORL (BCQ-based value learning + PDDP trajectory optimisation)": ("SMORL", OFFL),
    "OTHER:model-based RL with learned dynamics and MPC planning": ("Model-based RL + MPC", MB),
    "OTHER:model-based actor-critic (generalized exterior point)": ("Model-based AC", MB),
    "OTHER:CCAC (model-based actor-critic)": ("CCAC", MB), "OTHER:SPIL (model-based actor-critic)": ("SPIL", MB),
    "OTHER:safe actor-critic in DreamerV3 world model": ("DreamerV3 safe AC", MB),
    "MCTS": ("MCTS", OTH), "OTHER:UPPAAL Stratego strategy learning": ("UPPAAL Stratego", OTH),
    "OTHER:participant agents (various)": ("Various", OTH), "OTHER:case-study RL-trained NN controllers": ("Various", OTH),
    "OTHER:bounded residual RL (unspecified)": ("Unspecified", OTH), "NR": ("Not reported", OTH),
    # batches 11-19 (institutional PDFs), mapped 2026-10-08
    "A3C": ("A3C", ONP), "OTHER:PSA3C (parameter-sharing A3C)": ("A3C", ONP), "OTHER:DRQN": ("DRQN", VB),
    "OTHER:QMIX": ("QMIX", VB), "OTHER:VDN (constrained)": ("VDN", VB), "OTHER:discrete SAC": ("SAC", OFFP),
    "OTHER:CrossQ": ("CrossQ", OFFP), "OTHER:IQ-SAC (IQN critic in SAC)": ("SAC", OFFP),
    "OTHER:MATD3": ("MATD3", OFFP), "OTHER:DPPO (decentralised PPO)": ("PPO", ONP),
    "OTHER:hybrid-action PPO": ("PPO", ONP), "OTHER:policy gradient with baseline": ("REINFORCE with baseline", ONP),
    "OTHER:risk-aware MAA2C": ("A2C", ONP), "OTHER:bilevel Stackelberg actor-critic with curiosity": ("Actor-critic", GEN),
    "OTHER:generalized policy improvement (GPI) over Q-functions": ("GPI", VB),
    "OTHER:distributional Stackelberg Q-learning (C51 cost head)": ("C51 (distributional)", VB),
    "OTHER:DRL value tensor with MCTS": ("MCTS", OTH),
    "OTHER:AAC-MAA2C (Lagrangian multi-agent A2C)": ("MAA2C-Lagrangian", CON),
    "OTHER:ALM SAC-Discrete": ("SAC-augmented Lagrangian", CON), "OTHER:ALM-DDPG": ("DDPG-augmented Lagrangian", CON),
    "OTHER:ALPPO (augmented-Lagrangian PPO)": ("PPO-augmented Lagrangian", CON),
    "OTHER:lambda-PPO (Lagrangian PPO)": ("PPO-Lagrangian", CON), "OTHER:MAPPO-Lagrangian": ("MAPPO-Lagrangian", CON),
    "OTHER:MAPPO-Lagrangian with CVaR homotopy": ("MAPPO-Lagrangian", CON), "OTHER:MACPO": ("MACPO", CON),
    "OTHER:MAPCPO (multi-agent projected CPO)": ("MAPCPO", CON), "OTHER:RSCPO": ("RSCPO", CON),
    "OTHER:HCP4O (heterogeneous cluster constrained policy optimisation)": ("HCP4O", CON),
    "OTHER:Safe-SRPPO (constrained PPO with replay)": ("Constrained PPO", CON),
    "OTHER:worst-case PPO (PID-Lagrangian with CVaR cost)": ("PPO-PID Lagrangian (CVaR)", CON),
    "OTHER:state-wise Lagrangian SAC": ("SAC-Lagrangian", CON), "OTHER:Lyapunov-constrained SAC (LRSAC)": ("Lyapunov-constrained SAC", CON),
    "OTHER:WCSAC (worst-case SAC)": ("WCSAC", CON), "OTHER:WCA-SAC (worst-case-aware discrete SAC)": ("WCA-SAC", CON),
    "OTHER:constrained soft Q-learning (CSRL)": ("Constrained soft Q-learning", CON),
    "OTHER:constrained adversarial actor-critic (CAAC)": ("CAAC", CON),
    "OTHER:dual-constrained actor-critic (Lagrangian)": ("Dual-constrained AC", CON),
    "OTHER:fear-constrained actor-critic (FC-AC)": ("FC-AC", CON),
    "OTHER:latent-model SAC-Lagrangian with safety critic": ("SAC-Lagrangian", CON),
    "OTHER:TCHug-RL (Lagrangian TD3-style actor-critic)": ("TD3-Lagrangian", CON),
    "OTHER:model-based constrained policy search": ("Model-based constrained policy search", MB),
    "OTHER:constrained decision transformer + MACPO": ("Constrained decision transformer", OFFL),
    "OTHER:diffusion policy with ensemble Q (UADP)": ("Diffusion policy (UADP)", OFFL),
    # citation-search studies (Phase 8), mapped 2026-10-10
    "DuelingDQN": ("Dueling DQN", VB), "RainbowDQN": ("Rainbow DQN", VB), "PER-DQN": ("DQN (prioritised replay)", VB),
    "DRQN": ("DRQN", VB), "OTHER:Ape-X DQN": ("DQN (Ape-X)", VB), "OTHER:P-DQN": ("P-DQN", VB),
    "OTHER:IQN ensemble (EQN)": ("IQN", VB), "OTHER:value-network RL (SARL)": ("Value-network RL (SARL)", VB),
    "IPPO": ("IPPO", ONP), "OTHER:MA2C": ("A2C", ONP),
    "OTHER:actor-critic (RAD-DRL)": ("Actor-critic", GEN), "OTHER:ATAC (Tsallis actor-critic)": ("Tsallis actor-critic", OFFP),
    "OTHER:HACO (proxy-value off-policy RL)": ("Proxy-value actor-critic", OFFP),
    "OTHER:TS2C (off-policy actor-critic with teacher intervention)": ("Proxy-value actor-critic", OFFP),
    "OTHER:model-based actor-critic (GEP)": ("Model-based AC", MB), "OTHER:model-based actor-critic (ACOPFM)": ("Model-based AC", MB),
    "OTHER:RL planner with candidate policies": ("Unspecified", OTH), "BC": ("Behaviour cloning (with RL)", OTH),
    "OTHER:IQL-style offline actor-critic with HJ reachability value": ("IQL", OFFL),
    "OTHER:CQL-SAC (risk-adaptive)": ("CQL", OFFL),
    "OTHER:model-based actor-critic (SPRL)": ("Model-based AC", MB),
    "OTHER:RL policy as nominal MPC solver": ("Model-based AC", MB),
    "OTHER:actor-critic-identifier ADP (policy iteration)": ("Adaptive dynamic programming", MB),
    "OTHER:adaptive critic (prescribed-time learning)": ("Adaptive dynamic programming", MB),
    "OTHER:simplified actor-critic ADP": ("Adaptive dynamic programming", MB),
    # batches 20-24 (retrieval round 2026-10-09)
    "OTHER:constrained Q-learning-style path search (RLTT)": ("Constrained Q-learning path search", CON),
    "OTHER:option-based DQN": ("DQN", VB),
    "OTHER:PCPO (projection-based constrained policy optimisation)": ("PCPO", CON),
    "OTHER:defence-aware robust constrained actor-critic (DARRL)": ("Robust constrained AC", CON),
    "OTHER:constrained decision transformer": ("Constrained decision transformer", OFFL),
    "OTHER:adversarial multi-agent recurrent D3QN (ARMD2QN)": ("Dueling double DQN", VB),
    "OTHER:SMBPO (Lagrangian SAC with model rollouts)": ("Safe MBPO", MB),
    "OTHER:augmented-Lagrangian DDPG": ("DDPG-Lagrangian", CON),
    "OTHER:GP-based learning MPC (safe self-learning)": ("GP learning-based MPC", MB),
    "OTHER:diffusion implicit policy optimisation (DIMPO)": ("Diffusion policy optimisation", OFFP),
    "OTHER:critic-only ADP (fixed-time learning)": ("Adaptive dynamic programming", MB),
    "OTHER:constrained SAC with CBF/CLF residual losses (SAC-CC)": ("SAC-Lagrangian", CON),
    "OTHER:adversarial deep Q-learning with LSTM-GAN (NDRL)": ("DQN", VB),
    "OTHER:risk-aware prioritised replay DQN (RA-PRDQN)": ("DQN", VB),
    "OTHER:distributional DQN": ("Distributional DQN", VB),
    "OTHER:constrained multi-objective actor-critic (CMOAC)": ("Constrained multi-objective AC", CON),
    "OTHER:adversarial robust actor-critic (ARAC)": ("Adversarial robust AC", GEN),
    "OTHER:Actor-Critic-Safety (ACS) constrained actor-critic": ("Actor-Critic-Safety", CON),
    "OTHER:uncertainty-aware safe-evolving actor-critic (ensemble LCB)": ("Safe-evolving ensemble AC", OFFP),
    "OTHER:HRA-DDQN (Huber-regularised adaptive double DQN)": ("Double DQN", VB),
    "OTHER:off-policy integral RL (policy iteration)": ("Adaptive dynamic programming", MB),
    "OTHER:observation-uncertainty-constrained PPO (OUC-PPO)": ("PPO-Lagrangian", CON),
    "OTHER:feasible policy iteration with ensemble soft-MoE actor (AEGIS)": ("Feasible policy iteration", CON),
    "OTHER:LagCriticSAC (Lagrangian SAC with per-wheel cost critics)": ("SAC-Lagrangian", CON),
    "OTHER:expert-policy-constrained SAC (LLM-guided)": ("SAC", OFFP),
}


VENUE_NORM = [  # display names only; the evidence DB keeps the venue as recorded
    (r"arxiv", "arXiv"), (r"intelligent transportation systems conference|conference on intelligent transportation systems|\(ITSC\)",
     "IEEE Intelligent Transportation Systems Conference (ITSC)"),
    (r"american control conference", "American Control Conference (ACC)"),
    (r"conference on decision (and|&) control", "IEEE Conference on Decision and Control (CDC)"),
    (r"robotics and automation/proceedings|international conference on robotics and automation", "IEEE ICRA"),
    (r"intelligent robots and systems", "IEEE/RSJ IROS"),
    (r"intelligent vehicles symposium", "IEEE Intelligent Vehicles Symposium"),
]


def venue_norm(v):
    for pat, name in VENUE_NORM:
        if re.search(pat, v, re.I):
            return name
    return v


def split(v):
    return [x.strip() for x in v.split(";") if x.strip()]


def pct(n, d):
    return 0.0 if d == 0 else round(100.0 * n / d, 1)


def year_period(y):
    for lab, a, b in PERIODS:
        if a <= y <= b:
            return lab
    return "other"


# ----------------------------------------------------------------------------------------------
R = list(csv.DictReader(open(W / "extraction" / "evidence_db.csv")))
N = len(R)
for r in R:
    r["_year"] = int(r["year"])
    r["_period"] = year_period(r["_year"])
    algs = split(r["algorithm"])
    unknown = [a for a in algs if a not in ALG]
    if unknown:
        raise SystemExit(f"{r['study_id']}: algorithm value(s) not mapped in ALG: {unknown}")
    r["_alg"] = sorted({ALG[a][0] for a in algs})
    r["_fam"] = sorted({ALG[a][1] for a in algs})
    r["_lag"] = any(re.search(r"Lag|PID", a) for a in algs) or bool(
        re.search(r"lagrang|primal-dual", r["constraints"] + r["method_name"], re.I))
    r["_mech"] = split(r["mech"])
    r["_clusters"] = sorted({CLUSTER[m] for m in r["_mech"]})
    r["_safety_metrics"] = sorted(set(split(r["metrics"])) & SAFETY_METRICS)
    r["_physical"] = r["validation_tier"] in PHYSICAL

stats = {"N": N}
summary = []


def section(title):
    summary.append(f"\n## {title}\n")


def table(name, rows, header, note=""):
    """rows: list of tuples; writes csv and appends a markdown table to the summary."""
    with open(TAB / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    if note:
        summary.append(f"_{note}_\n")
    summary.append("| " + " | ".join(header) + " |")
    summary.append("|" + "---|" * len(header))
    for row in rows:
        summary.append("| " + " | ".join(str(x) for x in row) + " |")
    summary.append(f"\n(`analysis/tables/{name}.csv`)\n")


def freq(name, getter, labels=None, order=None, title=None, ids_max=12, denom=None, recs=None, note=""):
    recs = R if recs is None else recs
    d = len(recs) if denom is None else denom
    cnt, ids = Counter(), defaultdict(list)
    for r in recs:
        for v in set(getter(r)):
            cnt[v] += 1
            ids[v].append(r["study_id"])
    keys = order if order else [k for k, _ in cnt.most_common()]
    rows = []
    for k in keys:
        n = cnt.get(k, 0)
        lab = labels.get(k, k) if labels else k
        idl = ";".join(ids[k]) if 0 < n <= ids_max else ""
        rows.append((k, lab, n, pct(n, d), idl))
    stats[name] = {k: {"n": cnt.get(k, 0), "pct": pct(cnt.get(k, 0), d)} for k in keys}
    if title:
        section(title)
    table(name, rows, ["code", "label", "studies", f"% of {d}", f"study IDs (if <= {ids_max})"], note)
    return cnt


def crosstab(name, rget, cget, rows_order=None, cols_order=None, rlabels=None, title=None, note=""):
    ct = defaultdict(Counter)
    for r in R:
        for a in set(rget(r)):
            for b in set(cget(r)):
                ct[a][b] += 1
    rk = rows_order or sorted(ct)
    ck = cols_order or sorted({b for a in ct for b in ct[a]})
    rows = [[(rlabels or {}).get(a, a)] + [ct[a][b] for b in ck] + [sum(ct[a].values())] for a in rk]
    stats[name] = {a: dict(ct[a]) for a in rk}
    if title:
        section(title)
    table(name, rows, [""] + ck + ["row sum"], note)
    return ct


# ---------------------------------------------------------------- 1 Corpus profile (§20)
section("1 Corpus profile")
summary.append(f"Included studies with extraction records: **N = {N}**. "
               f"Publication years {min(r['_year'] for r in R)}-{max(r['_year'] for r in R)} "
               f"(2026 is a partial year, search conducted in October 2026).\n")
freq("year", lambda r: [r["year"]], order=sorted({r["year"] for r in R}), title="1.1 Studies per year")
freq("period", lambda r: [r["_period"]], order=[p[0] for p in PERIODS], title="1.2 Studies per period")
freq("pub_type", lambda r: [r["pub_type"]], title="1.3 Publication type")
vc = Counter(venue_norm(r["venue"]) for r in R)
freq("venue_top", lambda r: [venue_norm(r["venue"])], order=[v for v, n in vc.most_common() if n >= 2],
     title="1.4 Venues with at least two studies")
freq("country", lambda r: [r["country"]], title="1.5 Country/region of first (or corresponding) affiliation")
stats["qa_band"] = Counter(r["qa_band"] for r in R)

# ---------------------------------------------------------------- 2 RL methods (RQ3)
section("2 Reinforcement-learning methods (RQ3)")
freq("alg_family", lambda r: r["_fam"], title="2.1 Algorithm families (a study may use several)")
freq("algorithm", lambda r: r["_alg"], title="2.2 Algorithms (canonical names)", ids_max=5)
n_lag = sum(r["_lag"] for r in R)
n_con = sum(1 for r in R if CON in r["_fam"] or r["_lag"] or "B" in r["_mech"])
stats["lagrangian"] = {"n": n_lag, "pct": pct(n_lag, N)}
stats["constrained_any"] = {"n": n_con, "pct": pct(n_con, N)}
summary.append(f"Lagrangian / primal-dual solution: {n_lag} studies ({pct(n_lag, N)}%). "
               f"Any constrained formulation (constrained algorithm, Lagrangian, or mechanism B): "
               f"{n_con} ({pct(n_con, N)}%).\n")
freq("rl_paradigm", lambda r: split(r["rl_paradigm"]), title="2.3 RL paradigm")
freq("agents", lambda r: [r["agents"]], title="2.4 Single- vs multi-agent")
freq("action_level", lambda r: [r["action_level"]], title="2.5 Action level")
freq("network", lambda r: split(r["network"]), title="2.6 Network architectures")
freq("obs_type", lambda r: split(r["obs_type"]), title="2.7 Observation types")

# ---------------------------------------------------------------- 3 Safety mechanisms (RQ2, RQ5)
section("3 Safety formulations and mechanisms (RQ2, RQ5)")
freq("mech", lambda r: r["_mech"], labels=MECH, title="3.1 Safety mechanisms (all codes per study)", ids_max=8)
freq("mech_primary", lambda r: [r["mech_primary"]], labels=MECH, title="3.2 Primary safety mechanism", ids_max=8)
freq("mech_cluster", lambda r: r["_clusters"], title="3.3 Mechanism clusters (review-derived grouping)")
freq("mech_stage", lambda r: [r["mech_stage"]], title="3.4 When safety acts (training / execution / both)")
freq("safety_claim", lambda r: split(r["safety_claim"]), title="3.5 Type of safety claim")
n_cost = sum(1 for r in R if r["safety_cost"] not in ("NA", "") )
stats["explicit_safety_cost"] = {"n": n_cost, "pct": pct(n_cost, N)}
summary.append(f"Studies defining an explicit safety cost signal: {n_cost} ({pct(n_cost, N)}%).\n")
freq("n_mech", lambda r: [str(len(r["_mech"]))], order=sorted({str(len(r["_mech"])) for r in R}, key=int),
     title="3.6 Number of mechanism codes per study")

rows = []
for m in [k for k in MECH if k != "OTHER:benchmark"]:
    rs = [r for r in R if m in r["_mech"]]
    if not rs:
        rows.append((m, MECH[m], 0, "", "", "", "", ""))
        continue
    l3 = sum(1 for r in rs if r["safety_level"] in ("L3", "L4", "L5"))
    l4 = sum(1 for r in rs if r["safety_level"] in ("L4", "L5"))
    ph = sum(1 for r in rs if r["_physical"])
    emp = sum(1 for r in rs if split(r["safety_claim"]) == ["EMP"])
    qa = sorted(int(r["qa_total"]) for r in rs)
    rows.append((m, MECH[m], len(rs), pct(l3, len(rs)), pct(l4, len(rs)), pct(emp, len(rs)), ph, qa[len(qa) // 2]))
stats["mech_profile"] = {r[0]: r[2:] for r in rows}
section("3.7 Evidence profile of each mechanism (studies using the mechanism)")
table("mech_profile", rows, ["code", "mechanism", "studies", "% L3+", "% L4+", "% empirical-only claim",
                             "physical/HIL studies", "median QA"])

# ---------------------------------------------------------------- 4 Safety-control integration (§17)
section("4 Safety-control integration (§17)")
freq("rl_output", lambda r: [r["rl_output"]], title="4.1 What the RL policy outputs")
freq("safety_integration", lambda r: [r["safety_integration"]], title="4.2 How a run-time safety component is attached")
crosstab("rl_output_x_integration", lambda r: [r["rl_output"]], lambda r: [r["safety_integration"]],
         cols_order=["NONE", "FILTER", "MASK", "CORRECT", "EMBED"], title="4.3 RL output x safety integration")
freq("rl_role_s17", lambda r: [x.strip() for x in r["rl_role_s17"].split("|")], title="4.4 CLAUDE.md §17 roles")
freq("control", lambda r: split(r["control"]), title="4.5 Classical control components")
ctl = {"CBF": "F", "CLF/Lyapunov": "G", "CBF-CLF-QP": "H", "MPC": "I", "Reachability": "J", "Runtime assurance": "S"}
summary.append("Control-theoretic components (mechanism codes): " + "; ".join(
    f"{k} {stats['mech'][v]['n']} ({stats['mech'][v]['pct']}%)" for k, v in ctl.items()) + ".\n")
n_ct = sum(1 for r in R if set(r["_mech"]) & set("FGHIJ"))
stats["control_theoretic_any"] = {"n": n_ct, "pct": pct(n_ct, N)}
summary.append(f"Any of CBF, CLF, CBF-CLF-QP, MPC or reachability: {n_ct} ({pct(n_ct, N)}%).\n")

# ---------------------------------------------------------------- 5 Safety-evidence levels (§25-26)
section("5 Safety-evidence levels (review-derived L0-L5, §26)")
freq("safety_level", lambda r: [r["safety_level"]], order=LEVELS, title="5.1 Highest level substantiated")
crosstab("level_x_tier", lambda r: [r["safety_level"]], lambda r: [r["validation_tier"]], rows_order=LEVELS,
         cols_order=TIER, title="5.2 Safety level x validation tier")
crosstab("level_x_period", lambda r: [r["safety_level"]], lambda r: [r["_period"]], rows_order=LEVELS,
         cols_order=[p[0] for p in PERIODS], title="5.3 Safety level x period")
crosstab("level_x_cluster", lambda r: r["_clusters"], lambda r: [r["safety_level"]], cols_order=LEVELS,
         title="5.4 Mechanism cluster x safety level")
n_formal = sum(1 for r in R if "FORMAL" in split(r["safety_claim"]) or "PROB" in split(r["safety_claim"]))
stats["formal_or_prob_claim"] = {"n": n_formal, "pct": pct(n_formal, N)}
n_emp_only = sum(1 for r in R if split(r["safety_claim"]) == ["EMP"])
stats["empirical_only_claim"] = {"n": n_emp_only, "pct": pct(n_emp_only, N)}
summary.append(f"Studies whose only safety claim is empirical: {n_emp_only} ({pct(n_emp_only, N)}%). "
               f"Studies with a formal or probabilistic claim: {n_formal} ({pct(n_formal, N)}%).\n")

# ---------------------------------------------------------------- 6 Applications (RQ4, §18)
section("6 Driving applications (RQ4)")
freq("task", lambda r: split(r["task"]), labels=TASK, title="6.1 Driving tasks", ids_max=6)
freq("scenario", lambda r: split(r["scenario"]), title="6.2 Road scenarios")
freq("traffic", lambda r: [r["traffic"]], title="6.3 Other road users")
crosstab("task_x_cluster", lambda r: split(r["task"]), lambda r: r["_clusters"], rlabels=TASK,
         title="6.4 Task x mechanism cluster (application matrix, counts)")
crosstab("task_x_level", lambda r: split(r["task"]), lambda r: [r["safety_level"]], cols_order=LEVELS, rlabels=TASK,
         title="6.5 Task x safety level")

# ---------------------------------------------------------------- 7 Uncertainty (RQ6)
section("7 Uncertainty (RQ6)")
freq("uncertainty", lambda r: split(r["uncertainty"]), title="7.1 Uncertainty types addressed")
n_unc = sum(1 for r in R if split(r["uncertainty"]) != ["NONE"])
n_epi = sum(1 for r in R if {"EPI", "ALE"} & set(split(r["uncertainty"])))
stats["uncertainty_any"] = {"n": n_unc, "pct": pct(n_unc, N)}
stats["uncertainty_epi_ale"] = {"n": n_epi, "pct": pct(n_epi, N)}
summary.append(f"Any uncertainty addressed: {n_unc} ({pct(n_unc, N)}%); explicit epistemic or aleatoric "
               f"estimate: {n_epi} ({pct(n_epi, N)}%).\n")

# ---------------------------------------------------------------- 8 Simulation and evaluation (RQ7-RQ9, RQ11)
section("8 Environments, metrics, generalisation and validation (RQ7-RQ9, RQ11)")
freq("simulator", lambda r: split(r["simulator"]), title="8.1 Simulators used in experiments")
freq("dataset", lambda r: split(r["dataset"]), title="8.2 Datasets")
freq("validation_tier", lambda r: [r["validation_tier"]], labels=TIER_LABEL, order=TIER,
     title="8.3 Highest validation tier (RQ11)")
n_phys = sum(r["_physical"] for r in R)
stats["physical_any"] = {"n": n_phys, "pct": pct(n_phys, N)}
summary.append(f"Studies with any physical or hardware-in-the-loop evidence: {n_phys} ({pct(n_phys, N)}%); "
               f"simulation only: {N - n_phys} ({pct(N - n_phys, N)}%).\n")
crosstab("simulator_x_tier", lambda r: split(r["simulator"]), lambda r: [r["validation_tier"]], cols_order=TIER,
         title="8.4 Simulator x validation tier")
freq("metrics", lambda r: split(r["metrics"]), title="8.5 Evaluation metrics", ids_max=4)
n_sm = sum(1 for r in R if r["_safety_metrics"])
n_coll_only = sum(1 for r in R if r["_safety_metrics"] == ["COLL"])
n_ttc = sum(1 for r in R if {"TTC", "PET"} & set(r["_safety_metrics"]))
stats["safety_metric_any"] = {"n": n_sm, "pct": pct(n_sm, N)}
stats["collision_only_safety_metric"] = {"n": n_coll_only, "pct": pct(n_coll_only, N)}
stats["surrogate_ttc_pet"] = {"n": n_ttc, "pct": pct(n_ttc, N)}
summary.append(f"At least one safety metric: {n_sm} ({pct(n_sm, N)}%); collision rate as the only safety "
               f"metric: {n_coll_only} ({pct(n_coll_only, N)}%); surrogate safety measures TTC/PET: {n_ttc} "
               f"({pct(n_ttc, N)}%).\n")
freq("n_safety_metrics", lambda r: [str(len(r["_safety_metrics"]))],
     order=sorted({str(len(r["_safety_metrics"])) for r in R}, key=int), title="8.6 Number of distinct safety metrics per study")
freq("generalization", lambda r: split(r["generalization"]), title="8.7 Generalisation tests (RQ9)")
n_gen = sum(1 for r in R if split(r["generalization"]) != ["NONE"])
stats["generalization_any"] = {"n": n_gen, "pct": pct(n_gen, N)}
summary.append(f"Any generalisation test: {n_gen} ({pct(n_gen, N)}%).\n")
freq("baseline_types", lambda r: split(r["baseline_types"]), title="8.8 Baseline types")

# ---------------------------------------------------------------- 9 Reproducibility (RQ12)
section("9 Reproducibility (RQ12)")
for f, t in [("code", "9.1 Code availability"), ("data_avail", "9.2 Data availability"),
             ("hyperparams", "9.3 Hyperparameters reported"), ("eval_protocol", "9.4 Evaluation protocol"),
             ("stats", "9.5 Statistical reporting (variance, tests)"), ("compute", "9.6 Compute reported")]:
    freq(f, lambda r, f=f: [r[f]], title=t)
freq("seeds_reported", lambda r: ["reported" if r["seeds"] not in ("NR", "NA", "") else "not reported"],
     title="9.7 Random seeds reported")
crosstab("code_x_period", lambda r: [r["code"]], lambda r: [r["_period"]], cols_order=[p[0] for p in PERIODS],
         title="9.8 Code availability x period")

# ---------------------------------------------------------------- 9b Explainability (RQ10, codebook v1.5)
XAI = {r["study_id"]: r["explainability"] for r in csv.DictReader(open(W / "extraction" / "xai_codes.csv"))}
unknown = set(XAI) - {r["study_id"] for r in R}
if unknown:
    raise SystemExit(f"xai_codes.csv has IDs without extraction records: {unknown}")
for r in R:
    r["_xai"] = XAI.get(r["study_id"], "NONE")
freq("explainability", lambda r: [r["_xai"]], order=["VIS", "DESIGN", "NONE"], ids_max=16,
     title="9b Explainability (RQ10): VIS explanations inspected; DESIGN interpretability claimed by design; no user studies")

# ---------------------------------------------------------------- 10 AV stack (§28)
section("10 AV safety stack (§28)")
freq("stack", lambda r: split(r["stack"]), order=["PERC", "PRED", "PLAN", "DEC", "CTRL", "SUPERV", "RTA"],
     title="10.1 Stack layers addressed")

# ---------------------------------------------------------------- 11 Quality assessment (§14)
section("11 Quality assessment (Q1-Q12)")
freq("qa_band_t", lambda r: [r["qa_band"]], order=["High", "Medium", "Low"], title="11.1 Quality bands")
rows = []
for i in range(1, 13):
    v = [int(r[f"Q{i}"]) for r in R]
    rows.append((f"Q{i}", round(sum(v) / N, 2), v.count(2), v.count(1), v.count(0)))
stats["qa_items"] = {r[0]: {"mean": r[1], "n2": r[2], "n1": r[3], "n0": r[4]} for r in rows}
section("11.2 Item scores")
table("qa_items", rows, ["item", "mean (0-2)", "score 2", "score 1", "score 0"])
tot = [int(r["qa_total"]) for r in R]
stats["qa_total_mean"] = round(sum(tot) / N, 1)
stats["qa_total_median"] = sorted(tot)[N // 2]
summary.append(f"Mean total {stats['qa_total_mean']} / 24, median {stats['qa_total_median']}.\n")
rows = []
for g in ("journal", "conference", "preprint"):
    t = [int(r["qa_total"]) for r in R if r["pub_type"] == g]
    rows.append((g, len(t), round(sum(t) / len(t), 1) if t else ""))
stats["qa_by_pubtype"] = {r[0]: r[2] for r in rows}
section("11.3 Mean QA total by publication type")
table("qa_by_pubtype", rows, ["publication type", "studies", "mean total"])
rows = []
for p, a, b in PERIODS:
    t = [int(r["qa_total"]) for r in R if r["_period"] == p]
    rows.append((p, len(t), round(sum(t) / len(t), 1) if t else ""))
section("11.4 Mean QA total by period")
table("qa_by_period", rows, ["period", "studies", "mean total"])

# ---------------------------------------------------------------- 12 Temporal trends (§21)
section("12 Temporal trends (§21): share of studies per period")
feats = {
    "Reward design (A)": lambda r: "A" in r["_mech"],
    "Constrained RL (B)": lambda r: "B" in r["_mech"],
    "CBF/CLF/QP (F,G,H)": lambda r: bool(set(r["_mech"]) & set("FGH")),
    "MPC hybrid (I)": lambda r: "I" in r["_mech"],
    "Shield/filter/RTA (D,E,S)": lambda r: bool(set(r["_mech"]) & set("DES")),
    "Formal methods (T)": lambda r: "T" in r["_mech"],
    "Robust/risk/uncertainty (K,L,M,N)": lambda r: bool(set(r["_mech"]) & set("KLMN")),
    "Multi-agent": lambda r: r["agents"] != "SA",
    "Offline RL": lambda r: "OFF" in split(r["rl_paradigm"]) or "P" in r["_mech"],
    "Model-based": lambda r: "MB" in split(r["rl_paradigm"]) or "Q" in r["_mech"],
    "Human-in-the-loop (V)": lambda r: "V" in r["_mech"],
    "Foundation models (LLM/VLM)": lambda r: "LLM+RL" in split(r["rl_paradigm"]) or "X" in r["_mech"],
    "Run-time level L3+": lambda r: r["safety_level"] in ("L3", "L4", "L5"),
    "Physical / HIL validation": lambda r: r["_physical"],
    "Code released": lambda r: r["code"] == "Y",
}
per_n = {p[0]: sum(1 for r in R if r["_period"] == p[0]) for p in PERIODS}
rows, stats["trend"] = [], {}
for k, fn in feats.items():
    row = [k]
    stats["trend"][k] = {}
    for p in per_n:
        n = sum(1 for r in R if r["_period"] == p and fn(r))
        row.append(f"{n} ({pct(n, per_n[p])}%)")
        stats["trend"][k][p] = {"n": n, "pct": pct(n, per_n[p])}
    rows.append(row)
table("trends", rows, ["feature"] + [f"{p} (n={per_n[p]})" for p in per_n],
      "Cells: studies with the feature in the period (share of that period's studies).")

# ---------------------------------------------------------------- 13 Algorithm x mechanism (Figure 7)
section("13 Algorithm family x mechanism")
crosstab("family_x_cluster", lambda r: r["_fam"], lambda r: r["_clusters"], title="13.1 Algorithm family x mechanism cluster")
crosstab("family_x_primary", lambda r: r["_fam"], lambda r: [r["mech_primary"]], title="13.2 Algorithm family x primary mechanism")

# ---------------------------------------------------------------- 14 Sensitivity analysis
section("14 Sensitivity analysis")
subsets = {
    "all": R,
    "excl. questionable venues": [r for r in R if r["study_id"] not in QUESTIONABLE],
    "excl. Low QA": [r for r in R if r["qa_band"] != "Low"],
    "excl. preprints": [r for r in R if r["pub_type"] != "preprint"],
    "High QA only": [r for r in R if r["qa_band"] == "High"],
}
heads = {
    "simulation only": lambda r: not r["_physical"],
    "L3 or higher": lambda r: r["safety_level"] in ("L3", "L4", "L5"),
    "L4 or higher": lambda r: r["safety_level"] in ("L4", "L5"),
    "empirical-only claim": lambda r: split(r["safety_claim"]) == ["EMP"],
    "code released": lambda r: r["code"] == "Y",
    "no generalisation test": lambda r: split(r["generalization"]) == ["NONE"],
    "no uncertainty addressed": lambda r: split(r["uncertainty"]) == ["NONE"],
}
rows, stats["sensitivity"] = [], {}
for s, rs in subsets.items():
    row = [s, len(rs)]
    stats["sensitivity"][s] = {"N": len(rs)}
    for h, fn in heads.items():
        n = sum(1 for r in rs if fn(r))
        row.append(f"{pct(n, len(rs))}%")
        stats["sensitivity"][s][h] = pct(n, len(rs))
    rows.append(row)
table("sensitivity", rows, ["subset", "N"] + list(heads),
      "Headline proportions recomputed on subsets; stable values indicate the conclusions do not depend on weaker studies.")

# ---------------------------------------------------------------- 14b Assumptions behind run-time/formal safety (§24 Q4, §25)
ASSUME = {
    "known or accurate dynamics model": r"\bknown(?! motion)|accurate (vehicle |ego )?model|model accura|"
                                        r"nominal model|control-affine|kinematic|linear|dynamics|koopman|latent model|"
                                        r"model fidelity|hybrid model|model of (the )?vehicle|friction-circle model",
    "predictable other road users": r"constant[- ](velocity|speed|heading)|predict|worst-case|do not (change|turn|reverse|rear)|"
                                    r"non-adversarial|follow|bounded in speed|behaviour model|driver model|IDM|"
                                    r"motion of (surrounding|other)|other vehicles",
    "perfect perception or state": r"perfect|accurate (state|sens|percep|data|shar|online estimation)|ground[- ]truth|privileged|"
                                   r"ideal sens|observab|full(y)? observ|reliable perception|state measurement|state estimat",
    "optimisation feasibility": r"feasib",
    "bounded disturbance or error": r"bounded|disturbance|error bound|confidence bound|conformal",
    "reliable communication": r"(?<!no )(V2V|V2I|V2X|I2V)|(?<!no V2V )communicat|state sharing|shared",
    "correct learned component or rule set": r"critic|rules?\b|threshold|risk model|prior-knowledge|neural approximation|"
                                             r"safety-index|belief updater|return distribution",
}
sub = [r for r in R if r["safety_level"] in ("L3", "L4", "L5")]
stated = [r for r in sub if r["guarantee_assumptions"] not in ("NA", "")]
rows, stats["assumptions"] = [], {"N_L3plus": len(sub), "N_stated": len(stated)}
for k, p in ASSUME.items():
    ids = [r["study_id"] for r in stated if re.search(p, r["guarantee_assumptions"], re.I)]
    rows.append((k, len(ids), pct(len(ids), len(stated)), ";".join(ids) if len(ids) <= 12 else ""))
    stats["assumptions"][k] = {"n": len(ids), "pct": pct(len(ids), len(stated))}
section("14b Assumptions stated by L3-L5 studies")
summary.append(f"{len(stated)} of {len(sub)} studies at L3-L5 state the assumptions behind their safety claim "
               f"(regex coding of `guarantee_assumptions`; a study can match several themes).\n")
table("assumption_themes", rows, ["assumption theme", "studies", f"% of {len(stated)}", "study IDs (if <= 12)"])
nl4 = [r for r in R if r["safety_level"] == "L4"]
n_l4_sim = sum(1 for r in nl4 if not r["_physical"])
n_l4_low = sum(1 for r in nl4 if r["validation_tier"] == "SIM-LOW")
stats["L4_sim_only"] = {"n": n_l4_sim, "pct": pct(n_l4_sim, len(nl4))}
stats["L4_simlow"] = {"n": n_l4_low, "pct": pct(n_l4_low, len(nl4))}
summary.append(f"L4 studies validated only in simulation: {n_l4_sim} of {len(nl4)}; in low-fidelity simulation: "
               f"{n_l4_low} ({pct(n_l4_low, len(nl4))}%).\n")

# ---------------------------------------------------------------- 15 Detail listings for the synthesis
def listing(name, recs, fields, title):
    section(title)
    table(name, [[r["study_id"], r["year"]] + [r[f] for f in fields] for r in recs], ["study", "year"] + fields)


listing("physical_studies", sorted([r for r in R if r["_physical"]], key=lambda r: (TIER.index(r["validation_tier"]), r["year"])),
        ["validation_tier", "safety_level", "mech_primary", "task", "real_world"], "15.1 Studies with physical or HIL validation")
listing("l4_l5_studies", sorted([r for r in R if r["safety_level"] in ("L4", "L5")], key=lambda r: (r["safety_level"], r["year"])),
        ["safety_level", "mech", "validation_tier", "guarantee_assumptions"], "15.2 Studies at L4-L5 and their assumptions")
listing("multiagent_studies", sorted([r for r in R if r["agents"] != "SA"], key=lambda r: r["year"]),
        ["agents", "n_agents", "algorithm", "mech", "task", "safety_level", "validation_tier"], "15.3 Multi-agent studies")
listing("uncertainty_explicit", sorted([r for r in R if set(split(r["uncertainty"])) & {"EPI", "ALE"}], key=lambda r: r["year"]),
        ["uncertainty", "uncertainty_method", "mech_primary", "safety_level"], "15.4 Studies with explicit epistemic/aleatoric estimates")
listing("foundation_model_studies", sorted([r for r in R if "X" in r["_mech"] or "LLM+RL" in split(r["rl_paradigm"])], key=lambda r: r["year"]),
        ["method_name", "mech", "safety_level", "validation_tier"], "15.5 Foundation-model-assisted studies")

# ---------------------------------------------------------------- write outputs
(OUT / "stats.json").write_text(json.dumps(stats, indent=1, default=dict))
head = ["# Phase 5 statistics (generated by scripts/15_stats.py; do not edit by hand)\n",
        f"Source: extraction/evidence_db.csv, N = {N} studies. Percentages are of N unless stated."]
(OUT / "stats_summary.md").write_text("\n".join(head + summary) + "\n")


DIGIT_WORDS = dict(zip("0123456789", "Zero One Two Three Four Five Six Seven Eight Nine".split()))


def macro_name(*parts):
    parts = [re.sub(r"\d", lambda m: " " + DIGIT_WORDS[m.group()] + " ", p) for p in parts]
    s = "".join(p.title() if p.islower() else p for p in re.split(r"[^A-Za-z]+", " ".join(parts)) if p)
    return "st" + s


mac = ["% generated by scripts/15_stats.py -- do not edit", f"\\newcommand{{\\stN}}{{{N}}}"]
digits = dict(zip("0123456789", "Zero One Two Three Four Five Six Seven Eight Nine".split()))
for key in ("explainability", "safety_level", "validation_tier", "pub_type", "agents", "code", "mech", "mech_primary", "alg_family",
            "mech_cluster", "safety_integration", "rl_output", "stack", "period", "qa_band_t"):
    for k, v in stats[key].items():
        k2 = re.sub(r"^(\d{2})(\d{2})-(\d{2})(\d{2})$", r"\2to\4", k)   # periods: 2016-2020 -> 16to20
        nm = macro_name(key, re.sub(r"\d", lambda m: digits[m.group()], k2))
        mac.append(f"\\newcommand{{\\{nm}N}}{{{v['n']}}}")
        mac.append(f"\\newcommand{{\\{nm}P}}{{{v['pct']}}}")
for key in ("lagrangian", "constrained_any", "explicit_safety_cost", "control_theoretic_any", "formal_or_prob_claim",
            "empirical_only_claim", "uncertainty_any", "uncertainty_epi_ale", "physical_any", "safety_metric_any",
            "collision_only_safety_metric", "surrogate_ttc_pet", "generalization_any", "L4_sim_only", "L4_simlow"):
    nm = macro_name(key)
    mac.append(f"\\newcommand{{\\{nm}N}}{{{stats[key]['n']}}}")
    mac.append(f"\\newcommand{{\\{nm}P}}{{{stats[key]['pct']}}}")
mac.append(f"\\newcommand{{\\stQaMean}}{{{stats['qa_total_mean']}}}")
seen, out = set(), []
for line in mac:
    m = re.match(r"\\newcommand\{(\\\w+)\}", line)
    if m and m.group(1) in seen:
        raise SystemExit(f"duplicate macro {m.group(1)}")
    if m:
        seen.add(m.group(1))
    out.append(line)
(W / "manuscript" / "stats_macros.tex").write_text("\n".join(out) + "\n")
print(f"N={N}; tables={len(list(TAB.glob('*.csv')))}; macros={len(seen)}; summary -> analysis/stats_summary.md")
