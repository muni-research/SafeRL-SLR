# Extraction codebook (v1.3, 2026-10-07)

This codebook governs Phase 4. It defines every field of `extraction/evidence_db.xlsx`, the allowed
values (controlled vocabularies), and the decision rules for borderline cases. It implements
CLAUDE.md §15 (fields), §16 (taxonomy), §17 (safety–control integration), §25–26 (safety evidence),
§28 (AV safety stack), RQ6 (uncertainty), RQ11 (validation tier) and RQ12 (reproducibility).

**Unit of extraction:** one *study* (FI in `fulltext/fulltext_decisions.csv`). When a study has
additional reports (FD links), extract from the most complete report and add anything that only
appears in the other report; record the linked IDs in `linked_reports`.

**General rules**
1. Extract **what the paper reports**, not what the reviewer infers. Reviewer judgments are
   restricted to the fields marked *(judgment)* and are always accompanied by a note.
2. Multi-valued fields use `;` as separator and only codes from the vocabulary. A value outside
   the vocabulary is written `OTHER:<text>` and reviewed when the codebook is revised.
3. `NR` = not reported. `NA` = not applicable. Never leave a field silently empty.
4. Free-text fields are short (≤ 40 words), paraphrased, never copied sentences.
5. Numbers in `results` are copied as reported, with the metric and comparison ("collision rate
   0% vs 12% for PPO, 100 test episodes"). They are not re-computed or pooled.

---

## 1. Bibliographic fields (filled by script from the inventories)
`study_id`, `title`, `authors`, `year`, `venue`, `doi`, `pub_type` (journal / conference /
preprint / other), `linked_reports`.

## 2. Context fields
| Field | Content |
|---|---|
| `country` | Country of the first author's first affiliation (from the PDF). `NR` if absent. |
| `problem` | The research problem in one sentence. |

## 3. Application fields (RQ4, §18)
**`task`** (multi), the driving task(s) for which the policy is trained and evaluated:

| Code | Meaning |
|---|---|
| LK | lane keeping / lane following / path tracking |
| LC | lane changing |
| MERGE | on-ramp merging, lane-drop, zipper merge |
| OVT | overtaking |
| CF | car-following, adaptive cruise control, longitudinal speed control |
| INT | intersection crossing (signalised or unsignalised) |
| RAB | roundabout |
| CA | collision avoidance as the stated main task (incl. obstacle/pedestrian avoidance) |
| EMG | emergency maneuver (emergency braking, evasive steering) |
| PED | pedestrian / vulnerable-road-user interaction |
| NAV | general navigation / route following (urban or multi-scenario driving) |
| MP | motion or trajectory planning (continuous trajectory output) |
| TD | tactical decision making (discrete behavior selection) |
| PLT | platooning |
| COOP | cooperative driving among CAVs (other than platooning) |
| RACE | autonomous racing |
| PARK | parking |
| E2E | end-to-end driving from raw sensors |
| OTHER:… | anything else |

**`scenario`** (multi): HWY highway/motorway · URB urban streets · INTX intersection area ·
RAMP ramp/merge area · RAB roundabout · RURAL rural/curvy road · TRACK racetrack/test track ·
PARKLOT · MIXED several scenario types · GENERIC (abstract road, no specific geometry).

**`traffic`**: NONE (no other road users) · SCRIPTED (rule-based/IDM/simulator autopilot) ·
REPLAY (logged trajectories) · LEARNED (other agents learn) · HUMAN (human drivers in loop) ·
MIXED (CAVs + human-driven vehicles modeled explicitly).

## 4. RL fields (RQ3)
| Field | Values |
|---|---|
| `rl_paradigm` (multi) | MF model-free · MB model-based (learned or known model used for learning/planning) · OFF offline · OFF2ON offline-to-online · IL+RL imitation/demonstration-assisted RL · HRL hierarchical · META meta/transfer RL · LLM+RL foundation-model-assisted RL |
| `agents` | SA single learning agent · MA-CEN centralized multi-agent · MA-CTDE centralized training/decentralized execution · MA-DEC fully decentralized |
| `n_agents` | number of learning agents (integer or range), `1` for SA |
| `algorithm` (multi) | Base algorithm names as used by the paper, normalized: QL, DQN, DDQN, DuelingDQN, D3QN, RainbowDQN, PER-DQN, DRQN, PPO, TRPO, A2C, A3C, SAC, TD3, DDPG, REINFORCE, AC (generic actor-critic), CPO, PPO-Lag, TRPO-Lag, SAC-Lag, TD3-Lag, DDPG-Lag, PCPO, FOCOPS, CUP, P3O, RCPO, WCSAC, MAPPO, MADDPG, IPPO, QMIX, MAAC, BCQ, CQL, IQL, BC, DT (decision transformer), MBPO, Dreamer, MCTS, OTHER:… — the paper's own method is recorded by its base algorithm (e.g. a new Lagrangian SAC → SAC-Lag) and its name goes in `method_name`. |
| `method_name` | Name of the proposed method, or `NR` |
| `network` (multi) | MLP · CNN · RNN (LSTM/GRU) · GNN · ATT (attention/transformer) · RBF (radial-basis/linear-in-parameter approximators, typical of ADP) · NR |
| `obs_type` (multi) | VEC (state vector / kinematic features) · IMG (camera) · BEV (bird's-eye raster) · LIDAR · GRAPH · OCC (occupancy grid) · LANG (text/LLM input) |
| `action_type` | DISC · CONT · HYB |
| `action_level` | CTRL (steering/throttle/brake/acceleration) · TRAJ (trajectory or waypoints) · BEHAV (discrete behavior/meta-action) · PARAM (controller or planner parameters) · MIXED |
| `reward` | short description of the reward terms |
| `safety_cost` | short description of the cost signal, or `NA` if no separate cost |
| `constraints` | the explicit constraints (e.g. "E[cost] ≤ d", "TTC ≥ 2 s", "CBF h(x) ≥ 0") or `NA` |

## 5. Safety fields (RQ2, RQ5, §16–17, §25–26)
**`mech`** (multi): taxonomy categories (CLAUDE.md §16), extended with W and X:

| Code | Category | Assign when |
|---|---|---|
| A | safety-aware reward design | safety enters only (or mainly) through reward terms designed for safety |
| B | constrained RL | CMDP with Lagrangian, trust-region, projection, penalty-function or primal-dual solution |
| C | safety critic | a learned cost/risk value function used to guide or restrict actions |
| D | action shielding / masking | unsafe actions are removed or replaced *before* execution by a discrete check (shield, action mask) |
| E | safety filter / safety layer | the RL action is minimally modified (projection, QP) to a safe action |
| F | CBF-based | a control barrier function (incl. HOCBF, learned CBF) is used |
| G | CLF / Lyapunov-based | a Lyapunov or control-Lyapunov function constrains learning or actions |
| H | CBF-CLF-QP / optimization layer | a QP/optimization combining CBF/CLF constraints is solved at run time |
| I | MPC–RL hybrid | MPC is part of the control loop (as safety layer, planner, or RL-tuned controller) |
| J | reachability-based | Hamilton–Jacobi or set-based reachability, invariant/viable sets |
| K | robust RL | adversarial training, worst-case / minimax formulations, disturbance rejection |
| L | risk-sensitive RL | CVaR, distributional risk measures, chance constraints, risk-aware objectives |
| M | distributionally robust RL | ambiguity sets over distributions |
| N | uncertainty-aware RL | explicit epistemic/aleatoric uncertainty estimates drive decisions |
| O | multi-agent safe RL | safety is defined/enforced over interacting learning agents |
| P | offline safe RL | safety-constrained learning from fixed datasets |
| Q | model-based safe RL | a learned or known dynamics model is used to predict/ensure safety |
| R | hierarchical safe RL | safety is enforced at one level of a multi-level policy |
| S | runtime assurance / fallback | a monitor switches to a verified/backup controller (simplex-style) |
| T | formal verification / formal specification | temporal-logic specifications, verified shields, certified networks |
| U | sim-to-real safe RL | the safety method is explicitly designed for or tested in transfer to reality |
| V | human-aware safe RL | human guidance, takeover, demonstrations or human driver models used for safety |
| W | rule-based / knowledge-based intervention | hand-crafted traffic rules, expert rules or RSS-type rules override or bound the policy |
| X | foundation-model-assisted | LLM/VLM used for safety reasoning, reward or constraint generation |

Assign every category that is *part of the proposed method*. Baselines do not count. A category
mentioned only in related work is not assigned. U, O and P are assigned only when the safety
mechanism itself addresses transfer, multi-agent interaction or offline data respectively.

**`mech_primary`**: the single category that carries the paper's main safety contribution.

**`mech_stage`**: TRAIN (safety acts only during training, e.g. reward, Lagrangian) · EXEC (acts
only at execution, e.g. a filter added to a trained policy) · BOTH.

**`rl_output`** (§17, what RL produces): ACT low-level control action · DEC high-level decision ·
PARAM parameters of a controller/planner · TRAJ trajectory/waypoints · RES residual on top of a
nominal controller.

**`safety_integration`** (§17, how RL relates to the safety component):
NONE (no run-time safety component; safety only shaped through learning) ·
FILTER (RL action passes through a filter that may minimally modify it) ·
CORRECT (a safety controller overrides or replaces the RL action when triggered, incl. fallback/
switching) · EMBED (RL is embedded inside an optimization-based safety layer, e.g. RL supplies
cost/terminal value/weights to an MPC or QP that is solved at run time) ·
MASK (infeasible actions removed from the RL action set) .

The six §17 categories are then derived as: (1) RL generates control action = `rl_output` ACT/RES;
(2) RL generates high-level decision = DEC; (3) RL provides controller parameters = PARAM;
(4) RL under a safety filter = FILTER or MASK; (5) RL corrected by a safety controller = CORRECT;
(6) RL embedded in optimization layer = EMBED.

**`control`** (multi), classical control components present in the proposed system:
NONE · PID · PP (pure pursuit) · STANLEY · LQR · MPC · QP · IDM · MOBIL · SMC (sliding mode) ·
APF (artificial potential field) · PLANNER (sampling/graph/lattice planner) · BACKSTEP (backstepping) · RULE (rule-based fallback or guidance controller) · OTHER:…

**`safety_claim`** (multi, §25), what kind of safety the paper *claims*:
EMP empirical (fewer collisions in tests) · STAT statistical (confidence bounds, many-episode
statistics with uncertainty) · PROB probabilistic guarantee (chance constraint with proof/bound) ·
CEXP constraint satisfaction in expectation (CMDP) · ROB robustness to stated perturbations ·
FORMAL provable/formal property (forward invariance, verified shield) · RT run-time enforcement ·
CERT reference to standards/certification (ISO 26262, SOTIF/ISO 21448, UL 4600) with evidence.

**`guarantee_assumptions`**: the assumptions the safety claim needs (e.g. "known control-affine
dynamics; perfect state of surrounding vehicles; feasible QP"). `NA` if no guarantee is claimed.

**`safety_level`** *(judgment)*, review-derived safety-evidence level (protocol §7). Assign the
highest level **substantiated** by the paper:

| Level | Requirement |
|---|---|
| L0 | safety is a stated goal but no safety-specific evaluation (only reward/success reported) |
| L1 | safety is evaluated empirically with a safety metric (collisions, TTC, violations), no explicit constraint in the formulation |
| L2 | an explicit safety constraint/cost is part of the optimization (CMDP, chance constraint, risk constraint) and constraint satisfaction is reported |
| L3 | safety is enforced at run time by a mechanism that acts on every action (filter, shield, CBF-QP, fallback) and its effect is evaluated |
| L4 | a formal/provable safety property is stated and proven (or verified), with explicit assumptions |
| L5 | L3/L4 plus evidence oriented to real-world assurance: real-vehicle testing with safety analysis, or explicit alignment with safety standards/scenario-based validation for certification |

If the claimed guarantee relies on assumptions not met in the experiments (e.g. proof for known
dynamics, tested in CARLA with unmodelled dynamics) the level is kept but the mismatch is written
in `level_note`.

**`level_note`**: one sentence justifying the level.

## 6. Uncertainty (RQ6)
**`uncertainty`** (multi): EPI epistemic · ALE aleatoric · SENS sensor/perception noise ·
INTENT other agents' intentions · MODEL dynamics model error · PRED prediction error ·
DSHIFT distribution shift / OOD · PO partial observability (modeled as POMDP or occlusion) ·
STOCH stochastic traffic only · ADV adversarial perturbations · DIST external disturbances
(road friction, wind, actuator delay) · NONE.
Assign a code only if the uncertainty is *modeled or evaluated*, not merely mentioned.

**`uncertainty_method`**: short description (ensembles, Bayesian NN, MC dropout, distributional
critic, robust set, Gaussian process, conformal prediction, belief state…) or `NA`.

## 7. Environment and evaluation (RQ7–RQ9, RQ11)
**`simulator`** (multi): CARLA · SUMO · HWENV (highway-env) · METADRIVE · SMARTS · FLOW ·
TORCS · AIRSIM · LGSVL · CARSIM · PRESCAN · SIMULINK (MATLAB/Simulink, incl. Driving Scenario
Designer) · GAZEBO · WEBOTS · UNITY · NUPLAN · WAYMAX · COMMONROAD · SAFETYGYM (incl. Safety-
Gymnasium) · BULLET · CUSTOM (self-built) · NR.
Only simulators **used in the experiments** count.

**`dataset`** (multi): NGSIM · HIGHD · IND · ROUND · EXID · INTERACTION · WAYMO · NUSCENES ·
NUPLAN · ARGOVERSE · OWN (own recorded data) · NONE.

**`vehicle_model`** (multi when simulation and physical vehicle differ): PM point mass · KIN kinematic bicycle/unicycle · DYN dynamic bicycle/tyre
model · SIMVEH simulator's built-in vehicle physics (CARLA, CarSim, etc.) · REAL real/scaled
vehicle · NR.

**`metrics`** (multi): COLL collision rate/count · SUCC success/completion rate · VIOL constraint
violation rate or cumulative cost · TTC time-to-collision · PET post-encroachment time · DIST
minimum distance/headway/time-gap · RISK risk measure · INTERV safety-layer intervention
frequency · UNSAFE unsafe-action frequency · OFFROAD off-road/lane-departure rate · RULE traffic-
rule violations · DEV lateral/longitudinal tracking deviation · JERK · ACC acceleration ·
COMF comfort index · DSCORE composite driving score (e.g. CARLA driving score) · REW return/reward · SPEED average speed/efficiency · TIME travel time/time-
to-goal · THRU throughput/traffic flow · ENERGY fuel/energy · SAMPLE sample efficiency/learning
curve · COMP computation time · GEN generalization score.

**`baselines`**: names of compared methods (short). **`baseline_types`** (multi): NSRL non-safe RL ·
SRL safe RL · CLASS classical/rule-based/MPC/IDM · HUMAN human driver data · ABL ablation only ·
NONE.

**`results`**: main quantitative findings as reported.

**`generalization`** (multi): DENS traffic density · GEOM road geometry/maps · WEATHER ·
UNSEEN unseen scenarios · AGENTS unseen agent behaviors · DIST disturbances/noise ·
DYN vehicle dynamics · DOMAIN domain shift between simulators/datasets · S2R sim-to-real ·
RULES different traffic rules · NONE. Assign only when the test condition differs from training.

**`validation_tier`** (RQ11, highest reached):
SIM-LOW 2-D/kinematic or abstract simulator (highway-env, SUMO, custom Python, Simulink with
simple models) · SIM-HIFI 3-D physics-based driving simulator (CARLA, LGSVL, AirSim, CarSim,
PreScan, MetaDrive, TORCS, Gazebo/Webots with vehicle dynamics) · SIM-DATA data-driven closed-
loop simulation on real logs (nuPlan, Waymax, replayed NGSIM/highD/INTERACTION) · HIL hardware-
in-the-loop or vehicle-in-the-loop, including processor-in-the-loop on embedded automotive-grade hardware (policy runs on the target computer against a simulated plant) · SCALED small-scale physical vehicle (F1TENTH, robot car) ·
CLOSED full-size vehicle on closed course/test track · ROAD public-road testing · DEPLOY
deployed system. (SCALED and SIM-DATA extend the six RQ11 tiers; they are reported separately
and merged into the nearest RQ11 tier when needed.)

**`real_world`**: description of any physical testing, or `NA`.

## 8. Reproducibility (RQ12)
| Field | Values |
|---|---|
| `code` | Y (public repository link in paper) · REQ (on request) · N |
| `code_url` | the URL or `NA` |
| `data_avail` | Y (data/scenarios released or public dataset) · N · NA (pure simulation with standard maps) |
| `hyperparams` | Y (table or complete list) · P (partial) · N |
| `seeds` | number of independent training seeds/runs, `1` if a single run is evident, `NR` |
| `eval_protocol` | Y (number of test episodes/scenarios and conditions stated) · P · N |
| `stats` | Y (std/CI/significance over runs) · P (variance shown without definition) · N |
| `compute` | Y (hardware and/or training time reported) · N |

## 9. AV safety stack (§28)
**`stack`** (multi), where the RL policy operates: PERC perception · PRED prediction ·
PLAN planning (route/motion/trajectory) · DEC behavioral decision · CTRL control · SUPERV safety
supervision · RTA runtime assurance. The safety component's own layer is recorded too (e.g. an
RL controller with a CBF filter = CTRL;SUPERV).

## 10. Limitations
**`limitations`**: limitations reported by the authors, prefixed `A:`; limitations observed by the
reviewer, prefixed `R:` *(judgment)*.

## 11. Quality assessment (protocol §5)
`qa` = twelve scores (Q1…Q12, each 0/1/2), and `qa_note` justifying **every score below 2**.
Scores of 2 are justified by the corresponding extracted fields (traceability table below).

| Item | Score 2 | Score 1 | Score 0 | Linked fields |
|---|---|---|---|---|
| Q1 objective | explicit problem and contribution | vague | none | problem |
| Q2 Safe RL formulation | MDP/CMDP elements (state, action, reward, cost/constraint) formally defined | partly defined | not defined | reward, safety_cost, constraints |
| Q3 safety mechanism | mechanism specified so it could be re-implemented | described informally | not described | mech |
| Q4 experimental conditions | scenario, traffic, simulator settings, episode setup stated | partly | not stated | simulator, scenario, traffic |
| Q5 baselines | ≥1 non-safe RL **and** ≥1 safe-RL or classical baseline | only one type, or ablations only | none | baseline_types |
| Q6 safety metrics | ≥1 safety metric (COLL, VIOL, TTC, DIST, RISK, PET, UNSAFE, INTERV, OFFROAD, RULE) reported quantitatively with comparison | reported without comparison or only qualitatively | none | metrics |
| Q7 performance metrics | ≥1 performance metric (REW, SUCC, SPEED, TIME, THRU, COMF, JERK…) reported quantitatively | qualitative only | none | metrics |
| Q8 uncertainty/disturbance | evaluation under explicit uncertainty/disturbance conditions | uncertainty only in training (e.g. stochastic traffic) | none | uncertainty |
| Q9 generalization | tested in conditions different from training | only different random seeds/initial states | none | generalization |
| Q10 reproducible evaluation | hyperparameters, environment configuration and seeds/runs reported | two of these three | ≤ one | hyperparams, seeds, eval_protocol |
| Q11 code/data/simulator | public code (or code + data) | public simulator/benchmark named and configured, but no code | proprietary/custom simulator, nothing released | code, simulator |
| Q12 beyond trivial simulation | SIM-HIFI with realistic traffic, SIM-DATA, HIL, SCALED, CLOSED, ROAD | SIM-LOW with multi-vehicle traffic | single-agent toy/abstract setting | validation_tier, traffic |

Total = sum (0–24). Bands: High ≥ 18, Medium 12–17, Low ≤ 11.

---

## 12. Raw-record format
Records are written to `extraction/raw/batchNN.txt`, one block per study:

```
@@ A005
country: China
problem: ...
task: INT; CA
...
qa: 2 2 2 2 2 2 2 1 1 1 0 2
qa_note: Q8 stochastic traffic only; Q9 ...; Q10 no seeds; Q11 no code
```
`scripts/14_build_evidence_db.py` parses the blocks, checks every code against this codebook,
merges the bibliographic fields, computes QA totals/bands and the derived §17 role, and writes
`extraction/evidence_db.xlsx` and `extraction/evidence_db.csv`.

## Revision log
| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-07 | Created before extraction began; pilot on the first 20 studies to follow. |
| 1.1 | 2026-10-07 | After the 20-study pilot (batch01): added network RBF, control BACKSTEP and RULE, metric DSCORE; vehicle_model may be multi-valued (simulation + physical vehicle); HIL explicitly includes processor-in-the-loop on embedded hardware; co-simulators without a code (e.g. NS3 network simulator) are recorded as OTHER:. No definitions of existing codes changed, so pilot records stay valid (OTHER: values recoded). Lesson: keyword hints missed lower-case simulator names, so packets now carry an ENV section of environment/baseline sentences. |
| 1.2 | 2026-10-07 | Coding conventions added during batch 04 (no code definitions changed): (a) benchmark or challenge papers that propose no safety mechanism are coded `mech: OTHER:benchmark` (also `mech_primary`) and assigned L1 when they report safety metrics; (b) when a paper proposes a method and also benchmarks others (e.g. SafeRL-Kit), `mech` reflects the proposed method; (c) `code: Y` with `code_url: NR` is used when the paper states code is public but gives no resolvable link. |
| 1.3 | 2026-10-07 | `action_type` and `action_level` may be `NR` when the paper does not report the action space (first needed for B1149). Questionable-venue studies (B0385, B1149, B1158, B1342, B1700) are coded as reported, with concerns recorded under `limitations` (R:) and safety_level limited to what is substantiated; they are excluded in the sensitivity analysis. |
| 1.4 | 2026-10-07 | Conventions confirmed in batches 09–10 (no code definitions changed): (a) an intervention that acts only during training (rule-based cage, teacher policy or human takeover) gives L1 unless the deployed policy keeps a run-time mechanism; a proven bound that covers only training risk is recorded in `guarantee_assumptions` but does not raise the level; (b) L5 requires real-vehicle results with a reported safety analysis, so a deployment mentioned without data stays at the run-time level (B0658 recoded L5 → L3, stage BOTH); (c) a hardware demonstration that does not run the learned policy does not change `validation_tier` (B1790). (d) L5 needs L3 or L4 *plus* tests on a physical vehicle; scaled physical vehicles count, hardware-in-the-loop alone does not (B0186 recoded L5 → L2, B0575 L5 → L4, B0517 L5 → L3 under rule b). |
| 1.5 | 2026-10-08 | Added the study-level field `explainability` for RQ10, which the v1.0 field list had missed. Candidates were found with `scripts/16_xai_scan.py` (full-text vocabulary scan, `extraction/xai_scan.csv`) and coded by the reviewer in `extraction/xai_codes.csv`: VIS = explanations are produced and inspected (saliency, attention or risk visualization); DESIGN = interpretability-by-design is claimed as a contribution but not evaluated; all other studies NONE. No study evaluated explanations with users. |
| 1.5a | 2026-10-08 | Conventions confirmed while extracting batches 11–19 (164 institutional PDFs; no code definitions changed): (a) studies that add no safety mechanism of their own are coded with a descriptive `OTHER:` mechanism (B1178 safety-oriented state representation; B1443 safety case) and grouped with the benchmark study as cluster M0 in `15_stats.py`; (b) a safety case or assurance argument without new tests is L0, even when it cites earlier physical evidence (B1443); (c) "constraints" on robustness or human similarity (B0741, B1321, B1653, B1816) are coded K or V, not as safety constraints, and do not raise the level above L1; (d) a physical demonstration without safety statistics keeps the run-time level (B1778 scaled testbed stays L3; B1445 field test without a safety analysis stays L3). |
