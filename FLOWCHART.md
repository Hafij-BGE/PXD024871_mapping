# FLOWCHART

Diagrammatic view of `METHODOLOGY.md`. The specification is authoritative;
these diagrams are navigation aids and must be updated when it changes.

Diagrams are Mermaid and render on GitHub. Each is also described in text
beneath it, so the document is readable where Mermaid does not render.

---

## 1. Master pipeline

Sources, stages, gates, and the decisions that block them.

```mermaid
flowchart TD
    S1["S1 file manifest"]
    S2["S2 sample metadata"]
    S3["S3 identification containers"]
    S5["S5 reference background<br/>conditional on D002"]
    S6["S6 comparison predictors"]
    S7["S7 dataset publication"]

    subgraph PA["PHASE A — provenance mapping"]
        direction TB
        A1["S1-S2 retrieve and checksum"]
        A2["M1 file to metadata row"]
        G1{"G1<br/>inventory"}
        A3["M3 enrichment class<br/>M4 genotype parse"]
        G2{"G2<br/>class and genotype"}
        A4["M2 unit resolution<br/>M5 container to run"]
        A5["S7 stream-extract peptides"]
        G3{"G3<br/>units and containers"}
    end

    subgraph PB["PHASE B — dataset construction"]
        direction TB
        B1["M6 peptide to unit<br/>freeze filtering"]
        B2["negative construction<br/>fix class ratio"]
        G4{"G4<br/>table frozen"}
        B3["leakage and confound audit"]
        G5{"G5<br/>leakage"}
        B4["split construction<br/>hash and commit"]
        B5["preregistration freeze"]
        G6{"G6<br/>split locked"}
    end

    subgraph PC["PHASE C — model and evaluation"]
        direction TB
        C1["model fit<br/>train and validation only"]
        C2["held-out evaluation<br/>unit-level resampling"]
        C3["M7 contamination check<br/>predictor comparison"]
        C4["interpretation and report<br/>clean-environment re-run"]
    end

    S1 --> A1
    S2 --> A1
    A1 --> A2 --> G1
    G1 -->|PASS| A3
    A3 --> G2
    G2 -->|PASS| A4
    S3 --> A5
    A4 --> A5 --> G3
    G3 -->|PASS| B1
    B1 --> G4
    S5 --> B2
    B2 --> G4
    G4 -->|PASS| B3 --> G5
    G5 -->|PASS| B4 --> B5 --> G6
    G6 -->|PASS| C1 --> C2 --> C3 --> C4
    S6 --> C3
    S7 --> G2

    D001["D001 genotype in schema"] -.->|blocks| G2
    D002["D002 negative strategy<br/>and class ratio"] -.->|blocks| G4
    D004["D004 confidence threshold"] -.->|blocks| G4
    D007["D007 minimum-N gate"] -.->|blocks| G4
    D003["D003 shared sequences"] -.->|blocks| G5
    D005["D005 platform confound"] -.->|blocks| G5
    D008["D008 decision rule"] -.->|blocks| G6
    D009["D009 freeze mechanism"] -.->|blocks| G6
    D006["D006 predictor overlap"] -.->|blocks| C3

    classDef src fill:#e8eef7,stroke:#4a6fa5,color:#1a2a3a
    classDef gate fill:#fdf2e0,stroke:#b8860b,color:#3a2e14
    classDef dec fill:#f7e8e8,stroke:#a54a4a,color:#3a1a1a
    class S1,S2,S3,S5,S6,S7 src
    class G1,G2,G3,G4,G5,G6 gate
    class D001,D002,D003,D004,D005,D006,D007,D008,D009 dec
```

**In text:** seven sources feed three phases. Phase A resolves provenance and
ends at G3 with every eligible acquisition assigned to a unit with a class and
a genotype. Phase B builds and freezes the analysis table and the split. Phase
C fits and evaluates. Dotted edges are open decisions; each must be `RESOLVED`
before the gate it points at can pass. Phase A is blocked only at G2, by D001;
everything from G4 onward is blocked by multiple open decisions.

---

## 2. Mapping dataflow

How the seven mappings compose, and what each emits.

```mermaid
flowchart LR
    subgraph IN["inputs"]
        direction TB
        MAN["manifest<br/>filenames, sizes,<br/>published hashes"]
        MET["metadata rows<br/>one per acquisition"]
        CON["containers<br/>identifications"]
    end

    M1["M1<br/>file to row<br/>exact basename"]
    M2["M2<br/>row to unit<br/>participant id"]
    M3["M3<br/>row to class<br/>term table"]
    M4["M4<br/>unit to genotype<br/>parse and validate"]
    M5["M5<br/>container to run<br/>internal record"]
    M6["M6<br/>peptide to unit<br/>composite"]
    M7["M7<br/>peptide to training sets<br/>exact sequence"]

    FM[("FILE_MAP")]
    EL[("ELIGIBILITY")]
    UG[("UNIT_GENOTYPE")]
    UN[("UNITS")]
    CR[("CONTAINER_RUN_MAP")]
    PO[("PEPTIDE_OBSERVATIONS")]
    REJ[("rejects<br/>ambiguous, unmatched,<br/>conflict")]

    MAN --> M1
    MET --> M1
    M1 --> FM
    M1 --> REJ

    MET --> M3 --> EL
    MET --> M2 --> UN
    MET --> M4 --> UG
    M3 --> REJ
    M2 --> REJ
    M4 --> REJ

    CON --> M5
    FM --> M5
    M5 --> CR
    M5 --> REJ

    CR --> M6
    UN --> M6
    EL --> M6
    UG --> M6
    CON --> M6
    M6 --> PO
    M6 --> REJ

    PO --> M7

    classDef map fill:#e8f2e8,stroke:#4a8a4a,color:#1a2a1a
    classDef store fill:#f0f0f4,stroke:#6a6a8a,color:#1a1a2a
    classDef rej fill:#f7e8e8,stroke:#a54a4a,color:#3a1a1a
    class M1,M2,M3,M4,M5,M6,M7 map
    class FM,EL,UG,UN,CR,PO store
    class REJ rej
```

**In text:** M1 joins the manifest to the metadata rows on exact normalized
basename. M2, M3 and M4 each read the metadata rows independently and emit
units, class eligibility, and genotypes. M5 joins containers to acquisitions by
reading each container's own record of its inputs, not by parsing filenames.
M6 composes all of it into the peptide observation table, inheriting the
weakest status along each row's chain. M7 reads the frozen table only. Every
mapping has a second output edge into the rejects store — no mapping drops a
row silently.

---

## 3. Per-row status resolution

The decision procedure every join applies to a single source row. This is where
"never silently force an ambiguous match" is operationalized.

Since `METHODOLOGY.md` was restructured to the prompt's eleven-field format,
these status values are defined **per mapping**, under each one's
*Confidence/status categories* field, rather than in a single shared vocabulary.
Not every mapping uses every value. The diagram shows the common procedure;
each mapping's own field is authoritative for which statuses it can produce.

```mermaid
flowchart TD
    START["source row"] --> NORM["normalize key<br/>N1 to N8"]
    NORM --> LOOK["look up target"]
    LOOK --> N{"candidates<br/>found?"}

    N -->|"0"| EXP{"target<br/>expected?"}
    EXP -->|"no"| OOS["OUT_OF_SCOPE<br/>enumerate explicitly"]
    EXP -->|"yes"| NEAR{"near-miss<br/>present?"}
    NEAR -->|"no"| UNM["UNMATCHED<br/>to rejects"]
    NEAR -->|"yes"| CAND["UNMATCHED<br/>to rejects as<br/>adjudication candidate"]

    N -->|"1"| CONF{"other evidence<br/>disagrees?"}
    CONF -->|"yes"| CFL["CONFLICT<br/>to rejects<br/>no tie broken"]
    CONF -->|"no"| COMP{"evidence<br/>complete?"}
    COMP -->|"yes"| OK["EXACT or EVIDENCED<br/>eligible"]
    COMP -->|"no"| PART["PARTIAL<br/>eligible, flagged<br/>never imputed"]

    N -->|"2 or more"| AMB["AMBIGUOUS<br/>to rejects<br/>full candidate set recorded"]

    OK --> CHAIN["compose with<br/>upstream status<br/>weakest wins"]
    PART --> CHAIN
    CHAIN --> OUT["mapped row"]

    CAND -.->|"logged decision<br/>only"| OK
    AMB -.->|"logged decision<br/>only"| OK

    classDef good fill:#e8f2e8,stroke:#4a8a4a,color:#1a2a1a
    classDef warn fill:#fdf2e0,stroke:#b8860b,color:#3a2e14
    classDef bad fill:#f7e8e8,stroke:#a54a4a,color:#3a1a1a
    class OK,OUT,CHAIN good
    class PART,OOS warn
    class UNM,CAND,AMB,CFL bad
```

**In text:** a row with zero candidates is either `OUT_OF_SCOPE` — no target was
expected, and the category is enumerated so it cannot absorb real failures — or
`UNMATCHED`. A near-miss is still `UNMATCHED`; it is recorded as a candidate for
human adjudication but is never auto-repaired, because at this identifier
density any threshold that fixes a typo also merges distinct entities. Exactly
one candidate gives `EXACT`/`EVIDENCED`, or `PARTIAL` where the evidence is
known incomplete, or `CONFLICT` where another source disagrees. Two or more
candidates is `AMBIGUOUS`. The dotted edges are the only routes out of the
reject states, and both require an entry in `DECISION_LOG.md` — no code path
performs that promotion.

---

## 4. Gate handling

What a gate does, and the two permitted exits from a FAIL.

```mermaid
flowchart TD
    IN["stage outputs"] --> RUN["run all gate checks<br/>record pass/fail each"]
    RUN --> ALL{"all checks<br/>pass?"}

    ALL -->|"yes"| REC["write QC_Gn.md<br/>counts, distributions,<br/>reject tallies"]
    REC --> NEXT["next stage unblocked"]

    ALL -->|"no"| FAIL["gate FAIL recorded<br/>with failing check names"]
    FAIL --> DIAG["diagnose cause"]
    DIAG --> FIX{"correctable?"}

    FIX -->|"yes"| CORR["correct upstream<br/>re-run stage<br/>retain failed outputs"]
    CORR --> RUN

    FIX -->|"no"| ACC["formal acceptance<br/>as limitation"]
    ACC --> LOG["DECISION_LOG entry<br/>scope, consequence,<br/>affected claims"]
    LOG --> LIM["carried to<br/>report limitations"]
    LIM --> NEXT

    BYP["silent bypass"]
    BYP -.->|"prohibited"| NEXT

    classDef good fill:#e8f2e8,stroke:#4a8a4a,color:#1a2a1a
    classDef warn fill:#fdf2e0,stroke:#b8860b,color:#3a2e14
    classDef bad fill:#f7e8e8,stroke:#a54a4a,color:#3a1a1a
    class REC,NEXT,CORR good
    class FAIL,DIAG,ACC,LOG,LIM warn
    class BYP bad
```

**In text:** a gate runs every check and records pass/fail per check — there is
no partial pass. A FAIL exits one of two ways: corrected upstream and re-run,
with the failed outputs retained and the reason recorded; or formally accepted
as a limitation via a logged decision that names which claims it weakens. A
third path, proceeding without either, does not exist.

---

## 5. Decision dependency order

Which open decisions must close, in what order, and what each blocks.

```mermaid
flowchart TD
    subgraph NOW["closeable now — metadata only"]
        D001["D001 genotype in schema"]
        D011["D011 unit definition"]
        D012["D012 partial typing"]
    end

    subgraph AFTERA["needs Phase A counts"]
        D007["D007 minimum-N gate"]
        D004["D004 confidence threshold"]
        D005["D005 platform confound"]
    end

    subgraph AFTERPOS["needs positive set"]
        D002["D002 negative strategy<br/>and class ratio"]
        D003["D003 shared sequences"]
    end

    subgraph PREREG["preregistration"]
        D008["D008 decision rule"]
        D009["D009 freeze mechanism"]
        D010["D010 seed convention"]
    end

    subgraph LATE["evaluation"]
        D006["D006 predictor overlap"]
    end

    G2{"G2"}
    G3{"G3"}
    G4{"G4"}
    G5{"G5"}
    G6{"G6"}
    C3{"G11"}

    D001 --> G2
    D012 --> G2
    D011 --> G3
    D004 --> G4
    D007 --> G4
    D002 --> G4
    D003 --> G5
    D005 --> G5
    D008 --> G6
    D009 --> G6
    D010 --> G6
    D006 --> C3

    G2 --> G3 --> G4 --> G5 --> G6 --> C3

    D007 -.->|"if below threshold<br/>confirmatory arm<br/>does not run"| STOP["stop<br/>report as<br/>infeasible"]

    classDef now fill:#e8f2e8,stroke:#4a8a4a,color:#1a2a1a
    classDef later fill:#f0f0f4,stroke:#6a6a8a,color:#1a1a2a
    classDef gate fill:#fdf2e0,stroke:#b8860b,color:#3a2e14
    classDef stop fill:#f7e8e8,stroke:#a54a4a,color:#3a1a1a
    class D001,D011,D012 now
    class D002,D003,D004,D005,D006,D007,D008,D009,D010 later
    class G2,G3,G4,G5,G6,C3 gate
    class STOP stop
```

**In text:** three decisions are closeable immediately from metadata alone and
block only G2 and G3. Three more need the counts Phase A produces. D002 and
D003 need an existing positive set, so they cannot close before G3 — which is
why the recommended procedure for D002 is to fix the *decision rule* now and
execute it at G4. The preregistration decisions must close before the split is
locked at G6, since locking after seeing performance would void the endpoint.
D007 is the one decision whose outcome can terminate the project: if eligible
positives fall below the preregistered threshold, the confirmatory arm does not
run, and that is a reportable result rather than a failure.

---

## 6. Scope constraint

The constraint from proposal §1 and §28, drawn as what it forbids.

```mermaid
flowchart LR
    MAP["provenance mapping<br/>M1 to M5"] --> TAB["frozen peptide table"]
    TAB --> SPLIT["unit-disjoint split"]
    SPLIT --> CNN["model"]
    CNN --> EVAL["evaluation"]

    CNN -.->|"PROHIBITED"| MAP
    CNN -.->|"PROHIBITED"| TAB
    CNN -.->|"PROHIBITED"| SPLIT
    EVAL -.->|"PROHIBITED"| SPLIT

    classDef ok fill:#e8f2e8,stroke:#4a8a4a,color:#1a2a1a
    class MAP,TAB,SPLIT,CNN,EVAL ok
```

**In text:** the pipeline is strictly one-directional. No model output may
assign a file to a class, a run to a unit, or a peptide to a participant, and
no evaluation result may revise the split. Any code path from a model artifact
back into a mapping table or a split definition is a defect, not a refinement.

---

## See also

- `METHODOLOGY.md` — authoritative specification
- `DATA_SOURCES.md` — the S-numbered sources in diagram 1
- `DECISION_LOG.md` — the D-numbered decisions in diagram 5
- `SECTIONS.md` — gate schedule and per-section status
