#!/usr/bin/env python3
"""Phase 6 tables (CLAUDE.md §19, Tables 1-14). Counts and percentages are computed here from
extraction/evidence_db.csv (via srl_common); example studies are cited by study ID, which is the BibTeX
key in manuscript/included_studies.bib (scripts/19_included_bib.py).

Example-selection rule (stated in the table notes): among the studies matching a row, prefer those whose
*primary* mechanism matches (where applicable), then the highest safety-evidence level, then the highest
quality score, then the most recent year. This keeps the choice of examples reproducible.

Output: manuscript/tables/tabNN_<name>.tex, and the same content spliced into manuscript/main.tex between
'%% BEGIN GENERATED <name>' and '%% END GENERATED <name>' markers (the Springer template requires a single
.tex file, so tables are inlined rather than \\input).
"""
import csv
import re
import runpy
from collections import Counter

import srl_common as S

R, N = S.R, S.N
OUT = S.W / "manuscript" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
MAIN = S.W / "manuscript" / "main.tex"
LV = {l: i for i, l in enumerate(S.LEVELS)}
XAI = {r["study_id"]: r["explainability"] for r in csv.DictReader(open(S.W / "extraction" / "xai_codes.csv"))}
TABLES = {}


def esc(s):
    return (s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
            .replace("<", r"$<$").replace(">", r"$>$"))


def p(n, d=N):
    return f"{S.pct(n, d):.1f}"


def np_(n, d=N):
    return f"{n} ({p(n, d)})"


# citation preference: Q1/Q2 journal articles (JCR quartile, stageD/journal_quartiles.csv) are chosen as examples
# whenever a row has one; other studies are cited only where no such example exists
PREF = {r["study_id"] for r in csv.DictReader(open(S.W / "stageD" / "journal_quartiles.csv")) if r["quartile"] in ("Q1", "Q2")}
# studies already cited in the hand-written text: preferred as table examples so tables add few new references
_txt = re.sub(r"%% BEGIN GENERATED (\S+).*?%% END GENERATED \1", "", (S.W / "manuscript" / "main.tex").read_text(), flags=re.S)
TEXT_CITED = {k.strip() for m in re.finditer(r"\\cite[a-z]*\{([^}]+)\}", _txt) for k in m.group(1).split(",")}


def examples(rs, k=1, primary=None):
    def key(r):
        return (0 if primary and r["mech_primary"] == primary else 1, 0 if r["study_id"] in PREF else 1,
                0 if r["study_id"] in TEXT_CITED else 1, -LV[r["safety_level"]], -int(r["qa_total"]), -r["_year"],
                r["study_id"])
    ids = [r["study_id"] for r in sorted(rs, key=key)[:k]]
    return r"\citealp{" + ",".join(ids) + "}" if ids else "--"


def cites(rs):
    ids = [r["study_id"] for r in sorted(rs, key=lambda r: (r["_year"], r["study_id"]))]
    return r"\citealp{" + ",".join(ids) + "}" if ids else "--"


def top(counter, k=2, d=None, fmt=lambda x: x):
    return "; ".join(f"{fmt(a)} ({b})" for a, b in counter.most_common(k)) or "--"


def typeset_dashes(tex):
    """Ranges and paired labels use an en dash in print (year ranges, L3--L5, G0--G2, Low--Medium, primal--dual).
    Data keys keep the hyphen; only the typeset table text changes. Citation keys are left alone."""
    parts = re.split(r"(\\cite\w*\{[^}]*\})", tex)
    for i in range(0, len(parts), 2):
        t = parts[i]
        t = re.sub(r"\b(20\d\d)-(20\d\d)\b", r"\1--\2", t)
        t = re.sub(r"\b([LGE]\d)-([LGE]\d)\b", r"\1--\2", t)
        t = re.sub(r"\b(Low|Medium)-(Medium|High)\b", r"\1--\2", t)
        t = t.replace("primal-dual", "primal--dual").replace("\u2013", "--")
        parts[i] = t
    return "".join(parts)



def table(name, caption, label, colspec, header, rows, note="", size=r"\footnotesize", side=False):
    env, width = ("sidewaystable", r"\textheight") if side else ("table", r"\textwidth")
    colspec = re.sub(r"(?<![A-Za-z])p\{", "P{", colspec)        # ragged-right paragraph columns
    lines = [f"\\begin{{{env}}}" + ("" if side else "[!htbp]"), f"\\caption{{{caption}}}\\label{{{label}}}", size,
             r"\setlength{\tabcolsep}{3pt}",
             f"\\begin{{tabularx}}{{{width}}}{{@{{}}{colspec}@{{}}}}", r"\toprule",
             " & ".join(header) + r" \\", r"\midrule"]
    for r in rows:
        if r == "MID":
            lines.append(r"\midrule")
        elif isinstance(r, str):
            lines.append(r)
        else:
            lines.append(" & ".join(str(c) for c in r) + r" \\")
    lines.append(r"\botrule")
    lines.append(r"\end{tabularx}")
    # long summary rows must wrap, otherwise an l-type multicolumn widens the table and squeezes the X column
    lines = [re.sub(r"\\multicolumn\{(\d+)\}\{@\{\}l\}\{",
                    lambda m: r"\multicolumn{" + m.group(1) + r"}{@{}>{\raggedright\arraybackslash}p{\dimexpr" + width
                    + r"-1em\relax}@{}}{", x) for x in lines]
    lines = [re.sub(r"\\multicolumn\{4\}\{l\}\{", r"\\multicolumn{4}{>{\\raggedright\\arraybackslash}p{7.5cm}}{", x)
             for x in lines]
    if note:
        lines.append(r"\footnotetext{" + note + "}")
    lines.append(f"\\end{{{env}}}")
    tex = S.us_spelling(typeset_dashes("\n".join(lines) + "\n"))
    (OUT / f"{name}.tex").write_text(f"% generated by scripts/20_tables.py -- do not edit\n{tex}")
    TABLES[name] = tex


EX_NOTE = ("Example: a study matching the row, chosen by primary mechanism (where applicable), journal article "
           "in a JCR Q1/Q2 journal, highest safety-evidence level, quality score and recency; all studies are listed "
           "in the extraction database (Supplementary S3).")
LEVEL_NOTE = "L3+/L4+: share of the row's studies whose highest substantiated evidence level is at least L3/L4."


# ---------------------------------------------------------------------------------------------------
def t01_notions():
    claim = lambda c: [r for r in R if c in S.split(r["safety_claim"])]
    emp_only = [r for r in R if S.split(r["safety_claim"]) == ["EMP"]]
    l5 = [r for r in R if r["safety_level"] == "L5"]
    rows = [
        ["Empirical", "Unsafe events were rare in the tested episodes and scenarios",
         "Collision, success or violation rates in simulation or tests", "",
         f"{np_(len(claim('EMP')))}; only claim: {np_(len(emp_only))}", examples(emp_only)],
        ["Statistical", "As empirical, with confidence intervals or hypothesis tests over episodes",
         "Repeated seeds, bootstrap intervals, significance tests", "", np_(len(claim("STAT"))),
         examples(claim("STAT"))],
        ["Constraint satisfaction in expectation", "Expected cumulative cost stays below a budget",
         "Constrained MDP solved by Lagrangian, trust-region or projection methods",
         r"\citep{altman1999cmdp,achiam2017cpo}", np_(len(claim("CEXP"))), examples(claim("CEXP"), primary="B")],
        ["Probabilistic", "Safety holds with a stated probability under a stochastic model",
         "Chance constraints, Gaussian-process or conformal bounds, CVaR", "", np_(len(claim("PROB"))),
         examples(claim("PROB"))],
        ["Robust", "Safety holds for every perturbation in a bounded set", "Adversarial training, robust MPC/CBF, bounded-disturbance tubes",
         "", np_(len(claim("ROB"))), examples(claim("ROB"))],
        ["Run-time enforced", "Each executed action is checked or corrected online, given the monitor's model",
         r"Shields, safety filters, runtime assurance (Simplex-type fallback)", r"\citep{alshiekh2018shielding}",
         np_(len(claim("RT"))), examples(claim("RT"))],
        ["Formal", "A property (invariance, reachability, temporal-logic specification) is proved or verified under explicit assumptions",
         "CBF/CLF certificates, Hamilton--Jacobi or set reachability, model checking",
         r"\citep{ames2017cbfqp,ames2019cbf}", np_(len(claim("FORMAL"))), examples(claim("FORMAL"))],
        ["Towards certification", "Run-time or formal safety carried onto a physical vehicle with a safety analysis; ultimately a safety case against automotive standards",
         "Physical tests with violation statistics; assurance arguments (e.g.\\ ISO 26262, ISO 21448)", "",
         f"L5: {np_(len(l5))}; safety case: 1", examples(l5) + r"; safety case \citealp{B1443}"],
    ]
    table("tab01_notions", "Notions of safety used in Safe RL for autonomous vehicles, what each establishes, and how "
          "often included studies make each kind of claim (a study can make several)", "tab:notions",
          r"p{2.0cm} L p{3.6cm} p{2.4cm} p{1.8cm} p{3.4cm}",
          ["Notion", "What is established", "Typical formulation", "Foundations", r"Studies, $n$ (\%)", "Example"],
          rows, note=f"Percentages of the {N} included studies. Claim types are coded per study (Supplementary "
          "S3). " + EX_NOTE, size=r"\scriptsize", side=True)


# ---------------------------------------------------------------------------------------------------
def t02_algorithms():
    rows = []
    for f in S.FAMILIES:
        rs = [r for r in R if f in r["_fam"]]
        if not rs:
            continue
        algs = Counter(a for r in rs for a in r["_alg"] if f in S.ALG_FAMILY.get(a, ()))
        cl = Counter(c for r in rs for c in r["_clusters"] if c in S.CLUSTERS)
        cons = sum(r["_lag"] or S.has(r, "B") for r in rs)
        rows.append([f, np_(len(rs)), esc(top(algs, 3)), p(cons, len(rs)),
                     esc(top(cl, 2, fmt=lambda c: c.split(" ")[0])), p(sum(map(S.l3plus, rs)), len(rs)),
                     examples(rs)])
    lag = sum(r["_lag"] for r in R); anyc = sum(r["_lag"] or S.has(r, "B") or "Constrained policy optimisation" in r["_fam"] for r in R)
    par = Counter(x for r in R for x in S.split(r["rl_paradigm"]))
    rows += ["MID", [r"\multicolumn{7}{@{}l}{Paradigms (a study can use several): model-free " + np_(par["MF"]) +
                     "; hierarchical " + np_(par["HRL"]) + "; model-based " + np_(par["MB"]) + "; imitation + RL " +
                     np_(par["IL+RL"]) + "; offline or offline-to-online " + np_(par["OFF"] + par["OFF2ON"]) +
                     "; LLM-assisted " + np_(par["LLM+RL"]) + r".}"],
             [r"\multicolumn{7}{@{}l}{Constrained formulations: Lagrangian or primal-dual solution " + np_(lag) +
              "; any constrained formulation " + np_(anyc) + r".}"]]
    table("tab02_algorithms", "RL algorithm families, their most frequent algorithms, the safety mechanisms they are paired "
          r"with, and the resulting strength of safety evidence", "tab:algorithms",
          r"p{2.2cm} p{1.2cm} L p{0.9cm} p{1.6cm} p{0.7cm} p{2.2cm}",
          ["Family", r"$n$ (\%)", "Most frequent algorithms ($n$)", r"Constr.\ (\%)", "Main clusters ($n$)",
           r"L3+ (\%)", "Example"], rows,
          note="Constr.: studies of the family using a Lagrangian/primal-dual solution or a constrained (CMDP) formulation. "
          "Clusters M1--M6 as in Fig.~\\ref{fig:taxonomy}. " + LEVEL_NOTE + " " + EX_NOTE, size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t03_mechanisms():
    rows = []
    for c in S.CLUSTERS:
        rows.append([r"\multicolumn{8}{@{}l}{\textit{" + c + "}}"])
        for m in S.CLUSTER_MECHS[c]:
            rs = [r for r in R if S.has(r, m)]
            if not rs:
                rows.append([m, esc(S.MECH[m]), "0", "--", "--", "--", "--", "not observed"])
                continue
            ex = sum(r["mech_stage"] in ("EXEC", "BOTH") for r in rs)
            emp = sum(S.split(r["safety_claim"]) == ["EMP"] for r in rs)
            rows.append([m, esc(S.MECH[m]), np_(len(rs)), p(ex, len(rs)), p(sum(map(S.l3plus, rs)), len(rs)),
                         p(sum(map(S.l4plus, rs)), len(rs)), p(emp, len(rs)),
                         f"{sum(r['_physical'] for r in rs)}; " + examples(rs, primary=m)])
    table("tab03_mechanisms", "Safety mechanisms by review-derived cluster: frequency, when they act, the strength of "
          "safety evidence they reach, and physical validation", "tab:mechanisms",
          r"p{0.3cm} p{3.8cm} p{1.4cm} p{1.0cm} p{0.9cm} p{0.9cm} p{1.0cm} L",
          ["", "Mechanism", r"$n$ (\%)", r"Exec.\ (\%)", r"L3+ (\%)", r"L4+ (\%)", r"Emp.\ only (\%)",
           "Physical/HIL $n$; examples"], rows,
          note="Exec.: mechanism acts at execution time (alone or in addition to training). Emp.\\ only: the study's only "
          "safety claim is empirical. " + LEVEL_NOTE + " " + EX_NOTE, size=r"\scriptsize", side=True)


# ---------------------------------------------------------------------------------------------------
SIMNAME = {"CUSTOM": "custom", "HWENV": "highway-env", "METADRIVE": "MetaDrive", "SIMULINK": "Simulink",
           "CARSIM": "CarSim", "SAFETYGYM": "Safety Gym", "PRESCAN": "PreScan", "COMMONROAD": "CommonRoad",
           "CARLA": "CARLA", "SUMO": "SUMO", "SMARTS": "SMARTS", "TORCS": "TORCS", "FLOW": "Flow", "UNITY": "Unity",
           "AIRSIM": "AirSim", "WEBOTS": "Webots", "GAZEBO": "Gazebo", "LGSVL": "LGSVL", "NUPLAN": "nuPlan",
           "WAYMAX": "Waymax", "BULLET": "PyBullet"}
SIM_MIN, DS_MIN = 10, 10     # simulators/datasets used by fewer studies are grouped
METNAME = {"COLL": "collision", "SUCC": "success", "REW": "reward", "SPEED": "speed", "TIME": "travel time",
           "TTC": "TTC", "COMF": "comfort", "VIOL": "violation", "JERK": "jerk", "DEV": "tracking dev.",
           "COMP": "computation", "DIST": "gap/distance", "INTERV": "intervention", "SAMPLE": "sample eff.",
           "ENERGY": "energy", "THRU": "throughput", "OFFROAD": "off-road", "ACC": "acceleration",
           "RULE": "rule violation", "RISK": "risk", "DSCORE": "driving score", "PET": "PET", "UNSAFE": "unsafe action"}


def t04_applications():
    tasks = sorted(S.TASK, key=lambda t: -sum(t in S.split(r["task"]) for r in R))
    rows = []
    for t in tasks:
        rs = [r for r in R if t in S.split(r["task"])]
        mech = Counter(m for r in rs for m in r["_mech"] if len(m) == 1)
        alg = Counter(a for r in rs for a in r["_alg"])
        sim = Counter(s for r in rs for s in S.split(r["simulator"]) if s in SIMNAME)
        met = Counter(m for r in rs for m in r["_safety_metrics"])
        rows.append([esc(S.TASK[t]), np_(len(rs)), top(mech, 3), esc(top(alg, 2)),
                     top(sim, 2, fmt=lambda s: SIMNAME[s]), top(met, 2, fmt=lambda m: METNAME[m]),
                     p(sum(map(S.l3plus, rs)), len(rs)), p(sum(map(S.l4plus, rs)), len(rs)), examples(rs, 1)])
    table("tab04_applications", "Application matrix: for each driving task, the dominant safety mechanisms, RL algorithms, "
          "simulators and safety metrics, and the strength of safety evidence", "tab:applications",
          r"p{2.3cm} p{1.4cm} p{2.6cm} p{2.7cm} p{2.3cm} L p{0.7cm} p{0.7cm} p{2.6cm}",
          ["Task", r"$n$ (\%)", "Mechanisms ($n$)", "Algorithms ($n$)", "Simulators ($n$)", "Safety metrics ($n$)",
           "L3+", "L4+", "Example"], rows, side=True,
          note="A study can address several tasks. Mechanism codes as in Table~\\ref{tab:mechanisms}. L3+/L4+ in \\%. "
          + LEVEL_NOTE + " " + EX_NOTE, size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t05_environments():
    sims = Counter(s for r in R for s in S.split(r["simulator"]))
    rows = [r"\multicolumn{6}{@{}l}{\textit{Simulators (studies using each; a study can use several)}} \\"]
    for s, n in sims.most_common():
        if s.startswith("OTHER:") or s == "NR" or n < SIM_MIN:
            continue
        rs = [r for r in R if s in S.split(r["simulator"])]
        tier = Counter(r["validation_tier"] for r in rs).most_common(1)[0][0]
        tk = Counter(t for r in rs for t in S.split(r["task"]))
        rows.append([SIMNAME.get(s, s), np_(n), esc(S.TIER_LABEL[tier]), esc(top(tk, 2, fmt=lambda t: S.TASK[t])),
                     str(sum(r["_physical"] for r in rs)), examples(rs, 1)])
    small = lambda x: x.startswith("OTHER:") or (sims[x] < SIM_MIN and x != "NR")
    other = sum(any(small(x) for x in S.split(r["simulator"])) for r in R)
    names = [SIMNAME.get(x, x[6:] if x.startswith("OTHER:") else x) for x, _ in sims.most_common() if small(x)]
    rows.append(["other named simulators", np_(other),
                 r"\multicolumn{4}{p{8.2cm}}{" + esc(", ".join(names[:8])) + (", and others" if len(names) > 8 else "") + "}"])
    rows += ["MID", r"\multicolumn{6}{@{}l}{\textit{Datasets (used for scenarios, calibration, replay or offline training)}} \\"]
    ds = Counter(d for r in R for d in S.split(r["dataset"]) if d not in ("NONE",))
    dsn = {"OWN": "own collected data", "NGSIM": "NGSIM", "HIGHD": "highD", "IND": "inD", "WAYMO": "Waymo Open",
           "INTERACTION": "INTERACTION", "NUPLAN": "nuPlan", "NUSCENES": "nuScenes", "ROUND": "rounD", "EXID": "exiD"}
    for d, n in ds.most_common():
        if d.startswith("OTHER:") or n < DS_MIN:
            continue
        rs = [r for r in R if d in S.split(r["dataset"])]
        tk = Counter(t for r in rs for t in S.split(r["task"]))
        rows.append([dsn.get(d, d), np_(n), "--", esc(top(tk, 2, fmt=lambda t: S.TASK[t])),
                     str(sum(r["_physical"] for r in rs)), examples(rs, 1)])
    nod = sum(any(not x.startswith("OTHER:") and x != "NONE" for x in S.split(r["dataset"])) or
              any(x.startswith("OTHER:") for x in S.split(r["dataset"])) for r in R)
    dsmall = lambda x: x != "NONE" and (x.startswith("OTHER:") or ds[x] < DS_MIN)
    dnames = [dsn.get(x, x[6:] if x.startswith("OTHER:") else x) for x, _ in ds.most_common() if dsmall(x)]
    rows.append(["other datasets", np_(sum(any(dsmall(x) for x in S.split(r["dataset"])) for r in R)),
                 r"\multicolumn{4}{p{8.2cm}}{" + esc(", ".join(dnames[:8])) + (", and others" if len(dnames) > 8 else "") + "}"])
    rows += ["MID", [r"\multicolumn{6}{@{}l}{Any dataset: " + np_(nod) + "; custom simulator: " + np_(sims["CUSTOM"]) +
                     r"; scripted surrounding traffic: " + np_(sum(r["traffic"] == "SCRIPTED" for r in R)) + ".}"]]
    table("tab05_environments", "Simulation environments and datasets used in the experiments of the included studies",
          "tab:environments", r"p{1.9cm} p{1.2cm} p{1.8cm} L p{0.6cm} p{3.1cm}",
          ["Environment", r"$n$ (\%)", "Most common highest tier", "Main tasks ($n$)", "Phys.", "Example"],
          rows, note="Phys.: studies with physical or hardware-in-the-loop evidence. Only simulators actually used in the experiments were coded (mentions in related work were "
          "ignored). Simulators and datasets used by fewer than ten studies are grouped. " + EX_NOTE, size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t06_metrics():
    met = Counter(m for r in R for m in S.split(r["metrics"]) if not m.startswith("OTHER:"))
    cat = {**{m: "safety" for m in S.SAFETY_METRICS}, "SUCC": "task", "REW": "learning", "SAMPLE": "learning",
           "SPEED": "efficiency", "TIME": "efficiency", "THRU": "efficiency", "ENERGY": "efficiency",
           "COMF": "comfort", "JERK": "comfort", "ACC": "comfort", "DEV": "tracking", "COMP": "computation",
           "DSCORE": "composite", "GEN": "composite"}
    desc = {"COLL": "collision rate or count", "VIOL": "constraint or safety-cost violations", "TTC": "time to collision (TTC)",
            "PET": "post-encroachment time (PET)", "DIST": "headway, gap or minimum distance", "RISK": "explicit risk measure",
            "INTERV": "safety-layer interventions or takeovers", "UNSAFE": "unsafe-action frequency",
            "OFFROAD": "off-road or lane departure", "RULE": "traffic-rule violations", "SUCC": "success or completion rate",
            "REW": "episode return", "SAMPLE": "sample efficiency / convergence", "SPEED": "average speed",
            "TIME": "travel time or time to goal", "THRU": "traffic throughput", "ENERGY": "energy or fuel",
            "COMF": "comfort index", "JERK": "jerk", "ACC": "acceleration", "DEV": "lateral/longitudinal tracking error",
            "COMP": "computation time", "DSCORE": "driving score (e.g.\\ CARLA leaderboard)", "GEN": "generalisation score"}
    order = sorted(met, key=lambda m: (["safety", "task", "efficiency", "comfort", "tracking", "learning", "computation",
                                        "composite"].index(cat[m]), -met[m]))
    rows = []
    for m in order:
        rows.append([cat[m], desc[m], np_(met[m])])
    sm = Counter(len(r["_safety_metrics"]) for r in R)
    coll_only = sum(r["_safety_metrics"] == ["COLL"] for r in R)
    stats = Counter(r["stats"] for r in R)
    rows += ["MID",
             [r"\multicolumn{3}{@{}l}{Studies with no safety metric: " + np_(sm[0]) + "; exactly one: " + np_(sm[1]) +
              "; collision as the only safety metric: " + np_(coll_only) + ".}"],
             [r"\multicolumn{3}{@{}l}{Statistical reporting: full (variance and tests) " + np_(stats["Y"]) +
              "; partial (variance only) " + np_(stats["P"]) + "; none " + np_(stats["N"]) + ".}"]]
    table("tab06_metrics", "Evaluation metrics reported by the included studies, grouped by what they measure",
          "tab:metrics", r"p{1.8cm} L p{2.0cm}", ["Category", "Metric", r"Studies, $n$ (\%)"], rows,
          note="A study usually reports several metrics. Reward and success are performance quantities and are not "
          "counted as safety metrics.", size=r"\footnotesize")


# ---------------------------------------------------------------------------------------------------
def t07_control():
    import re as _re
    rows = []
    OUTN = {"ACT": "action", "DEC": "decision", "TRAJ": "trajectory", "PARAM": "parameters", "RES": "residual"}
    INTN = {"FILTER": "filter", "MASK": "mask", "CORRECT": "corrective", "EMBED": "embedded", "NONE": "none"}
    hi = [r for r in R if S.l3plus(r) and r["guarantee_assumptions"] not in ("NA", "")]
    for m in "FGHIJS":
        rs = [r for r in R if S.has(r, m)]
        o = Counter(r["rl_output"] for r in rs); i = Counter(r["safety_integration"] for r in rs)
        ass = Counter(t for r in rs if r in hi for t, pat in S.ASSUME.items()
                      if _re.search(pat, r["guarantee_assumptions"], _re.I))
        rows.append([esc(S.MECH[m]), np_(len(rs)), top(o, 2, fmt=lambda x: OUTN[x]), top(i, 2, fmt=lambda x: INTN[x]),
                     esc(top(ass, 2)), p(sum(map(S.l4plus, rs)), len(rs)), str(sum(r["_physical"] for r in rs)),
                     examples(rs, 1, primary=m)])
    anyc = [r for r in R if any(S.has(r, m) for m in "FGHIJ")]
    rows += ["MID", [r"\multicolumn{8}{@{}l}{Any CBF, CLF, CBF-CLF-QP, MPC or reachability component: " + np_(len(anyc)) +
                     "; RL tunes a certified controller (parameters): " + np_(sum(r["rl_output"] == "PARAM" for r in R)) +
                     "; RL adds a bounded residual: " + np_(sum(r["rl_output"] == "RES" for r in R)) + ".}"]]
    table("tab07_control", "Integration of RL with control-theoretic and formal safety components: what the learned policy "
          "outputs, how the safety component is attached, what the guarantee assumes, and the evidence reached",
          "tab:control", r"p{2.6cm} p{1.4cm} p{2.4cm} p{2.4cm} L p{0.8cm} p{0.6cm} p{3.0cm}",
          ["Component", r"$n$ (\%)", "RL output ($n$)", "Attachment ($n$)", "Main stated assumptions ($n$)",
           r"L4+ (\%)", "Phys.", "Example"], rows, side=True,
          note="Assumption themes are coded from the stated assumptions of studies at L3--L5 (Sect.~\\ref{sec:integration}). "
          "Phys.: studies with physical or hardware-in-the-loop evidence. " + LEVEL_NOTE + " " + EX_NOTE,
          size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t08_uncertainty():
    UN = {"STOCH": "Stochastic traffic", "INTENT": "Intent of other road users", "MODEL": "Model / dynamics mismatch",
          "SENS": "Sensor noise or attack on observations", "DSHIFT": "Distribution shift", "PO": "Partial observability, occlusion",
          "PRED": "Prediction uncertainty", "EPI": "Epistemic (explicit estimate)", "DIST": "External disturbance",
          "ADV": "Adversarial agents or attacks", "ALE": "Aleatoric (explicit estimate)"}
    u = Counter(x for r in R for x in S.split(r["uncertainty"]) if x != "NONE")
    rows = []
    for k, n in u.most_common():
        rs = [r for r in R if k in S.split(r["uncertainty"])]
        mech = Counter(m for r in rs for m in r["_mech"] if m in "KLNFIJEDSQ")
        gen = sum(r["generalization"] not in ("NONE", "") for r in rs)
        rows.append([UN[k], np_(n), top(mech, 3), p(gen, len(rs)), p(sum(map(S.l3plus, rs)), len(rs)), examples(rs)])
    none = sum(r["uncertainty"] == "NONE" for r in R)
    ex = sum(bool({"EPI", "ALE"} & set(S.split(r["uncertainty"]))) for r in R)
    rows += ["MID", [r"\multicolumn{6}{@{}l}{No uncertainty addressed: " + np_(none) + "; any uncertainty: " + np_(N - none) +
                     "; explicit epistemic or aleatoric estimate: " + np_(ex) + ".}"]]
    table("tab08_uncertainty", "Uncertainty addressed by the included studies, the mechanisms used to handle it, and how "
          "often generalisation is tested alongside it", "tab:uncertainty",
          r"p{3.0cm} p{1.3cm} p{1.9cm} p{0.9cm} p{0.7cm} L",
          ["Uncertainty source", r"$n$ (\%)", "Main mechanisms ($n$)", r"Gen.\ test (\%)", r"L3+ (\%)", "Example"], rows,
          note="Mechanism codes as in Table~\\ref{tab:mechanisms}, restricted to robustness, risk, uncertainty, certificate "
          "and run-time mechanisms. Gen.\\ test: share of the row's studies with any generalization test. " + LEVEL_NOTE +
          " " + EX_NOTE, size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t09_multiagent():
    AG = {"MA-CEN": "Centralised (one policy controls all agents)", "MA-CTDE": "Centralised training, decentralised execution",
          "MA-DEC": "Decentralised (independent or game-theoretic)"}
    rows = []
    comm = S.ASSUME["reliable communication"]
    for k, lab in AG.items():
        rs = [r for r in R if r["agents"] == k]
        tk = Counter(t for r in rs for t in S.split(r["task"]))
        al = Counter(a for r in rs for a in r["_alg"])
        me = Counter(m for r in rs for m in r["_mech"] if len(m) == 1 and m != "O")
        cm = sum(bool(re.search(comm, r["guarantee_assumptions"], re.I)) for r in rs)
        rows.append([lab, np_(len(rs)), esc(top(tk, 2, fmt=lambda t: S.TASK[t])), esc(top(al, 2)), top(me, 3), str(cm),
                     p(sum(map(S.l3plus, rs)), len(rs)), str(sum(r["_physical"] for r in rs)), examples(rs)])
    ma = [r for r in R if r["agents"] != "SA"]
    rows += ["MID", [r"\multicolumn{9}{@{}l}{All multi-agent studies: " + np_(len(ma)) + "; at L4+: " +
                     str(sum(map(S.l4plus, ma))) + "; with physical or HIL evidence: " +
                     cites([r for r in ma if r["_physical"]]) + ".}"]]
    table("tab09_multiagent", "Multi-agent Safe RL for autonomous vehicles by training and execution architecture",
          "tab:multiagent", r"p{3.2cm} p{1.4cm} p{3.0cm} p{2.8cm} p{2.0cm} p{0.7cm} p{0.7cm} p{0.6cm} L",
          ["Architecture", r"$n$ (\%)", "Main tasks ($n$)", "Algorithms ($n$)", "Mechanisms ($n$)", "Comm.", "L3+",
           "Phys.", "Example"], rows, side=True,
          note="Comm.: studies whose safety claim states reliable V2V/V2I communication as an assumption. L3+ in \\%. "
          "Phys.: physical or hardware-in-the-loop evidence. " + LEVEL_NOTE + " " + EX_NOTE, size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t10_simreal():
    rows = []
    for t in ["HIL", "SCALED", "CLOSED", "ROAD"]:
        rs = [r for r in R if r["validation_tier"] == t]
        lv = Counter(r["safety_level"] for r in rs)
        rows.append([esc(S.TIER_LABEL[t]), str(len(rs)), ", ".join(f"{l} {lv[l]}" for l in S.LEVELS if lv[l]),
                     cites([r for r in rs if r["safety_level"] == "L5"]),
                     examples([r for r in rs if r["safety_level"] != "L5"], 2)])
    sim = Counter(r["validation_tier"] for r in R if not r["_physical"])
    rows += ["MID", [r"\multicolumn{5}{@{}l}{Simulation only: " + np_(N - sum(r["_physical"] for r in R)) +
                     f" (low-fidelity {sim['SIM-LOW']}, high-fidelity {sim['SIM-HIFI']}, data-driven {sim['SIM-DATA']}); "
                     "deployment: 0.}"]]
    table("tab10_simreal", "Studies that progress beyond simulation, by highest validation tier and safety-evidence level",
          "tab:simreal", r"p{2.0cm} p{0.4cm} p{2.0cm} p{2.8cm} L",
          ["Highest tier", "$n$", "Evidence levels", "Studies at L5", "Other studies (examples)"], rows,
          note="L5 requires run-time or formal safety (L3/L4) together with a physical test that reports a safety analysis "
          "(Sect.~\\ref{sec:levels}).", size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def t11_repro():
    per = [x[0] for x in S.PERIODS]
    items = [("Code released", lambda r: r["code"] == "Y"), ("Data released", lambda r: r["data_avail"] == "Y"),
             ("Hyperparameters fully reported", lambda r: r["hyperparams"] == "Y"),
             ("Hyperparameters partly reported", lambda r: r["hyperparams"] == "P"),
             ("Random seeds reported", lambda r: r["seeds"] not in ("NR", "NA", "")),
             ("Compute reported", lambda r: r["compute"] == "Y"),
             ("Full evaluation protocol", lambda r: r["eval_protocol"] == "Y"),
             ("Statistical reporting (variance and tests)", lambda r: r["stats"] == "Y"),
             ("Compared with another Safe RL method", lambda r: "SRL" in S.split(r["baseline_types"])),
             ("Compared with a classical controller", lambda r: "CLASS" in S.split(r["baseline_types"]))]
    rows = []
    for lab, f in items:
        cells = [np_(sum(f(r) for r in R))]
        for pe in per:
            rs = [r for r in R if r["_period"] == pe]
            cells.append(p(sum(f(r) for r in rs), len(rs)))
        rows.append([lab] + cells)
    nper = [sum(r["_period"] == pe for r in R) for pe in per]
    table("tab11_repro", "Reproducibility of the included studies, overall and by publication period", "tab:repro",
          r"L p{1.6cm}" + " p{1.4cm}" * 4,
          ["Item", r"All, $n$ (\%)"] + [f"{pe} (\\%, $n$={n})" for pe, n in zip(per, nper)], rows,
          note="Seeds reported: the number of seeds or their use is stated.", size=r"\footnotesize")


# ---------------------------------------------------------------------------------------------------
def t12_quality():
    Q = ["Research objective clearly defined", "Safe RL formulation clearly described", "Safety mechanism explicitly defined",
         "Experimental conditions sufficiently described", "Meaningful baselines included", "Safety metrics reported",
         "Performance metrics reported", "Uncertainty or disturbance conditions evaluated", "Generalisation evaluated",
         "Evaluation reproducible", "Code, data or simulator details available", "Evaluated beyond a trivial simulation"]
    rows = []
    for i, q in enumerate(Q, 1):
        v = Counter(r[f"Q{i}"] for r in R)
        mean = sum(int(r[f"Q{i}"]) for r in R) / N
        rows.append([f"Q{i}", q, f"{mean:.2f}", p(v["2"]), p(v["1"]), p(v["0"])])
    band = Counter(r["qa_band"] for r in R)
    tot = sorted(int(r["qa_total"]) for r in R)
    bypt = {t: [int(r["qa_total"]) for r in R if r["pub_type"] == t] for t in ("journal", "conference", "preprint")}
    rows += ["MID", [r"\multicolumn{6}{@{}l}{Total score (0--24): mean " + f"{sum(tot) / N:.1f}, median {tot[N // 2]}" +
                     "; bands: high ($\\ge$18) " + np_(band["High"]) + ", medium (12--17) " + np_(band["Medium"]) +
                     ", low ($\\le$11) " + np_(band["Low"]) + ".}"],
             [r"\multicolumn{6}{@{}l}{Mean total by publication type: " + "; ".join(
                 f"{t} {sum(v) / len(v):.1f} ($n$={len(v)})" for t, v in bypt.items()) + ".}"]]
    table("tab12_quality", "Quality assessment of the included studies (each criterion scored 0, 1 or 2)", "tab:quality",
          r"p{0.6cm} L p{0.9cm} p{1.1cm} p{1.1cm} p{1.1cm}",
          ["Item", "Criterion", "Mean", r"Score 2 (\%)", r"Score 1 (\%)", r"Score 0 (\%)"], rows,
          note="Scores and the justification of every score below 2 are in the extraction database (Supplementary "
          "S4).", size=r"\footnotesize")


# ---------------------------------------------------------------------------------------------------
GAPTEXT = {
    "G1": "Simulation-to-reality and deployment gap", "G2": "Strong guarantees only in simple simulators (assurance--realism inversion)",
    "G3": "Guarantees conditional on idealised prediction, models and perception", "G4": "Narrow and inconsistent safety metrics; weak statistics",
    "G5": "No shared benchmark or evaluation protocol", "G6": "Limited uncertainty modelling, especially perception",
    "G7": "Narrow generalisation testing", "G8": "Interactive and vulnerable-road-user scenarios under-served",
    "G9": "Expected-value constraints do not cover rare catastrophic events", "G10": "Weak comparative baselines",
    "G11": "Reproducibility not improving", "G12": "Safe RL absent from perception and prediction; end-to-end safety unaddressed",
    "G13": "Explainability unexamined", "G14": "Formal methods not scaling to learned driving policies",
    "G15": "Weak link to safety standards and target-hardware evidence"}
GAPX = {  # second piece of evidence per gap (computed below) and illustrative studies
    "G1": ("road tests", lambda: f"{sum(r['validation_tier'] == 'ROAD' for r in R)} public-road studies, 0 deployments", ["B0761", "B0716"]),
    "G2": ("L5", lambda: f"{sum(r['safety_level'] == 'L5' for r in R)} studies at L5", ["B0757", "B0896"]),
    "G3": ("", lambda: "fragility shown under attack, model error and sensor faults", ["A164", "B0761", "B1230"]),
    "G4": ("", lambda: f"collision the only safety metric in {p(sum(r['_safety_metrics'] == ['COLL'] for r in R))}\\%; "
           f"no statistics in {p(sum(r['stats'] == 'N' for r in R))}\\%", ["B1403", "B1813"]),
    "G5": ("", lambda: f"scripted traffic in {p(sum(r['traffic'] == 'SCRIPTED' for r in R))}\\%", ["B0930", "B1162"]),
    "G6": ("", lambda: f"sensor uncertainty in {p(sum('SENS' in S.split(r['uncertainty']) for r in R))}\\%", ["B0750", "B1430"]),
    "G7": ("", lambda: f"weather/friction {sum('WEATHER' in S.split(r['generalization']) for r in R)}, vehicle dynamics "
           f"{sum('DYN' in S.split(r['generalization']) for r in R)}, traffic rules 0", ["B0754", "B1169"]),
    "G8": ("", lambda: f"pedestrian interaction in {p(sum('PED' in S.split(r['task']) for r in R))}\\%", ["B1046", "B1021"]),
    "G9": ("", lambda: "rare-event or tail-risk methods in a handful of studies", ["B0658", "B1798", "B1403"]),
    "G10": ("", lambda: f"classical-controller baseline in {p(sum('CLASS' in S.split(r['baseline_types']) for r in R))}\\%", ["B0308", "B0805"]),
    "G11": ("", lambda: f"seeds reported in {p(sum(r['seeds'] not in ('NR', 'NA', '') for r in R))}\\%", ["B1692"]),
    "G12": ("", lambda: f"image input in {p(sum('IMG' in S.split(r['obs_type']) for r in R))}\\%; end-to-end studies at L3+: "
            f"{sum('E2E' in S.split(r['task']) and S.l3plus(r) for r in R)}", ["B1640"]),
    "G13": ("", lambda: "no study evaluates explanations with users", ["B0268", "B1427"]),
    "G14": ("", lambda: "formal-methods share " + " / ".join(
        p(sum(S.has(r, "T") for r in R if r["_period"] == pe[0]), sum(r["_period"] == pe[0] for r in R)) + "\\%"
        for pe in S.PERIODS) + " across the four periods", ["B0937", "B1230"]),
    "G15": ("", lambda: f"{sum(r['validation_tier'] == 'HIL' for r in R)} HIL studies; one safety case", ["B1443"]),
}


def t13_gaps(G):
    rows = []
    order = ["G1", "G2", "G15", "G3", "G6", "G9", "G4", "G8", "G12", "G5", "G7", "G10", "G11", "G13", "G14"]
    gi = {g[0]: g for g in G}
    for gid in order:
        g, prob, lab, val, den = gi[gid]
        _, f, ids = GAPX[gid]
        rows.append([gid, GAPTEXT[gid], f"{esc(lab)}: {val:.1f}\\% ({esc(den.replace('one safety case, B1443', f'of {N} studies'))}); {f()}", prob,
                     r"\citealp{" + ",".join(ids[:1]) + "}"])
    table("tab13_gaps", "Research gaps supported by the evidence, the indicator that quantifies each gap, and the core "
          "research problem it feeds", "tab:gaps", r"p{0.5cm} p{4.2cm} L p{0.6cm} p{4.4cm}",
          ["ID", "Gap", "Evidence (computed from the extraction database)", "Prob.", "Illustrative study"], rows,
          note="Indicators as in Fig.~\\ref{fig:gaps}. Problems P1--P8 are defined in Sect.~\\ref{sec:gaps}. The illustrative "
          "study documents the gap or points to a partial answer.", size=r"\scriptsize", side=True)


def t14_roadmap():
    R_ = [
        ("Short", "R1", "Common safety evaluation protocol: several safety metrics with confidence intervals, violations during "
         "training and testing, TTC/PET distributions and intervention rates; Safe RL and classical baselines", "P6; G4, G5, G10",
         ["B0308", "B0805", "B0930", "B1162", "B1692"]),
        ("Short", "R2", "Reproducibility minimum: code, seeds, simulator configurations and scenario files released with every "
         "safety claim", "P6; G11", ["B0847", "B0972"]),
        ("Short", "R3", "Report the safety-evidence level reached and every assumption the guarantee needs", "P1, P2; G2, G3",
         ["B1116", "B0987"]),
        ("Medium", "R4", "Perception- and prediction-aware certificates whose margins come from calibrated uncertainty "
         "(conformal, Gaussian-process, observer, robust or chance-constrained bounds), tested against noise and attacks",
         "P2, P5; G3, G6, G12", ["B0750", "A053", "B0910", "B1777", "B1430"]),
        ("Medium", "R5", "Uncertainty-triggered runtime assurance with verified fallbacks, evaluated on embedded hardware",
         "P1, P2; G1, G6", ["A096", "B1093", "B0653"]),
        ("Medium", "R6", "Interactive, multi-agent and vulnerable-road-user safety with reactive or human traffic, "
         "communication loss and harm-weighted costs", "P4; G8", ["B0882", "B0974", "B1046", "B1808"]),
        ("Medium", "R7", "State-wise and tail-risk constraints and safety-critical scenario generation against the current "
         "policy", "P3; G9", ["B0658", "B1798", "B1813", "B1403"]),
        ("Medium", "R8", "Staged sim-to-real pipelines that carry the same safety layer from high-fidelity simulation "
         "through HIL and closed courses to supervised road trials", "P1; G1, G7", ["A140", "B0757", "B1169", "B0761"]),
        ("Long", "R9", "Compositional verification of the safety layer and run-time monitoring of its assumptions",
         "P7; G14", ["B0937", "B0157", "B0029", "B1230"]),
        ("Long", "R10", "Certification-oriented safety cases that map RL evidence to automotive standards, with the policy "
         "bounded by an assured supervisor", "P7; G15", ["B1443"]),
        ("Long", "R11", "Offline, world-model, human-guided and foundation-model methods kept inside an independent "
         "safety envelope; explanations evaluated with users", "P8; G13", ["B1584", "B1780", "B1745"]),
    ]
    rows = [[h, rid, txt, pg, r"\citealp{" + ",".join(ids[:1]) + "}"] for h, rid, txt, pg, ids in R_]
    table("tab14_roadmap", "Future research directions, each linked to the core problems (P) and gaps (G) it addresses "
          "and to studies that already point the way", "tab:roadmap", r"p{0.9cm} p{0.5cm} L p{1.9cm} p{2.6cm}",
          ["Horizon", "ID", "Direction", "Addresses", "Building on"], rows, size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
RDY_SHORT = {"Low": "L", "Low-Medium": "LM", "Medium": "M", "Medium-High": "MH", "High": "H"}


def readiness_examples(rs, k=1):
    order = {r: i for i, r in enumerate(S.READINESS)}
    rs = sorted(rs, key=lambda r: (-order[S.readiness(r)], 0 if r["study_id"] in PREF else 1,
                                   0 if r["study_id"] in TEXT_CITED else 1, -LV[r["safety_level"]],
                                   -int(r["qa_total"]), -r["_year"]))
    return r"\citealp{" + ",".join(r["study_id"] for r in rs[:k]) + "}" if rs else "--"


def t15_framework():
    rows = []
    fams = [n for n, _ in S.MECH_FAMILY]
    for f in fams:
        rs = [r for r in R if S.mech_family(r) == f]
        alg = Counter(a for r in rs for a in r["_alg"] if a not in ("Not reported", "Various", "Unspecified"))
        g = Counter(S.GUARANTEE[S.guarantee_index(r)] for r in rs)
        gmod = g.most_common(1)[0][0].split(" ", 1)[1]
        g3 = sum(S.guarantee_index(r) >= 3 for r in rs)
        tk = Counter(t for r in rs for t in S.split(r["task"]))
        rd = Counter(S.readiness(r) for r in rs)
        dist = "/".join(str(rd[x]) for x in S.READINESS[:4])
        med = sum(rd[x] for x in ("Medium", "Medium-High", "High"))
        sim = sum(not r["_physical"] for r in rs); phys = len(rs) - sim
        rows.append([esc(f), str(len(rs)), esc(top(alg, 2)), f"{gmod}; G3+ {p(g3, len(rs))}\\%",
                     esc(top(tk, 2, fmt=lambda t: S.TASK[t])), f"{sim} / {phys}",
                     dist, p(med, len(rs)), readiness_examples(rs)])
    tot = Counter(S.readiness(r) for r in R)
    rows += ["MID", [r"\multicolumn{9}{@{}l}{All studies: readiness Low " + str(tot["Low"]) + ", Low--Medium " +
                     str(tot["Low-Medium"]) + ", Medium " + str(tot["Medium"]) + ", Medium--High " + str(tot["Medium-High"]) +
                     ", High " + str(tot["High"]) + ".}"]]
    table("tab15_framework", "The Safe RL deployment-readiness chain: for each family of primary safety mechanism, the "
          "typical RL approach, the safety guarantee it reaches, the AV applications, the evaluation setting and the "
          "resulting deployment readiness (review-derived; computed from the coded evidence of every study)",
          "tab:framework", r"p{2.3cm} p{0.5cm} p{2.4cm} p{2.3cm} p{3.1cm} p{1.0cm} p{1.6cm} p{0.8cm} L",
          ["Safety mechanism (primary)", "$n$", "Safe RL approach ($n$)", "Typical guarantee", "Main AV applications ($n$)",
           "Sim.\\ only / phys.", "Readiness L / LM / M / MH", r"Med.+ (\%)", "Example"],
          rows, side=True,
          note="Guarantee classes: G0 asserted only, G1 empirical, G2 constraint satisfied in expectation, G3 run-time "
          "enforced, G4 formal under stated assumptions (from evidence levels L0--L5, with L5 counted as G4). Readiness: "
          + "; ".join(f"{k} = {v}" for k, v in S.READINESS_RULE.items()) + ". Readiness distribution lists Low/Low--Medium/"
          "Medium/Medium--High; no study reaches High. Sim.\\ only / phys.: studies evaluated only in simulation / with physical or hardware-in-the-loop evidence; Med.+: share at Medium readiness or higher. Example: highest readiness, then a JCR Q1/Q2 journal article, evidence level, quality score and recency.",
          size=r"\scriptsize")


def t16_readiness_tasks():
    tasks = sorted(S.TASK, key=lambda t: -sum(t in S.split(r["task"]) for r in R))
    rows = []
    for t in tasks:
        rs = [r for r in R if t in S.split(r["task"])]
        rd = Counter(S.readiness(r) for r in rs)
        med = sum(rd[x] for x in ("Medium", "Medium-High", "High"))
        rows.append([esc(S.TASK[t]), str(len(rs))] + [str(rd[x]) for x in S.READINESS[:4]] +
                    [p(med, len(rs)), readiness_examples(rs)])
    table("tab16_readiness_tasks", "Deployment readiness by driving task (review-derived readiness classes, see "
          "Table~\\ref{tab:framework})", "tab:readinesstasks",
          r"p{3.0cm} p{0.5cm} p{0.6cm} p{0.6cm} p{0.6cm} p{0.6cm} p{1.4cm} L",
          ["Task", "$n$", "Low", "Low--Med.", "Med.", "Med.--High", r"Medium or higher (\%)", "Highest-readiness examples"],
          rows, note="A study can address several tasks.", size=r"\scriptsize")


# ---------------------------------------------------------------------------------------------------
def splice():
    tex = MAIN.read_text()
    for name, body in TABLES.items():
        b, e = f"%% BEGIN GENERATED {name}", f"%% END GENERATED {name}"
        if b in tex:
            tex = re.sub(re.escape(b) + r".*?" + re.escape(e), lambda m: f"{b}\n{body}{e}", tex, flags=re.S)
        else:
            print(f"  marker for {name} not found in main.tex (table written to tables/ only)")
    MAIN.write_text(tex)


if __name__ == "__main__":
    G = runpy.run_path(str(S.W / "scripts" / "18_figures.py"), run_name="lib")["gap_indicators"]()
    t01_notions(); t02_algorithms(); t03_mechanisms(); t04_applications(); t05_environments(); t06_metrics()
    t07_control(); t08_uncertainty(); t09_multiagent(); t10_simreal(); t11_repro(); t12_quality(); t13_gaps(G)
    t14_roadmap(); t15_framework(); t16_readiness_tasks()
    splice()
    print(f"wrote {len(TABLES)} tables to {OUT.relative_to(S.W)}")
