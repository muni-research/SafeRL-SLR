#!/usr/bin/env python3
"""Phase 7: compute every number quoted in the manuscript text and write it as a LaTeX macro
(\\n<Name>, letters only), so that the prose never contains hand-typed statistics.

Sources: extraction/evidence_db.csv (via srl_common), manuscript/generated/prisma_counts.json,
extraction/xai_codes.csv and the batch files (retrieval round of each study).
Output: manuscript/generated/text_numbers.tex, spliced into main.tex between
'%% BEGIN GENERATED text_numbers' and '%% END GENERATED text_numbers'.
Convention: <Name>N = count, <Name>P = percentage (one decimal) of the stated denominator.
"""
import csv
import glob
import re
from collections import Counter

import srl_common as S

R, N = S.R, S.N
M = {}


def put(name, value):
    assert re.fullmatch(r"[A-Za-z]+", name), name
    assert name not in M, f"duplicate macro {name}"
    M[name] = value


def np_(name, n, d=N):
    put(name + "N", n)
    put(name + "P", f"{S.pct(n, d):.1f}")


def cnt(f, rs=R):
    return sum(1 for r in rs if f(r))


DIG = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
       "8": "Eight", "9": "Nine"}


def alpha(s):
    s = "".join(DIG.get(c, c) for c in s)
    return re.sub(r"[^A-Za-z]", "", s)


# ---------------------------------------------------------------- PRISMA
P = S.PRISMA
idf, scr, el, inc = P["identification"], P["screening"], P["eligibility"], P["included"]
put("RecSeed", idf["records_supplied_corpus"]); put("RecDB", idf["records_databases_total"])
put("RecIdent", idf["records_supplied_corpus"] + idf["records_databases_total"])
for k, v in idf["records_by_database"].items():
    put("RecDB" + alpha(k), v)
put("Dup", idf["duplicates_removed_total"]); put("Screened", scr["records_screened"])
put("ScrExcluded", scr["records_excluded"]); put("BackgroundPool", scr["of_which_background_pool_EC1"])
put("ScrReviews", scr["excluded_by_reason"].get("EC9", 0))
put("Sought", el["reports_sought_for_retrieval"]); put("NotRetrieved", el["not_retrieved"])
put("Assessed", el["fulltext_assessed"]); put("FtExcluded", el["fulltext_excluded"])
put("Included", inc["studies"]); put("Reports", inc["reports"])
put("AddReports", el["fulltext_additional_reports_of_included_studies"] + (P.get("other_methods") or {}).get("additional_reports", 0))
put("N", N)
om = P.get("other_methods") or {}
if om:   # citation searching and update search (Phase 8)
    put("CitRecords", om["records_identified"]); put("CitBackward", om["backward"]); put("CitForward", om["forward"])
    put("CitUpdate", om["update_search"]); put("CitDup", om["duplicates_removed"])
    put("CitDupScreened", om["duplicates_already_screened"]); put("CitKeyword", om["removed_by_automation_keyword_filter"])
    put("CitScreened", om["records_screened"]); put("CitScrExcluded", om["records_excluded"])
    put("CitDupAtScreening", om["duplicates_found_at_screening"]); put("CitBackground", om["of_which_background_pool_EC1"])
    put("CitSought", om["reports_sought"]); put("CitNotRetrieved", om["not_retrieved"]); put("CitAssessed", om["assessed"])
    put("CitFtExcluded", om["excluded"]); put("CitIncluded", om["studies_included"]); put("CitAddReports", om["additional_reports"])
    put("DbIncluded", inc["studies_databases"])
    put("SoughtAll", el["reports_sought_for_retrieval"] + om["reports_sought"])
    put("CitReviews", om["screening_excluded_by_reason"].get("EC9", 0))
    put("ScrReviewsAll", scr["excluded_by_reason"].get("EC9", 0) + om["screening_excluded_by_reason"].get("EC9", 0))
    put("NotRetrievedAll", el["not_retrieved"] + om["not_retrieved"])
    u2 = P.get("update_search_2") or {}
    if u2:   # second update search (2026-11-13), part of the other-methods column
        put("UpdTwoRecords", u2["records_identified"]); put("UpdTwoDup", u2["duplicates_removed"])
        put("UpdTwoKeyword", u2["removed_by_automation_keyword_filter"]); put("UpdTwoScreened", u2["records_screened"])
        put("UpdTwoScrExcluded", u2["records_excluded"]); put("UpdTwoSought", u2["reports_sought"])
        put("UpdTwoNotRetrieved", u2["not_retrieved"]); put("UpdTwoAssessed", u2["assessed"])
        put("UpdTwoFtExcluded", u2["excluded"]); put("UpdTwoIncluded", u2["studies_included"])
    put("CitOnlyIncluded", om["studies_included"] - (u2.get("studies_included", 0) if u2 else 0))

# ---------------------------------------------------------------- corpus profile
np_("YrRecent", cnt(lambda r: r["_year"] >= 2025)); np_("YrMid", cnt(lambda r: 2023 <= r["_year"] <= 2024))
np_("YrEarly", cnt(lambda r: r["_year"] <= 2020))
put("YrFirst", min(r["_year"] for r in R))
for t in ("journal", "conference", "preprint"):
    np_("Pub" + t.capitalize(), cnt(lambda r, t=t: r["pub_type"] == t))
cc = Counter(r["country"] for r in R)
for c in ("China", "USA", "Germany", "Singapore"):
    np_("Ctry" + c, cc[c])
put("CtryCount", len([c for c in cc if c != "NR"]))

# ---------------------------------------------------------------- quality
tot = sorted(int(r["qa_total"]) for r in R)
put("QAMean", f"{sum(tot) / N:.1f}"); put("QAMedian", tot[N // 2])
band = Counter(r["qa_band"] for r in R)
for b in ("High", "Medium", "Low"):
    np_("QA" + b, band[b])
for i in range(1, 13):
    put("QAQ" + alpha(str(i)) + "Mean", f"{sum(int(r[f'Q{i}']) for r in R) / N:.2f}")
for t in ("journal", "conference", "preprint"):
    v = [int(r["qa_total"]) for r in R if r["pub_type"] == t]
    put("QA" + t.capitalize(), f"{sum(v) / len(v):.1f}")

# ---------------------------------------------------------------- retrieval rounds (access check)
grp = {}
for f in sorted(glob.glob(str(S.W / "extraction" / "raw" / "batch*.txt"))):
    n = int(re.search(r"batch(\d+)", f).group(1))
    g = "OA" if n <= 10 else ("IEEE" if n <= 19 else ("RTwo" if n <= 24 else "Cit"))
    for line in open(f):
        if line.startswith("@@ "):
            sid = line[3:].strip()
            grp[sid] = "Upd" if sid.startswith("E") else g      # second update search: not a retrieval round
for g in ("OA", "IEEE", "RTwo", "Cit"):
    rs = [r for r in R if grp.get(r["study_id"]) == g]
    put("Grp" + g + "N", len(rs))
    put("Grp" + g + "LThreeP", f"{S.pct(cnt(S.l3plus, rs), len(rs)):.1f}")
    put("Grp" + g + "PhysP", f"{S.pct(cnt(lambda r: r['_physical'], rs), len(rs)):.1f}")
    put("Grp" + g + "CodeP", f"{S.pct(cnt(lambda r: r['code'] == 'Y', rs), len(rs)):.1f}")

# human consistency checks (scripts/30_consistency_kappa.py)
CJ = S.W / "logs" / "consistency" / "consistency_results.json"
if CJ.exists():
    import json as _json
    C = _json.load(open(CJ))
    for k, name in (("screen_frame", "ConsFrame"), ("screen_sampled", "ConsSample"), ("screen_decided", "ConsDecided"),
                    ("screen_agree_fwd_pct", "ConsAgreeFwd"), ("screen_kappa_fwd", "ConsKappaFwd"),
                    ("screen_agree_4_pct", "ConsAgreeFour"), ("screen_kappa_4", "ConsKappaFour"),
                    ("screen_disagreements", "ConsDisagree"), ("screen_undecided", "ConsUndecided"),
                    ("rec_upheld_exclusions", "ConsUpheldExcl"), ("rec_upheld_forwarded", "ConsUpheldFwd"),
                    ("rec_changed", "ConsChanged")):
        if C.get(k) is not None:
            put(name, C[k])

# most frequent outlets (from analysis/tables/venue_top.csv, written by 15_stats.py)
VEN = {r["code"]: int(r["studies"]) for r in csv.DictReader(open(S.W / "analysis" / "tables" / "venue_top.csv"))}
for code, name in (("IEEE Transactions on Intelligent Transportation Systems", "TITS"), ("arXiv", "Arxiv"),
                   ("IEEE Intelligent Transportation Systems Conference (ITSC)", "ITSC"),
                   ("IEEE Transactions on Vehicular Technology", "TVT"), ("IEEE Intelligent Vehicles Symposium", "IV"),
                   ("IEEE Transactions on Intelligent Vehicles", "TIV")):
    put("Ven" + name, VEN.get(code, 0))

# database-search vs citation-search studies (search-scope effect)
for g, rs in (("Db", [r for r in R if r["study_id"][0] != "C"]), ("Cit", [r for r in R if r["study_id"][0] == "C"])):
    put("Scope" + g + "N", len(rs))
    put("Scope" + g + "LOneP", f"{S.pct(cnt(lambda r: r['safety_level'] in ('L0', 'L1'), rs), len(rs)):.1f}")
    put("Scope" + g + "LThreeP", f"{S.pct(cnt(S.l3plus, rs), len(rs)):.1f}")
    put("Scope" + g + "CmdpP", f"{S.pct(cnt(lambda r: 'B' in r['_mech'], rs), len(rs)):.1f}")
    put("Scope" + g + "SafeTitleN", cnt(lambda r: bool(re.search(
        r"safe (reinforcement|rl|policy|learning|exploration|deep)|constrained (reinforcement|policy|markov|rl)|"
        r"safety[- ](aware|constrained|guaranteed|critical) (reinforcement|rl|deep|policy)", r["title"], re.I)), rs))
    put("Scope" + g + "LFourP", f"{S.pct(cnt(lambda r: r['safety_level'] in ('L4', 'L5'), rs), len(rs)):.1f}")

# ---------------------------------------------------------------- sensitivity (ranges across subsets)
QUEST = S._ns["QUESTIONABLE"]
subsets = [R, [r for r in R if r["study_id"] not in QUEST], [r for r in R if r["qa_band"] != "Low"],
           [r for r in R if r["pub_type"] != "preprint"], [r for r in R if r["qa_band"] == "High"]]
def rng(f, name):
    v = [S.pct(cnt(f, s), len(s)) for s in subsets]
    put(name + "Min", f"{min(v):.1f}"); put(name + "Max", f"{max(v):.1f}")
rng(lambda r: not r["_physical"], "SensSim"); rng(S.l3plus, "SensLThree"); rng(lambda r: r["code"] == "Y", "SensCode")
hi = subsets[-1]
put("SensHighN", len(hi))
put("SensHighNoGenP", f"{S.pct(cnt(lambda r: r['generalization'] in ('NONE', ''), hi), len(hi)):.1f}")
put("SensHighNoUncP", f"{S.pct(cnt(lambda r: r['uncertainty'] == 'NONE', hi), len(hi)):.1f}")
put("SensHighEmpOnlyP", f"{S.pct(cnt(lambda r: S.split(r['safety_claim']) == ['EMP'], hi), len(hi)):.1f}")

# ---------------------------------------------------------------- mechanisms
nm = Counter(len(r["_mech"]) for r in R)
np_("MechSingle", nm[1]); np_("MechMulti", N - nm[1])
for c in S.CLUSTERS:
    np_("Cl" + alpha(c.split(" ")[0]), cnt(lambda r, c=c: c in r["_clusters"]))
for m in "ABCDEFGHIJKLNOPQRSTUVWX":
    rs = [r for r in R if S.has(r, m)]
    put("Mech" + m + "N", len(rs))
    put("Mech" + m + "P", f"{S.pct(len(rs), N):.1f}")
    put("Mech" + m + "LThreeP", f"{S.pct(cnt(S.l3plus, rs), len(rs)):.1f}")
    put("Mech" + m + "LFourP", f"{S.pct(cnt(S.l4plus, rs), len(rs)):.1f}")
    put("Mech" + m + "LThreeN", cnt(S.l3plus, rs))
    put("Mech" + m + "LFourN", cnt(S.l4plus, rs))
    put("Mech" + m + "EmpOnlyP", f"{S.pct(cnt(lambda r: S.split(r['safety_claim']) == ['EMP'], rs), len(rs)):.1f}")
    put("Mech" + m + "Phys", cnt(lambda r: r["_physical"], rs))
    put("Mech" + m + "LFive", cnt(lambda r: r["safety_level"] == "L5", rs))
    q = sorted(int(r["qa_total"]) for r in rs)
    put("Mech" + m + "QAMedian", q[len(q) // 2])
np_("SafetyCost", cnt(lambda r: r["safety_cost"] not in ("NA", "")))
stage = Counter(r["mech_stage"] for r in R)
for k in ("TRAIN", "EXEC", "BOTH"):
    np_("Stage" + k.capitalize(), stage[k])

# ---------------------------------------------------------------- algorithms and paradigms
par = Counter(x for r in R for x in S.split(r["rl_paradigm"]))
for k, nmn in (("MF", "MF"), ("HRL", "HRL"), ("MB", "MB"), ("IL+RL", "ILRL"), ("LLM+RL", "LLM")):
    np_("Par" + nmn, par[k])
np_("ParOffline", cnt(lambda r: bool({"OFF", "OFF2ON"} & set(S.split(r["rl_paradigm"])))))
FAMN = {"Off-policy actor-critic": "OffPol", "Value-based": "Value", "On-policy policy gradient": "OnPol",
        "Constrained policy optimisation": "ConPol", "Model-based RL": "ModelBased", "Offline RL": "OfflineFam",
        "Generic actor-critic": "GenericAC", "Other / unspecified": "OtherFam"}
for f, nmn in FAMN.items():
    np_("Fam" + nmn, cnt(lambda r, f=f: f in r["_fam"]))
alg = Counter(a for r in R for a in r["_alg"])
for a, nmn in (("PPO", "PPO"), ("SAC", "SAC"), ("DQN", "DQN"), ("DDPG", "DDPG"), ("TD3", "TDThree"),
               ("Double DQN", "DDQN"), ("SAC-Lagrangian", "SACLag"), ("PPO-Lagrangian", "PPOLag"),
               ("Dueling double DQN", "DDDQN"), ("CPO", "CPO")):
    np_("Alg" + nmn, alg[a])
np_("Lag", cnt(lambda r: r["_lag"]))
np_("AnyConstr", cnt(lambda r: r["_lag"] or S.has(r, "B") or "Constrained policy optimisation" in r["_fam"]))
net = Counter(x for r in R for x in S.split(r["network"]))
obs = Counter(x for r in R for x in S.split(r["obs_type"]))
np_("NetMLP", net["MLP"]); np_("ObsVEC", obs["VEC"]); np_("ObsIMG", obs["IMG"]); np_("ObsBEV", obs["BEV"])
np_("ObsLIDAR", obs["LIDAR"])
al = Counter(r["action_level"] for r in R)
for k in ("CTRL", "BEHAV", "TRAJ", "PARAM"):
    np_("Act" + k.capitalize(), al[k])

# ---------------------------------------------------------------- integration (§17)
ro = Counter(r["rl_output"] for r in R); si = Counter(r["safety_integration"] for r in R)
for k in ("ACT", "DEC", "TRAJ", "PARAM", "RES"):
    np_("Out" + k.capitalize(), ro[k])
for k in ("NONE", "FILTER", "CORRECT", "EMBED", "MASK"):
    np_("Int" + k.capitalize(), si[k])
role = Counter(x for r in R for x in S.split(r["rl_role_s17"]) if x)
xt = Counter((r["rl_output"], r["safety_integration"]) for r in R)
put("XActFilter", xt[("ACT", "FILTER")]); put("XActCorrect", xt[("ACT", "CORRECT")])
put("XDecMask", xt[("DEC", "MASK")]); put("XDecCorrEmb", xt[("DEC", "CORRECT")] + xt[("DEC", "EMBED")])
put("XParamEmbed", xt[("PARAM", "EMBED")])
ctl = Counter(x for r in R for x in S.split(r["control"]))
np_("CtlMPC", ctl["MPC"]); np_("CtlQP", ctl["QP"])
np_("AnyCert", cnt(lambda r: any(S.has(r, m) for m in "FGHIJ")))
np_("RoleAction", cnt(lambda r: r["rl_output"] in ("ACT", "RES")))
np_("RoleDecision", cnt(lambda r: r["rl_output"] in ("DEC", "TRAJ")))

# ---------------------------------------------------------------- evidence levels and claims
lv = Counter(r["safety_level"] for r in R)
for l in S.LEVELS:
    np_("Lev" + alpha(l), lv[l])
np_("LevThreePlus", cnt(S.l3plus)); np_("LevFourPlus", cnt(S.l4plus))
claim = lambda c: cnt(lambda r: c in S.split(r["safety_claim"]))
np_("ClaimEmp", claim("EMP")); np_("ClaimEmpOnly", cnt(lambda r: S.split(r["safety_claim"]) == ["EMP"]))
np_("ClaimFormalProb", cnt(lambda r: bool({"FORMAL", "PROB"} & set(S.split(r["safety_claim"])))))
for c in ("STAT", "PROB", "CEXP", "ROB", "RT", "FORMAL"):
    np_("Claim" + c.capitalize(), claim(c))
nsm = Counter(len(r["_safety_metrics"]) for r in R)
np_("SafeMetNone", nsm[0]); np_("SafeMetOne", nsm[1]); np_("SafeMetAtMostOne", nsm[0] + nsm[1])
np_("SafeMetAny", N - nsm[0])
np_("CollOnly", cnt(lambda r: r["_safety_metrics"] == ["COLL"]))
met = Counter(x for r in R for x in S.split(r["metrics"]))
for k in ("COLL", "SUCC", "REW", "TTC", "PET", "RISK", "VIOL", "INTERV", "COMF", "JERK"):
    np_("Met" + k.capitalize(), met[k])
np_("MetTTCPET", cnt(lambda r: bool({"TTC", "PET"} & set(S.split(r["metrics"])))))
st = Counter(r["stats"] for r in R)
np_("StatsFull", st["Y"]); np_("StatsPartial", st["P"]); np_("StatsNone", st["N"])
l4 = [r for r in R if r["safety_level"] == "L4"]
put("LFourSimN", cnt(lambda r: not r["_physical"], l4))
np_("LFourLow", cnt(lambda r: r["validation_tier"] == "SIM-LOW", l4), len(l4))
phys = [r for r in R if r["_physical"]]
np_("Phys", len(phys)); np_("SimOnly", N - len(phys))
for l in S.LEVELS:
    put("Phys" + alpha(l), cnt(lambda r, l=l: r["safety_level"] == l, phys))
put("PhysNotLFive", cnt(lambda r: r["safety_level"] != "L5", phys))
tier = Counter(r["validation_tier"] for r in R)
for k, nmn in (("SIM-LOW", "SimLow"), ("SIM-HIFI", "SimHifi"), ("SIM-DATA", "SimData"), ("HIL", "HIL"),
               ("SCALED", "Scaled"), ("CLOSED", "Closed"), ("ROAD", "Road")):
    np_("Tier" + nmn, tier[k])

# ---------------------------------------------------------------- assumptions (L3-L5)
sub = [r for r in R if S.l3plus(r)]
stated = [r for r in sub if r["guarantee_assumptions"] not in ("NA", "")]
put("AsmBaseN", len(sub)); put("AsmStatedN", len(stated))
ASN = {"known or accurate dynamics model": "Model", "predictable other road users": "Others",
       "perfect perception or state": "Perception", "optimisation feasibility": "Feasible",
       "bounded disturbance or error": "Bounded", "reliable communication": "Comm",
       "correct learned component or rule set": "Learned"}
for t, nmn in ASN.items():
    np_("Asm" + nmn, cnt(lambda r, t=t: bool(re.search(S.ASSUME[t], r["guarantee_assumptions"], re.I)), stated),
        len(stated))

# ---------------------------------------------------------------- applications
for t in S.TASK:
    rs = [r for r in R if t in S.split(r["task"])]
    np_("Task" + alpha(t.capitalize()), len(rs))
    put("Task" + alpha(t.capitalize()) + "LFourN", cnt(lambda r: r["safety_level"] == "L4", rs))
    put("Task" + alpha(t.capitalize()) + "LFourPlusN", cnt(S.l4plus, rs))
    put("Task" + alpha(t.capitalize()) + "LThreePlusN", cnt(S.l3plus, rs))
    put("Task" + alpha(t.capitalize()) + "MTwoN", cnt(lambda r: "M2 Run-time intervention" in r["_clusters"], rs))
    put("Task" + alpha(t.capitalize()) + "MOneN", cnt(lambda r: "M1 Objective shaping" in r["_clusters"], rs))
sc = Counter(x for r in R for x in S.split(r["scenario"]))
for k in ("HWY", "URB", "INTX", "RAMP"):
    np_("Scen" + k.capitalize(), sc[k])
tr = Counter(r["traffic"] for r in R)
for k in ("SCRIPTED", "LEARNED", "HUMAN", "MIXED", "REPLAY", "NONE"):
    np_("Traf" + k.capitalize(), tr[k])
np_("TrafReactive", tr["LEARNED"] + tr["HUMAN"])
ma = [r for r in R if r["agents"] != "SA"]
np_("MultiAgent", len(ma)); put("MultiAgentPhys", cnt(lambda r: r["_physical"], ma))
ag = Counter(r["agents"] for r in R)
for k, nmn in (("MA-CEN", "Cen"), ("MA-CTDE", "CTDE"), ("MA-DEC", "Dec")):
    np_("Ag" + nmn, ag[k])

# ---------------------------------------------------------------- environments, generalisation, uncertainty, stack
sims = Counter(x for r in R for x in S.split(r["simulator"]))
for k, nmn in (("CUSTOM", "Custom"), ("CARLA", "CARLA"), ("HWENV", "HWEnv"), ("SUMO", "SUMO"),
               ("SIMULINK", "Simulink"), ("METADRIVE", "MetaDrive"), ("CARSIM", "CarSim"), ("SAFETYGYM", "SafetyGym")):
    np_("Sim" + nmn, sims[k])
put("SimDistinct", len(sims))
ds = Counter(x for r in R for x in S.split(r["dataset"]))
np_("DataAny", cnt(lambda r: any(x != "NONE" for x in S.split(r["dataset"]))))
put("DataNGSIM", ds["NGSIM"]); put("DataHighD", ds["HIGHD"]); put("DataOwn", ds["OWN"])
gen = Counter(x for r in R for x in S.split(r["generalization"]))
np_("GenNone", gen["NONE"]); np_("GenAny", N - gen["NONE"])
for k in ("DENS", "UNSEEN", "GEOM", "DIST", "AGENTS", "S2R", "DOMAIN", "DYN", "WEATHER"):
    np_("Gen" + alpha(k.capitalize()), gen[k])
un = Counter(x for r in R for x in S.split(r["uncertainty"]))
np_("UncNone", un["NONE"]); np_("UncAny", N - un["NONE"])
for k in ("STOCH", "INTENT", "MODEL", "SENS", "DSHIFT", "PO", "PRED", "EPI", "DIST", "ADV", "ALE"):
    np_("Unc" + k.capitalize(), un[k])
np_("UncExplicit", cnt(lambda r: bool({"EPI", "ALE"} & set(S.split(r["uncertainty"])))))
stk = Counter(x for r in R for x in S.split(r["stack"]))
for k in ("PERC", "PRED", "PLAN", "DEC", "CTRL", "SUPERV", "RTA"):
    np_("Stack" + k.capitalize(), stk[k])
xai = {r["study_id"]: r["explainability"] for r in csv.DictReader(open(S.W / "extraction" / "xai_codes.csv"))}
np_("XaiVis", cnt(lambda r: xai.get(r["study_id"]) == "VIS")); np_("XaiDesign", cnt(lambda r: xai.get(r["study_id"]) == "DESIGN"))

# ---------------------------------------------------------------- reproducibility and baselines
np_("Code", cnt(lambda r: r["code"] == "Y")); np_("Data", cnt(lambda r: r["data_avail"] == "Y"))
np_("HypFull", cnt(lambda r: r["hyperparams"] == "Y")); np_("HypPart", cnt(lambda r: r["hyperparams"] == "P"))
np_("Seeds", cnt(lambda r: r["seeds"] not in ("NR", "NA", ""))); np_("Compute", cnt(lambda r: r["compute"] == "Y"))
np_("Protocol", cnt(lambda r: r["eval_protocol"] == "Y"))
bt = Counter(x for r in R for x in S.split(r["baseline_types"]))
for k in ("NSRL", "SRL", "CLASS", "ABL", "HUMAN", "NONE"):
    np_("Base" + k.capitalize(), bt[k])

# ---------------------------------------------------------------- trends by period
PN = ["One", "Two", "Three", "Four"]
for (lab, _, _), pn in zip(S.PERIODS, PN):
    rs = [r for r in R if r["_period"] == lab]
    put("Per" + pn + "N", len(rs))
    f = lambda g: f"{S.pct(cnt(g, rs), len(rs)):.1f}"
    put("Per" + pn + "ShieldP", f(lambda r: any(S.has(r, m) for m in "DES")))
    put("Per" + pn + "FormalP", f(lambda r: S.has(r, "T")))
    put("Per" + pn + "RobustP", f(lambda r: any(S.has(r, m) for m in "KLMN")))
    put("Per" + pn + "ConsP", f(lambda r: S.has(r, "B")))
    put("Per" + pn + "CBFP", f(lambda r: any(S.has(r, m) for m in "FGH")))
    put("Per" + pn + "MPCP", f(lambda r: S.has(r, "I")))
    put("Per" + pn + "MAP", f(lambda r: r["agents"] != "SA"))
    put("Per" + pn + "ModelBasedP", f(lambda r: S.has(r, "Q")))
    put("Per" + pn + "OfflineP", f(lambda r: S.has(r, "P")))
    put("Per" + pn + "HitlP", f(lambda r: S.has(r, "V")))
    put("Per" + pn + "FMN", cnt(lambda r: S.has(r, "X"), rs)); put("Per" + pn + "FMP", f(lambda r: S.has(r, "X")))
    put("Per" + pn + "LThreeP", f(S.l3plus))
    put("Per" + pn + "PhysP", f(lambda r: r["_physical"]))
    put("Per" + pn + "CodeP", f(lambda r: r["code"] == "Y"))
    put("Per" + pn + "QA", f"{sum(int(r['qa_total']) for r in rs) / len(rs):.1f}")

# ---------------------------------------------------------------- deployment-readiness chain
rd = Counter(S.readiness(r) for r in R)
for k in S.READINESS:
    np_("Rdy" + alpha(k), rd[k])
np_("RdyMediumPlus", rd["Medium"] + rd["Medium-High"] + rd["High"])
gi = Counter(S.guarantee_index(r) for r in R)
np_("GuarRuntimePlus", gi[3] + gi[4])
FAMS = {"Reward shaping": "Reward", "Constrained RL / safety critic": "Constrained", "Risk-sensitive RL": "Risk",
        "Shield, mask or rule-based intervention": "Shield", "Safety filter": "Filter", "Runtime assurance": "RTA",
        "Barrier / Lyapunov certificate (CBF, CLF, CBF-CLF-QP)": "Barrier", "MPC hybrid": "MPC",
        "Reachability / formal verification": "Formal", "Robust / uncertainty-aware RL": "Robust",
        "Learning-paradigm extension": "Paradigm"}
for f, nmn in FAMS.items():
    rs = [r for r in R if S.mech_family(r) == f]
    put("Fam" + nmn + "Size", len(rs))
    put("Fam" + nmn + "GThreeP", f"{S.pct(cnt(lambda r: S.guarantee_index(r) >= 3, rs), len(rs)):.1f}")
    put("Fam" + nmn + "MedPlusP", f"{S.pct(cnt(lambda r: S.readiness(r) in ('Medium', 'Medium-High', 'High'), rs), len(rs)):.1f}")
    put("Fam" + nmn + "MedPlusN", cnt(lambda r: S.readiness(r) in ("Medium", "Medium-High", "High"), rs))
    put("Fam" + nmn + "SimOnlyP", f"{S.pct(cnt(lambda r: not r['_physical'], rs), len(rs)):.1f}")
for t in S.TASK:
    rs = [r for r in R if t in S.split(r["task"])]
    put("Task" + alpha(t.capitalize()) + "MedPlusN", cnt(lambda r: S.readiness(r) in ("Medium", "Medium-High", "High"), rs))
gsim = [r for r in R if S.guarantee_index(r) >= 3]
np_("GuarRuntimeSimOnly", cnt(lambda r: not r["_physical"], gsim), len(gsim))
weak_phys = [r for r in R if r["_physical"] and S.guarantee_index(r) <= 2]
put("PhysWeakGuarN", len(weak_phys))

# ---------------------------------------------------------------- pre-submission review checks (17 Nov 2026)
# Evidence levels are partly definitional: L3+ needs a run-time or certificate mechanism. How many studies that use
# such a mechanism do NOT reach L3, and why (mechanism acting only during training)?
RTM = set("DESWFGHIJT")
rtm = [r for r in R if RTM & set(r["_mech"])]
rtm_low = [r for r in rtm if not S.l3plus(r)]
put("RtMechN", len(rtm))
np_("LThreePlus", cnt(S.l3plus), len(R))
np_("RtMechBelow", len(rtm_low), len(rtm))
put("RtMechBelowTrainN", cnt(lambda r: r["mech_stage"] == "TRAIN", rtm_low))
put("NoRtMechLThreeN", cnt(lambda r: S.l3plus(r), [r for r in R if not RTM & set(r["_mech"])]))
# Citation-search keyword filter, tested on the database-search and seed inclusions (which it did not influence)
_RL = re.compile(r"reinforcement learning|\bRL\b|policy optimi[sz]ation|actor-critic|q-learning|\bDQN\b|\bPPO\b|\bSAC\b", re.I)
_SAFE = re.compile(r"safe|safety|constrain|risk|shield|barrier|lyapunov|collision|reachab|verif|runtime assurance", re.I)
_VEH = re.compile(r"vehicle|driving|driver|self-driving|car\b|cars\b|lane|merging|intersection|platoon|cruise control|"
                  r"racing|parking|traffic|automated driving|autonomous driving", re.I)
_ab = {}
for _f in ("stageA/stageA_inventory.csv", "stageB/records_unique.csv", "stageC/records.csv", "stageE/records.csv"):
    for _r in csv.DictReader(open(S.W / _f)):
        _ab.setdefault(_r["study_id"], (_r.get("title") or "") + " " + (_r.get("abstract") or ""))
_db = [r for r in R if r["study_id"][0] in "AB"]
# The filter reads abstracts, which the public release does not redistribute: the per-study result is stored in
# manuscript/generated/keyword_filter_check.csv when abstracts are available and read back from there otherwise.
_kf = S.W / "manuscript" / "generated" / "keyword_filter_check.csv"
_have_abs = any(len(v.split()) > 40 for v in _ab.values())
if _have_abs or not _kf.exists():
    _pass = {r["study_id"]: bool(_RL.search(_ab[r["study_id"]]) and _SAFE.search(_ab[r["study_id"]]) and _VEH.search(_ab[r["study_id"]]))
             for r in _db}
    with open(_kf, "w", newline="") as _fo:
        _w = csv.writer(_fo); _w.writerow(["study_id", "passes_keyword_filter"])
        _w.writerows([k, int(v)] for k, v in sorted(_pass.items()))
else:
    _pass = {x["study_id"]: x["passes_keyword_filter"] == "1" for x in csv.DictReader(open(_kf))}
_fail = [r for r in _db if not _pass[r["study_id"]]]
np_("FiltLost", len(_fail), len(_db))
put("FiltDbN", len(_db))
np_("DbShare", len(_db), len(R))
# Sensitivity of the quality bands: stricter high band (>= 20)
_hi = [r for r in R if int(r["qa_total"]) >= 20]
np_("QAStrictHigh", len(_hi), len(R))
put("QAStrictSimP", f"{S.pct(cnt(lambda r: not r['_physical'], _hi), len(_hi)):.1f}")
put("QAStrictLThreeP", f"{S.pct(cnt(S.l3plus, _hi), len(_hi)):.1f}")
# Cochran-Armitage trend tests across the four periods (two-sided p)
import math as _m
def _trend(f):
    ns = [[r for r in R if a <= int(r["year"]) <= b] for _, a, b in S.PERIODS]
    xs = [cnt(f, g) for g in ns]; ns = [len(g) for g in ns]; Nn = sum(ns); pb = sum(xs) / Nn
    T = sum(i * (x - n * pb) for i, (x, n) in enumerate(zip(xs, ns)))
    V = pb * (1 - pb) * (sum(n * i * i for i, n in enumerate(ns)) - sum(n * i for i, n in enumerate(ns)) ** 2 / Nn)
    pv = _m.erfc(abs(T / _m.sqrt(V)) / _m.sqrt(2))
    return "<0.001" if pv < 0.001 else f"{pv:.2f}"
put("TrendCodeP", _trend(lambda r: r["code"] == "Y"))
put("TrendLThreeP", _trend(S.l3plus))
put("TrendPhysP", _trend(lambda r: bool(r["_physical"])))
put("TrendFormalP", _trend(lambda r: S.has(r, "T")))

# ---------------------------------------------------------------- write and splice
body = "% generated by scripts/21_text_numbers.py -- do not edit\n" + "".join(
    f"\\newcommand{{\\n{k}}}{{{S.us_spelling(str(v))}}}\n" for k, v in sorted(M.items()))
(S.W / "manuscript" / "generated" / "text_numbers.tex").write_text(body)
main = S.W / "manuscript" / "main.tex"
tex = main.read_text()
b, e = "%% BEGIN GENERATED text_numbers", "%% END GENERATED text_numbers"
if b not in tex:
    tex = tex.replace("\\raggedbottom", f"{b}\n{e}\n\n\\raggedbottom", 1)
tex = re.sub(re.escape(b) + r".*?" + re.escape(e), lambda m: f"{b}\n{body}{e}", tex, flags=re.S)
main.write_text(tex)
print(f"wrote {len(M)} macros")
