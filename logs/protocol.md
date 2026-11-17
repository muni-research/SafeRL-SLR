# Review Protocol, v1.0 (2026-10-07)

**Review:** Safe Reinforcement Learning for Autonomous Vehicles: a PRISMA 2020 systematic literature review
**Target journal:** *Artificial Intelligence Review*
**Status:** Fixed before data extraction. Every later change is recorded in the amendment log at the end, with date and reason.
**Registration:** Not registered yet; the user decides (OSF is an option).

---

## 1. Research questions
Core question and RQ1–RQ14 exactly as in CLAUDE.md §5–6 (see also `PLAN.md` §1).

## 2. Eligibility criteria

### Inclusion (all must hold)
| Code | Criterion |
|---|---|
| IC1 | The study proposes, applies or evaluates a reinforcement-learning method (including RL used inside hybrid control or planning architectures). |
| IC2 | Safety is an explicit objective, constraint, mechanism, metric or evaluation criterion. |
| IC3 | Autonomous, automated or connected **road** vehicles are a substantive application. Simulated settings count. Robot cars and scale vehicles count. Mixed traffic counts if the controlled agent is a vehicle. |
| IC4 | Enough methodological detail to extract the formulation, safety mechanism and evaluation. |
| IC5 | Peer-reviewed journal or conference paper. Preprints only with a recorded reason (very recent and technically complete, or highly cited with no peer-reviewed version). |
| IC6 | English language. |

### Exclusion
| Code | Criterion | Notes |
|---|---|---|
| EC1 | Not a road-vehicle domain | If it is a Safe RL **method** study, assign the decision **Background** instead of Exclude. |
| EC2 | Not RL | Supervised, imitation-only, pure optimization or rule-based methods. Imitation plus RL fine-tuning **counts as RL**. |
| EC3 | Safety superficial | "Safe" appears only in motivation, with no role in the method or evaluation. Safety metrics such as collision rate count as evaluation, but only together with a safety-motivated design. |
| EC4 | Non-research item | Editorial, news, patent, abstract-only. |
| EC5 | Duplicate or superseded version | See §4. |
| EC6 | Insufficient method detail | |
| EC7 | Full text not retrievable | Recorded as "reports not retrieved" in PRISMA. |
| EC8 | Thesis or dissertation | Unless justified. |
| EC10 | RL used to *test or validate* AVs (adversarial scenario generation, falsification), not as part of the driving or control policy | Related evidence for the validation discussion; not a Safe RL policy study. Added 2026-10-07. |
| EC11 | Not in English (IC6) | Added 2026-10-07. |
| EC9 | Review or survey article | **Not** an included primary study. Assign the decision **Review**: used for positioning (prior-review table) and snowballing. |

### Screening decisions
| Decision | Meaning | Counted in PRISMA? |
|---|---|---|
| Include | Meets IC1–IC6 at title/abstract level | Goes to full-text assessment |
| Unsure | Cannot decide from title/abstract | Goes to full-text assessment |
| Exclude (ECx) | Fails one or more criteria | Counted as excluded, with the reason |
| Background | Safe RL method outside road vehicles | Excluded from the AV synthesis (EC1). Reported separately as the background pool. |
| Review | Survey or review article | Excluded as a primary study (EC9). Used for positioning. |

**Consistency check:** a random 20% of the Stage A and Stage B records is re-screened in a separate pass, blind to the first decision. Agreement and Cohen's κ are reported. Because first-pass screening was AI-assisted, **the second screener must be a human author.** The sample is in `stageA/consistency_sample.csv`, generated with fixed seed 20261007.

## 3. Information sources
- **Stage A:** the supplied seed corpus (`Articles for Review/`), inventoried 2026-10-07.
- **Stage B:** Crossref, OpenAlex, Semantic Scholar, arXiv (via API); IEEE Xplore, ScienceDirect, SpringerLink, ACM DL, Wiley, T&F (via search interfaces or Google Scholar where APIs are not accessible); backward and forward snowballing.

## 4. De-duplication
Matches are checked in order: (1) exact DOI; (2) normalized title similarity ≥ 0.90; (3) same first author, year and venue with a similar title. Conference and journal versions of the same study: keep the more complete version as the unit of evidence and log the relationship. Cite both only if the extended version adds distinct experiments.

## 5. Quality assessment
Twelve criteria, Q1–Q12 (CLAUDE.md §14), each scored as:
- **0** = no evidence
- **1** = partial (mentioned or only partly reported)
- **2** = strong (explicit, complete and verifiable)

Maximum score 24. Bands: **High ≥ 18**, **Medium 12–17**, **Low ≤ 11**. The bands are fixed now, before scoring.

Rationale: the scheme follows the checklist style common in software-engineering and AI SLRs (Kitchenham-style quality checklists), adapted to Safe RL evaluation. QA scores are **not** used to exclude studies. They are used for sensitivity analysis (findings restricted to High-quality studies) and reported in Table 12.

Operational guidance:
- **Q5** = 2 requires at least one non-safe RL baseline **and** one safe or classical baseline.
- **Q10** = 2 requires that hyperparameters, environment configuration and seeds/runs are reported.
- **Q12** = 2 requires a high-fidelity simulator with realistic traffic, HIL, or a real vehicle. Grid-world or single-agent kinematic toy settings score 0.

## 6. Data extraction
- **Fields:** CLAUDE.md §15, plus RL role (§17), safety-evidence level L0–L5 (§26), validation tier (RQ11), AV-stack layer (§28), uncertainty types (RQ6) and reproducibility items (RQ12).
- **Vocabularies:** controlled vocabularies are defined in `extraction/codebook.md` (created at the start of Phase 4).

## 7. Review-derived safety-evidence levels
L0 safety asserted · L1 empirical safety · L2 constraint-based safety · L3 runtime enforcement · L4 formal/provable properties · L5 toward certification.

Assign the **highest level actually substantiated**. These levels are a classification proposed by this review, not an external standard.

## 8. Synthesis
- **Methods:** structured narrative synthesis plus descriptive statistics computed by script.
- **No meta-analysis:** none is planned, because metrics, scenarios and simulators are heterogeneous. This will be revisited if a cluster of studies shares a benchmark and metric.
- **Sensitivity analysis:** repeat the key frequencies for High-quality studies only.

## 9. Use of AI assistance
An AI assistant (Claude, Anthropic) supports metadata extraction, screening suggestions and drafting. **Every inclusion decision and every reported number is traceable to logged data and subject to author verification.** This will be disclosed in the manuscript under Springer Nature's AI policy.

---

## Amendment log
| Date | Change | Reason |
|---|---|---|
| 2026-10-07 | v1.0 created | |
| 2026-10-07 | **Phase 4 extraction (v1.3).** Extraction codebook created (`extraction/codebook.md` v1.0) before extraction and piloted on 20 studies; revised to v1.1 (added codes only, no definitions changed). QA justification rule: every score below 2 has a written reason in `qa_note`; scores of 2 are traceable to the linked extracted fields. Records are validated by `scripts/14_build_evidence_db.py`. | Make extraction auditable and consistent. |
| 2026-10-07 | **Stage B screening (v1.2).** Added EC10 (RL for AV testing/scenario generation) and EC11 (non-English). Decisions were recorded per batch of 200 records: every record was read, and the file lists each record whose decision differs from the batch's stated default (EC3), so the default is only a typing aid (`stageB/screening_decisions_raw/`). Traffic-signal-control studies with safety objectives are marked Unsure pending an IC3 check (RL does not control the vehicle). Energy-management studies whose 'safety' concerns battery or powertrain limits, not driving safety, are EC3. Non-road UGV, off-road, AUV/USV and UAV safe-RL studies are Background. | Volume and recurring borderline types met in Stage B. |
| 2026-10-07 | **Operational rules clarified during Stage A screening (v1.1).** (a) A general Safe RL method paper that only *mentions* AVs in its motivation → Background. (b) If its only driving evidence is MetaDrive tasks aggregated inside a benchmark suite (e.g. DSRL offline benchmarks) → Background. (c) If it contains a *dedicated* driving experiment (its own section/setup, e.g. SafeMetaDrive, car-following, multi-agent MetaDrive) → Unsure, and full-text assessment decides whether the AV application is substantive (IC3). (d) "Vehicles" in a generic sense (unicycle agents, target enclosing) → Unsure until the vehicle type is confirmed. (e) Rail (maglev, virtual coupling), aerial, marine, space and warehouse AGVs are non-road → Background. (f) A conference paper superseded by an extended journal version of the same study is removed as a duplicate before screening and logged in `duplicate_log.csv`. (g) Full-text keyword counts (`fulltext_indicators.csv`) are only an aid for finding driving experiments; decisions are made by reading. | Ambiguities met during screening; rules written down so they are applied consistently and can be audited. |
| 2026-10-08 | **Phase 4–5 coding rules (codebook v1.4–v1.5).** (a) Training-only interventions give L1; (b) L5 needs real-vehicle results with a reported safety analysis; (c) a hardware demo that does not run the learned policy does not raise the validation tier; (d) L5 needs L3/L4 plus a physical (full-size or scaled) vehicle test, and HIL alone does not qualify. Recoded: B0658, B0517 (L5 → L3), B0186 (L5 → L2), B0575 (L5 → L4). Added the `explainability` field for RQ10 (VIS/DESIGN/NONE; `scripts/16_xai_scan.py`, `extraction/xai_codes.csv`). | Apply the L0–L5 definitions consistently; RQ10 was missing from the extraction fields. |
| 2026-10-08 | **Phase 5 synthesis.** Statistics from `scripts/15_stats.py` only (tables in `analysis/tables/`, LaTeX macros in `manuscript/stats_macros.tex`). Mechanism categories grouped into six review-derived clusters (M1–M6). Meta-analysis re-examined as required by §8: the largest shared-benchmark cluster (14 MetaDrive studies) uses different maps, densities, cost definitions and training budgets, and several share authors, so results are synthesised narratively and compared descriptively only. Sensitivity analysis extended to four subsets (questionable venues, Low QA, preprints, High QA only). | Planned synthesis; no change to the questions or eligibility criteria. |
| 2026-10-10 | **Citation searching and update search (Stage C).** One round of backward and forward citation searching from the 452 studies included via the database search (OpenAlex reference and citing lists), plus an update search; records already screened and duplicates within the citation results removed; an automated keyword filter (RL ∧ safety ∧ road vehicle on title/abstract) removed records that could not meet the eligibility criteria before manual screening of the remainder (`scripts/24_snowball_update.py`, `stageC/record_flow.json`). Remaining records screened with the unchanged criteria (EC1–EC11); full texts retrieved open-access first, then through institutional access in the reviewer's browser (`scripts/26`, `scripts/08d --stage C`); assessed and extracted with codebook v1.5a; studies coded with C-IDs. No eligibility or coding definition changed. Reported as a separate "identification via other methods" column in the PRISMA flow diagram. | PRISMA 2020 item 7 (other sources) and the planned snowballing step of the protocol. |
| 2026-10-10 | **Consistency checks drawn (scripts/29).** The screening sample is a stratified random 20% of all title/abstract-screened records of Stages A, B and C (2,818 records, 564 sampled, seed 20261010), extended from Stages A–B to include the citation-search records; an extraction check by a second coder was added for a stratified random 10% of included studies (68) on six key fields (evidence level, primary mechanism, RL output, safety integration, validation tier, algorithm family). Agreement and Cohen's κ are computed by scripts/30. A stage-B-only sample drawn earlier (`stageB/consistency_sample.csv`) was never used and is superseded. | Cover the whole screened set and add the extraction check that the AI-use disclosure promises. |
| 2026-10-16 | **Screening consistency check, round 1 (human, blind).** 559 of 564 sampled records re-screened (5 left blank; one entry "ii" set to Include on the screener's instruction; workbook as received kept as `screening_sample_blind_as_received_2026-10-16.xlsx`). Agreement on forwarding to full text 51.5%, Cohen's κ = 0.16 (four categories: 31.8%, κ = 0.08). Disagreements are mainly first-pass exclusions under EC3, EC1, EC2, EC9 and EC8 that the human screener included; the Background category and exclusion codes were not used. Decision (user): resolve every disagreement by discussion in `logs/consistency/screening_disagreements_reconcile.xlsx` (276 rows, `scripts/30b_reconcile_sheet.py`); records agreed as Include/Unsure after a first-pass exclusion go to full-text assessment and the review is updated; the initial κ is reported as observed. | PRISMA 2020 item 8; transparent handling of low agreement. |
| 2026-10-16 | **Screening consistency check, reconciliation.** Screener decisions: reviews/surveys (EC9) and records without an explicit safety role (EC3) are excluded (146 rows); the other rule-based first-pass exclusions (EC1, EC2, EC8, EC10, EC4) are upheld (105 rows); records forwarded at first pass and included after full-text assessment stay included (20); forwarded records that could not be retrieved stay "not retrieved" (5). Result: 251 first-pass exclusions upheld, 25 forwarded records kept, no change of status, PRISMA counts unchanged (`scripts/30_consistency_kappa.py`, `consistency_results.json`). Reported in Sect. 3.6 and Threats to validity with the initial κ = 0.16. | PRISMA 2020 item 8. |
| 2026-10-16 | **Preprint references.** Seven included preprints with a verified peer-reviewed version are cited in that version (B0048 AAAI 2019; B0929 ITSC 2025; B0944 IV 2026; B1285 ICML 2021, PMLR 139; B1639, B1692 ICRA 2026; C0083 CoRL 2019, PMLR 100; `scripts/14` PUBLISHED_VERSION, `stageD/preprint_published_check.csv`); their publication type changes from preprint to conference. All remaining arXiv preprints carry their DataCite arXiv DOI. Background references to SAC, TD3, DDPG, CARLA and the statistical-precipice paper now cite the published versions. No study added or removed. | Prefer peer-reviewed versions; complete DOIs. |
| 2026-10-16 | **Citation policy (reporting only).** Reference list reduced to 150–200 entries at the authors' request: the text and generated tables cite representative studies, preferring articles in JCR 2025 Q1/Q2 journals (`stageD/journal_quartiles.csv`, from the authors' JCR file); conference papers, preprints and lower-quartile journals are cited only where a statement concerns that specific study. Tables show one example per row (Table 17 keeps all L5 studies). The corpus (676 studies), all counts and findings are unchanged; every study remains in Supplementary S3. Final list: 192 references (140 included studies, 52 background). | Concise reference list; transparency stated in Sect. 3.10. |
| 2026-10-17 | **Reference audit (192 entries).** All 181 DOIs resolved and matched their Crossref/DataCite records (title, first author). Fixes: B0209 cited in its current arXiv version (retitled in v2; v1 title given as a note); Altman (1999) title without the series name; reference years set to the year of the published version (Crossref issued year; 19 cited entries, 69 overall), while analyses keep first-appearance year (stated in Sect. 3.8); journal and conference names normalized (e.g. Transportation Research Part C: Emerging Technologies; one ITSC name); AAAI Shielding typed as proceedings. Duplicate check: none. | Reference accuracy and consistency. |
| 2026-11-13 | **Second update search (pre-submission).** The final database strings (OpenAlex Q1v2–Q3v2, arXiv S×V and M×V phrase queries) were re-run without a date filter (`scripts/33_update_search.py`; OpenAlex cursor paging now needs an API key, so page-number paging was used and no key or e-mail was sent) and de-duplicated by DOI, arXiv id and normalized title against every record of Stages A–C; the keyword filter of the citation search was applied. 2,045 records; 1,953 duplicates/already handled; 14 removed by the filter; 78 screened (`stageE/decisions/`, E-IDs; reviews coded Exclude EC9 as in Stage C); 36 sought; 31 retrieved (8 open access, 23 through the authors' institutional access in Chrome, `scripts/08d --stage E`); 5 not retrieved (E002, E021, E066 no access; E042 repository holds no full text; E068 Elsevier, not pursued as decided 2026-10-10); 31 assessed, 26 included (`stageE/ft_decisions_raw/`, extraction `extraction/raw/batch45.txt`), 4 excluded (EC3 ×2, EC6 ×2), 1 to the background pool. Counted in the PRISMA 'other methods' column with the first update search; hit counts for the same strings were lower than on 2026-10-07 (index changes) and the October records are kept. Search date reported: up to 13 November 2026. Corpus 676 → 702 studies. | Bring the search close to the submission date (PRISMA 2020 item 6). |
