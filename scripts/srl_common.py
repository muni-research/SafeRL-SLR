"""Shared loader for the Phase 6 scripts (figures and tables).

It executes the definition part of scripts/15_stats.py (label dictionaries, the ALG mapping and the
per-study preprocessing) so that figures and tables use exactly the same codes, clusters and
algorithm families as the statistics. Nothing here writes files.
"""
import json
from pathlib import Path

W = Path(__file__).resolve().parent.parent
_src = (W / "scripts" / "15_stats.py").read_text()
_cut = _src.index('\nstats = {"N": N}')
_ns = {"__file__": str(W / "scripts" / "15_stats.py")}
exec(compile(_src[:_cut], "15_stats.py (definitions)", "exec"), _ns)

_a = _src.index("ASSUME = {"); _b = _src.index("\nsub = ", _a)
exec(compile(_src[_a:_b], "15_stats.py (ASSUME)", "exec"), _ns)
ASSUME = _ns["ASSUME"]          # assumption themes (regexes over guarantee_assumptions)
R = _ns["R"]                    # list of study dicts with derived fields (_mech, _alg, _fam, _period ...)
N = _ns["N"]
MECH, CLUSTER, TASK = _ns["MECH"], _ns["CLUSTER"], _ns["TASK"]
TIER, TIER_LABEL, PHYSICAL = _ns["TIER"], _ns["TIER_LABEL"], _ns["PHYSICAL"]
LEVELS, PERIODS = _ns["LEVELS"], _ns["PERIODS"]
SAFETY_METRICS = _ns["SAFETY_METRICS"]
split, pct = _ns["split"], _ns["pct"]
ALG_FAMILY = {}                  # canonical algorithm name -> families it is mapped to
for _v in _ns["ALG"].values():
    ALG_FAMILY.setdefault(_v[0], set()).add(_v[1])
FAMILIES = [_ns[k] for k in ("OFFP", "VB", "ONP", "CON", "MB", "OFFL", "GEN", "OTH")]
PRISMA = json.loads((W / "manuscript" / "generated" / "prisma_counts.json").read_text())

CLUSTERS = ["M1 Objective shaping", "M2 Run-time intervention", "M3 Control-theoretic certificates",
            "M4 Formal methods", "M5 Robustness and uncertainty", "M6 Learning-paradigm extensions"]
CLUSTER_MECHS = {c: [m for m in "ABCDEFGHIJKLMNOPQRSTUVWX" if CLUSTER.get(m) == c] for c in CLUSTERS}


def has(r, code):
    return code in r["_mech"]


def l3plus(r):
    return r["safety_level"] in ("L3", "L4", "L5")


def l4plus(r):
    return r["safety_level"] in ("L4", "L5")


# ---------------------------------------------------------------- deployment-readiness chain (review-derived)
# Safe RL approach -> safety mechanism -> safety guarantee -> AV application -> evaluation -> deployment readiness.
GUARANTEE = ["G0 Asserted only", "G1 Empirical", "G2 Constraint in expectation", "G3 Run-time enforced",
             "G4 Formal under assumptions"]
EVALUATION = ["E1 Low-fidelity simulation", "E2 High-fidelity or data-driven simulation",
              "E3 Hardware-in-the-loop or scaled vehicle", "E4 Full-size vehicle (closed course or road)",
              "E5 Deployment"]
READINESS = ["Low", "Low-Medium", "Medium", "Medium-High", "High"]
READINESS_RULE = {
    "Low": "empirical or expectation-level guarantee (G0-G2), simulation only (E1-E2)",
    "Low-Medium": "run-time or formal guarantee (G3-G4) in simulation only, or a weaker guarantee with hardware evidence (E3-E4)",
    "Medium": "run-time or formal guarantee (G3-G4) on hardware-in-the-loop or a scaled vehicle (E3)",
    "Medium-High": "run-time or formal guarantee (G3-G4) on a full-size vehicle, closed course or road (E4)",
    "High": "deployment or certification evidence (E5)",
}
# primary-mechanism families used as the 'safety mechanism' stage of the chain
MECH_FAMILY = [("Reward shaping", "A"), ("Constrained RL / safety critic", "BC"), ("Risk-sensitive RL", "L"),
               ("Shield, mask or rule-based intervention", "DW"), ("Safety filter", "E"), ("Runtime assurance", "S"),
               ("Barrier / Lyapunov certificate (CBF, CLF, CBF-CLF-QP)", "FGH"), ("MPC hybrid", "I"),
               ("Reachability / formal verification", "JT"), ("Robust / uncertainty-aware RL", "KN"),
               ("Learning-paradigm extension", "OPQRUVX")]


def guarantee_index(r):
    return {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 4}[r["safety_level"]]


def evaluation_index(r):
    return {"SIM-LOW": 0, "SIM-HIFI": 1, "SIM-DATA": 1, "HIL": 2, "SCALED": 2, "CLOSED": 3, "ROAD": 3,
            "DEPLOY": 4}[r["validation_tier"]]


def readiness(r):
    g, e = guarantee_index(r), evaluation_index(r)
    if e == 4:
        return "High"
    if g >= 3 and e == 3:
        return "Medium-High"
    if g >= 3 and e == 2:
        return "Medium"
    if g >= 3 or e >= 2:
        return "Low-Medium"
    return "Low"


def mech_family(r):
    for name, codes in MECH_FAMILY:
        if r["mech_primary"] in codes:
            return name
    return "No mechanism of its own"


# ---------------------------------------------------------------- US spelling for all generated output
# The manuscript uses US spelling (authors' decision, 17 Nov 2026). Codebook values in the extraction database keep
# their original spelling (they are matched as data); generated tables, macro values and figure labels are converted.
import re as _re_us
IS=["decentralis","centralis","generalis","organis","conceptualis","idealis","maximis","minimis","normalis","optimis","regularis",
    "utilis","characteris","prioritis","emphasis","summaris","visualis","recognis","parameteris","discretis","linearis","randomis","operationalis"]
OTHER=[("catalogue","catalog"),("behaviour","behavior"),("colour","color"),("judgement","judgment"),("manoeuvre","maneuver"),
 ("modelled","modeled"),("modelling","modeling"),("travelled","traveled"),("towards","toward"),("defences","defenses"),("defence","defense"),
 ("labelled","labeled"),("labelling","labeling"),("favour","favor"),("neighbour","neighbor"),("signalling","signaling"),("programme","program"),
 ("centre","center"),("artefact","artifact"),("whilst","while")]
EXACT=[("analyse","analyze"),("analysed","analyzed"),("analysing","analyzing")]
def _case(w,out):
    if w.isupper(): return out.upper()
    if w[0].isupper(): return out[0].upper()+out[1:]
    return out
def us_spelling(s):
    """Convert British to US spelling in generated text (word-wise, case kept)."""
    n=0
    for b in IS:
        s,k=_re_us.subn(r"\b(?i:"+b+r")(e|ed|es|ing|ation|ations|er|ers|able)\b",
                    lambda m:_case(m.group(0),b[:-1]+"z"+m.group(1)),s); n+=k
    for b,u in OTHER:
        s,k=_re_us.subn(r"\b(?i:"+b+r")([a-z]*)\b",lambda m:_case(m.group(0),u+m.group(1)),s); n+=k
    for b,u in EXACT:
        s,k=_re_us.subn(r"\b(?i:"+b+r")\b",lambda m:_case(m.group(0),u),s); n+=k
    return s
