# Search Strings (Stage B)

Concept blocks. All strings combine **[Safe RL] AND [Vehicle]** (Q1). Q2 is a complementary query, **[RL] AND [Safety/control mechanism] AND [Vehicle]**, which catches papers that use CBFs, shields or MPC with RL but never say "safe RL".

| Block | Terms |
|---|---|
| **S (Safe RL)** | "safe reinforcement learning", "safe RL", "safety reinforcement learning", "constrained reinforcement learning", "risk-sensitive reinforcement learning", "risk-aware reinforcement learning", "safe policy optimization", "constrained policy optimization", "shielded reinforcement learning", "safety-critical reinforcement learning", "safe exploration", "safe deep reinforcement learning", "constrained Markov decision process" |
| **V (Vehicle)** | "autonomous vehicle(s)", "autonomous driving", "self-driving", "automated driving", "automated vehicle(s)", "connected and automated vehicles", "connected autonomous vehicles", "intelligent vehicle(s)", "autonomous car", "driverless" |
| **R (RL)** | "reinforcement learning" |
| **M (Mechanism)** | "control barrier function(s)", "safety filter", "safety shield", "shielding", "safety layer", "Lyapunov", "reachability", "model predictive control", "runtime assurance", "formal verification", "collision avoidance" |

**Limits for all sources:** no start year (the field is effectively 2015 onward); end = search date; English; all document types (non-research items are removed at screening).

---

## A. Run automatically by `scripts/05_search.py`
OpenAlex (Q1, Q2), arXiv (S×V and R×M×V phrase combinations), DBLP (18 title-keyword queries) and Semantic Scholar (attempted). Exact strings, dates and hit counts are in `stageB/search_runs.csv`.

## B. To be run by the authors through institutional access
Export **all** results (RIS or CSV, with abstracts) into `SLR_Workspace/stageB/manual_exports/`, and name each file `<database>_<Q1|Q2>_<YYYY-MM-DD>.<ext>`. Note the hit count shown by the database in the table below.

### Scopus (Advanced search)
```
Q1: TITLE-ABS-KEY ( ( "safe reinforcement learning" OR "safe RL" OR "safety reinforcement learning" OR "constrained reinforcement learning" OR "risk-sensitive reinforcement learning" OR "risk-aware reinforcement learning" OR "safe policy optimization" OR "constrained policy optimization" OR "shielded reinforcement learning" OR "safety-critical reinforcement learning" OR "safe exploration" OR "safe deep reinforcement learning" OR "constrained Markov decision process" ) AND ( "autonomous vehicle*" OR "autonomous driving" OR "self-driving" OR "automated driving" OR "automated vehicle*" OR "connected and automated vehicle*" OR "connected autonomous vehicle*" OR "intelligent vehicle*" OR "autonomous car*" OR driverless ) ) AND ( LIMIT-TO ( LANGUAGE , "English" ) )

Q2: TITLE-ABS-KEY ( "reinforcement learning" AND ( "control barrier function*" OR "safety filter" OR "safety shield" OR shielding OR "safety layer" OR Lyapunov OR reachability OR "model predictive control" OR "runtime assurance" OR "formal verification" OR "collision avoidance" ) AND ( "autonomous vehicle*" OR "autonomous driving" OR "self-driving" OR "automated driving" OR "automated vehicle*" OR "connected and automated vehicle*" OR "connected autonomous vehicle*" OR "intelligent vehicle*" OR "autonomous car*" OR driverless ) ) AND ( LIMIT-TO ( LANGUAGE , "English" ) )
```

### Web of Science Core Collection (Advanced search, field TS)
```
Q1: TS=( ("safe reinforcement learning" OR "safe RL" OR "safety reinforcement learning" OR "constrained reinforcement learning" OR "risk-sensitive reinforcement learning" OR "risk-aware reinforcement learning" OR "safe policy optimization" OR "constrained policy optimization" OR "shielded reinforcement learning" OR "safety-critical reinforcement learning" OR "safe exploration" OR "safe deep reinforcement learning" OR "constrained Markov decision process") AND ("autonomous vehicle*" OR "autonomous driving" OR "self-driving" OR "automated driving" OR "automated vehicle*" OR "connected and automated vehicle*" OR "connected autonomous vehicle*" OR "intelligent vehicle*" OR "autonomous car*" OR driverless) )

Q2: TS=( "reinforcement learning" AND ("control barrier function*" OR "safety filter" OR "safety shield" OR shielding OR "safety layer" OR Lyapunov OR reachability OR "model predictive control" OR "runtime assurance" OR "formal verification" OR "collision avoidance") AND ("autonomous vehicle*" OR "autonomous driving" OR "self-driving" OR "automated driving" OR "automated vehicle*" OR "connected and automated vehicle*" OR "connected autonomous vehicle*" OR "intelligent vehicle*" OR "autonomous car*" OR driverless) )
```

### IEEE Xplore (Command search, "All Metadata")
```
Q1: ("All Metadata":"safe reinforcement learning" OR "All Metadata":"safe RL" OR "All Metadata":"constrained reinforcement learning" OR "All Metadata":"risk-sensitive reinforcement learning" OR "All Metadata":"risk-aware reinforcement learning" OR "All Metadata":"constrained policy optimization" OR "All Metadata":"safe exploration" OR "All Metadata":"safe deep reinforcement learning" OR "All Metadata":"constrained Markov decision process") AND ("All Metadata":"autonomous vehicle*" OR "All Metadata":"autonomous driving" OR "All Metadata":"self-driving" OR "All Metadata":"automated driving" OR "All Metadata":"automated vehicle*" OR "All Metadata":"connected and automated vehicle*" OR "All Metadata":"intelligent vehicle*")

Q2: ("All Metadata":"reinforcement learning") AND ("All Metadata":"control barrier function*" OR "All Metadata":"safety filter" OR "All Metadata":"shield*" OR "All Metadata":"safety layer" OR "All Metadata":Lyapunov OR "All Metadata":reachability OR "All Metadata":"model predictive control" OR "All Metadata":"runtime assurance") AND ("All Metadata":"autonomous vehicle*" OR "All Metadata":"autonomous driving" OR "All Metadata":"self-driving" OR "All Metadata":"automated driving" OR "All Metadata":"automated vehicle*" OR "All Metadata":"intelligent vehicle*")
```
*IEEE limits the number of wildcards and terms per search. If it rejects the string, split Q1 into two halves by the S-block terms and export both.*

### ScienceDirect (Advanced search, Title/Abstract/Keywords; max. 8 Boolean connectors per field)
```
Q1a: ("safe reinforcement learning" OR "constrained reinforcement learning" OR "safe RL" OR "risk-sensitive reinforcement learning") AND ("autonomous vehicle" OR "autonomous driving" OR "automated vehicle" OR "self-driving")
Q1b: ("safe exploration" OR "constrained policy optimization" OR "constrained Markov decision process" OR "safe deep reinforcement learning") AND ("autonomous vehicle" OR "autonomous driving" OR "automated vehicle" OR "self-driving")
Q2a: "reinforcement learning" AND ("control barrier function" OR "safety filter" OR "shielding" OR "model predictive control") AND ("autonomous vehicle" OR "autonomous driving" OR "automated vehicle")
```

### ACM Digital Library / SpringerLink
Use the Q1 string in the advanced search (Abstract field for ACM; "with all/any of the words" is not reliable on SpringerLink, so use the Q1a/Q1b split). Export to BibTeX or RIS.

| Database | Query | Date run | Hits | Export file | Run by |
|---|---|---|---|---|---|
| Scopus | Q1 | | | | |
| Scopus | Q2 | | | | |
| Web of Science | Q1 | | | | |
| Web of Science | Q2 | | | | |
| IEEE Xplore | Q1 | | | | |
| IEEE Xplore | Q2 | | | | |
| ScienceDirect | Q1a/Q1b/Q2a | | | | |
| ACM DL | Q1 | | | | |
| SpringerLink | Q1a/Q1b | | | | |
