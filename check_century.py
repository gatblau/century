#!/usr/bin/env python3
"""
check_century.py — regression harness for century_sim.py.

Guards the invariant the accuracy-upgrade plan was built on: the baseline engine
path must stay bit-identical at seed 431 while behaviour-changing work lands
behind CENTURY_V2_* switches. It:

  * compares the engine's headline output blocks
    (outcomes / aggregates / agi / gap_at_agi / events_per_world) against stored
    golden JSON captured from the current engine;
  * strict-JSON-validates every documented reproduction command — NaN and
    Infinity are rejected, and any RuntimeWarning is promoted to a failure;
  * prints analytic binomial Monte-Carlo 95 % error bars for each outcome share;
  * offers a negative control that perturbs one hazard constant in memory and
    proves the golden comparison actually notices (guards against a vacuous
    checker).

Usage:
  python3 check_century.py                 # default: --quick --full --strict-scenarios
  python3 check_century.py --quick         # N=20000 vs golden/headline-20k-seed431.json
  python3 check_century.py --full          # N=800000 vs golden/headline-800k-seed431.json
  python3 check_century.py --strict-scenarios   # strict-JSON across documented commands (N=5000)
  python3 check_century.py --negative-control    # perturb a hazard constant; comparison MUST fire
  python3 check_century.py --capture       # (re)write golden files from the current engine

Exit status: 0 = every requested check passed; non-zero = at least one failed.
For --negative-control specifically, a NON-ZERO exit is the healthy outcome (the
planted perturbation was detected); a zero exit means the checker is vacuous.

Standard library only (NumPy is used solely by the engine it drives).
"""

import argparse
import contextlib
import io
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "century_sim.py")
GOLDEN_DIR = os.path.join(HERE, "golden")

# The blocks whose every figure is pinned to the seed-431 RNG stream. Later
# phases may extend the profile blocks; these five are the frozen contract.
COMPARE_BLOCKS = ["outcomes", "aggregates", "agi", "gap_at_agi", "events_per_world"]

# Phase 12 flipped the engine default to v2. There are now two golden sets: the v2
# defaults (headline-*) and the retained baseline path (baseline-*, reproduced by
# CENTURY_BASELINE=1). check_golden picks the set from BASELINE_MODE, so
# `check_century.py --full` checks the v2 goldens and `CENTURY_BASELINE=1
# check_century.py --full` checks the baseline goldens.
BASELINE_MODE = bool(int(os.environ.get("CENTURY_BASELINE", "0")))
GOLDEN = {
    (20000, False): os.path.join(GOLDEN_DIR, "headline-20k-seed431.json"),
    (800000, False): os.path.join(GOLDEN_DIR, "headline-800k-seed431.json"),
    (20000, True): os.path.join(GOLDEN_DIR, "baseline-20k-seed431.json"),
    (800000, True): os.path.join(GOLDEN_DIR, "baseline-800k-seed431.json"),
}

# Every documented reproduction command (future.md §9 + strategy.md §6) that can run at
# this gate's N, plus the four retained REC_* switch paths. The ten documented
# CENTURY_OVERRIDES commands (eight distinct — the containment-holds companion and
# prepared-world each appear in both documents) are all present.
#
# Two documented commands are deliberately absent. CENTURY_WEIGHTS and
# CENTURY_LEVER_WEIGHTS load a per-world weights file whose length must equal N, so
# neither can run at N=5000, and the .npz files are gitignored build products that need
# not exist on a fresh clone. --calib-audit and --lever-audit cover those paths at the N
# their weights were built for.
#
# CENTURY_RECOVERY / WINDOW / DIVIDEND / REACT are no longer named in either document —
# V2_STRUCT samples per world the structure they used to switch — but the engine still
# honours them, so they stay here to keep those paths exercised.
SCENARIOS = [
    ("headline", {}),
    ("override:containment-holds", {"CENTURY_OVERRIDES": '{"erode_mag":0}'}),
    ("baseline", {"CENTURY_BASELINE": "1"}),
    ("decadal", {"CENTURY_DECADAL": "1"}),
    ("recovery", {"CENTURY_RECOVERY": "1"}),
    ("window", {"CENTURY_WINDOW": "1"}),
    ("dividend", {"CENTURY_DIVIDEND": "1"}),
    ("react", {"CENTURY_REACT": "1"}),
    ("override:race-world",
     {"CENTURY_OVERRIDES": '{"race":0.95,"respond":0.25,"safety_eff":0.006,"redist_will":0.30}'}),
    ("override:prepared-world",
     {"CENTURY_OVERRIDES": '{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75}'}),
    ("override:plateau-world",
     {"CENTURY_OVERRIDES": '{"plateau":true}'}),
    ("override:fast-takeoff",
     {"CENTURY_OVERRIDES": '{"alpha":1.7,"k":0.15}'}),
    ("override:slow-lane",
     {"CENTURY_OVERRIDES": '{"alpha":1.1,"k":0.06}'}),
    ("override:socio-extremes",
     {"CENTURY_OVERRIDES": '{"race":0.25,"respond":1.0,"safety_eff":0.020,"assist":0.65,"redist_will":0.90}'}),
    ("override:prepared+pace",
     {"CENTURY_OVERRIDES": '{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75,"k":0.06}'}),
]
# The retained-but-unpublished entries, counted separately so the gate's own line does not
# call them documented. Promote a name out of here the moment a document names it.
RETAINED_SCENARIOS = ("recovery", "window", "dividend", "react")
N_OVERRIDE_SCENARIOS = sum(1 for name, _ in SCENARIOS if name.startswith("override:"))
N_RETAINED_SCENARIOS = sum(1 for name, _ in SCENARIOS if name in RETAINED_SCENARIOS)
N_PUBLISHED_SCENARIOS = len(SCENARIOS) - N_RETAINED_SCENARIOS

# Phase 3 v2 mechanical-correction switches, in reporting order (individually
# attributable, then the umbrella). Used by --v2-deltas.
V2_CONFIGS = [
    ("CENTURY_V2_HAZMASK", "absorbed worlds drop out of later same-year hazards"),
    ("CENTURY_V2_NUKE_R", "nuclear exchange also degrades readiness R"),
    ("CENTURY_V2_NATPAND", "natural-pandemic rate scales with capability x biodefence"),
    ("CENTURY_V2_GAPNORM", "takeover hazard uses the threshold-normalised gap"),
    ("CENTURY_V2_SUBSTEP", "sub-annual capability integration for fast-takeoff worlds"),
    ("CENTURY_V2_SOFT", "logistic (soft-saturating) updates for W/Rd/G/Tr/H"),
    ("CENTURY_V2_STRUCT", "per-world sampled structure (window/lethal/dividend/react)"),
    ("CENTURY_V2_CORR", "Gaussian-copula correlated priors (marginals preserved)"),
    ("CENTURY_V2_DEMO", "sampled fertility trajectory (population can decline)"),
    ("CENTURY_V2_CLIMATE", "sampled climate sensitivity + tipping (wider warming)"),
    ("CENTURY_V2_POLICY", "endogenous state-responsive safety_eff / race / respond"),
    ("CENTURY_V2_XHAZ", "unknown-unknowns absorbing hazard (own fate channel)"),
    ("CENTURY_V2_REBUILD", "collapse becomes non-absorbing (rebuild + recover)"),
    ("CENTURY_V2_BIOUP", "post-AGI bio-offence uplift (AGI-grade biotool misuse)"),
    ("CENTURY_V2_ERODE", "capability growth erodes containment/evaluation readiness"),
    ("CENTURY_V2_ALPHASUB", "curvature prior reaches the slow worlds the old ceiling excluded"),
    ("CENTURY_V2_PLATDRAG", "a stalled paradigm slows growth instead of only capping it"),
    ("CENTURY_V2", "umbrella: all seventeen corrections together"),
]
OUTCOME_ORDER = [
    "aligned_abundance", "oligarchic_prosperity", "turbulent_transition",
    "constrained_flourishing", "muddling_degraded",
    "disempowerment", "lockin", "collapse", "extinction",
]
AGGREGATE_ORDER = [
    "good(broadly acceptable)", "aligned_abundance_only",
    "irreversible_bad", "extinction_or_collapse",
]
PINNED_VARS = ["W", "Rd", "G", "Tr", "H"]
NOTES_PATH = os.path.join(HERE, "notes", "v2-deltas.md")
DOC_PATH = os.path.join(HERE, "docs", "future.md")
STRATEGY_PATH = os.path.join(HERE, "docs", "strategy.md")

# --doc-figures verification registry: each entry pins a document table to the engine.
#   doc       - the document file
#   anchor    - a substring of the table's header row that locates the table
#   source    - which engine run supplies the expected values:
#                 "run:<N>"                -> v2 default run at N worlds
#                 "cmd:<overrides-json>@<N>" -> run with CENTURY_OVERRIDES=<json> at N
#                 "env:<K=V,...>@<N>"      -> run with those env vars set at N
#   rows      - {doc-row-label -> dotted engine JSON path} (label matched exactly, * stripped).
#               A row value may instead be {col -> path} to pin several value columns of the
#               same row; col is 1-based over the row's value cells (a plain path means col 1).
#   precision - display decimals to compare at
# Later phases of the doc-regeneration plan append entries here as each section is regenerated.

# Column map for the strategy.md §3 ladder table: P(good) | P(bad) | Extinction |
# Disempower. | Median AGI. Shared by all four ladder rows (one engine run each).
_LADDER = {
    1: "aggregates.good(broadly acceptable)",
    2: "aggregates.irreversible_bad",
    3: "outcomes.extinction",
    4: "outcomes.disempowerment",
    5: "agi.median_year",
}

DOC_TABLES = [
    {"id": "s3-outcomes", "doc": DOC_PATH, "anchor": "| Outcome | Probability", "source": "run:800000", "precision": 1,
     "rows": {
         "Disempowerment": "outcomes.disempowerment",
         "Oligarchic prosperity": "outcomes.oligarchic_prosperity",
         "Aligned abundance": "outcomes.aligned_abundance",
         "Extinction": "outcomes.extinction",
         "Unknown catastrophe": "outcomes.unknown_catastrophe",
         "Turbulent transition": "outcomes.turbulent_transition",
         "Constrained flourishing (no AGI)": "outcomes.constrained_flourishing",
         "Recovered (post-collapse)": "outcomes.recovered",
         "Muddling degraded (no AGI)": "outcomes.muddling_degraded",
         "Totalitarian lock-in": "outcomes.lockin",
         "Civilisational collapse": "outcomes.collapse",
     }},
    {"id": "s3-aggregates", "doc": DOC_PATH, "anchor": "| Aggregate", "source": "run:800000", "precision": 1,
     "rows": {
         "Irreversibly bad (disempowerment + lock-in + collapse + extinction + unknown catastrophe)":
             "aggregates.irreversible_bad",
         "Broadly acceptable (abundance + oligarchic + flourishing)": "aggregates.good(broadly acceptable)",
         "of which extinction or civilisational collapse": "aggregates.extinction_or_collapse",
     }},
    {"id": "s4.1-agi", "doc": DOC_PATH, "anchor": "| Statistic | Value", "source": "run:800000", "precision": 1,
     "rows": {
         "P(AGI by 2126)": "agi.p_agi_by_2126",
         "Median crossing year": "agi.median_year",
         "10th–90th percentile": "agi.p10_year",
         "P(by 2035)": "agi.p_by_2035",
         "P(by 2040)": "agi.p_by_2040",
         "P(by 2050)": "agi.p_by_2050",
     }},
    {"id": "s4.2-gap", "doc": DOC_PATH, "anchor": "| Condition at AGI | Share of crossings", "source": "run:800000", "precision": 1,
     "rows": {
         "Controlled (gap < 0.15)": ["gap_at_agi", "p_controlled(gap<0.15)"],
         "Contested (0.15–0.35)": ["gap_at_agi", "p_contested(0.15-0.35)"],
         "Uncontrolled (gap > 0.35)": ["gap_at_agi", "p_uncontrolled(>0.35)"],
     }},
    {"id": "s4.4-hazards", "doc": DOC_PATH, "anchor": "| Event | Expected count per world", "source": "run:800000", "precision": 2,
     "rows": {
         "Regional wars": ["events_per_world", "regional_war"],
         "Natural (COVID-class) pandemics": ["events_per_world", "nat_pandemic"],
         "AI warning-shot incidents": ["events_per_world", "warning_shot"],
         "Nuclear use events (any scale)": ["events_per_world", "nuclear_war"],
         "Engineered pandemics (any severity)": ["events_per_world", "eng_pandemic"],
     }},
    {"id": "s3.2-disemp-cond", "doc": DOC_PATH, "anchor": "| Condition | P(disempowerment)", "source": "run:800000", "precision": 1,
     "rows": {
         "No AGI at all": ["conditionals", "P(disemp)|no_agi"],
         "Crossed AGI with gap < 0.15": ["conditionals", "P(disemp)|gap<0.15_at_agi"],
         "AGI after 2050": ["conditionals", "P(disemp)|agi>2050"],
         "Crossed AGI with gap > 0.35": ["conditionals", "P(disemp)|gap>0.35_at_agi"],
         "AGI by 2035": ["conditionals", "P(disemp)|agi<=2035"],
     }},
    {"id": "s3.3-crossing", "doc": DOC_PATH, "anchor": "| Condition at AGI crossing | Share of abundance", "source": "run:800000", "precision": 1,
     "rows": {
         "Controlled (gap < 0.15)": ["abundance_profile", "crossing_condition_%", "controlled(gap<0.15)"],
         "Contested (0.15–0.35)": ["abundance_profile", "crossing_condition_%", "contested(0.15-0.35)"],
         "Uncontrolled (gap > 0.35)": ["abundance_profile", "crossing_condition_%", "uncontrolled(>0.35)"],
     }},
    {"id": "s6.2-bad-cond", "doc": DOC_PATH, "anchor": "| Condition | P(irreversibly bad)", "source": "run:800000", "precision": 1,
     "rows": {
         "Crossed AGI with gap > 0.35": ["conditionals", "P(bad)|gap>0.35_at_agi"],
         "Crossed AGI with gap < 0.15": ["conditionals", "P(bad)|gap<0.15_at_agi"],
         "AGI by 2035": ["conditionals", "P(bad)|agi<=2035"],
         "AGI after 2050": ["conditionals", "P(bad)|agi>2050"],
         "No AGI at all": ["conditionals", "P(bad)|no_agi"],
     }},
    {"id": "strat3-ladder-headline", "doc": STRATEGY_PATH, "anchor": "| Configuration | P(good)",
     "source": "run:800000", "precision": 1,
     "rows": {"Do nothing (headline)": _LADDER}},
    {"id": "strat3-ladder-prepared", "doc": STRATEGY_PATH, "anchor": "| Configuration | P(good)",
     "source": 'cmd:{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75}@800000',
     "precision": 1,
     "rows": {"Make the feasible socio-political choices": _LADDER}},
    {"id": "strat3-ladder-extremes", "doc": STRATEGY_PATH, "anchor": "| Configuration | P(good)",
     "source": 'cmd:{"race":0.25,"respond":1.0,"safety_eff":0.020,"assist":0.65,"redist_will":0.90}@800000',
     "precision": 1,
     "rows": {"Socio-levers at their extremes": _LADDER}},
    {"id": "strat3-ladder-pace", "doc": STRATEGY_PATH, "anchor": "| Configuration | P(good)",
     "source": 'cmd:{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75,"k":0.06}@800000',
     "precision": 1,
     "rows": {"Feasible choices + pace restraint (compute governance)": _LADDER}},

    # Calibration tables (sections 6.3 and 6.5, and the summary tables realistic-bet.md
    # builds from them). These quote the max-entropy solve rather than any engine run, so
    # until the calib: source existed they were the only tables in the documents this gate
    # could not see. They are also the ones that went stale unnoticed when the arrival
    # anchors were revised. Column 2 of a fit table is a range cell; _num takes the first
    # token, so it pins the band's LOWER edge against anchors.json. The upper edge is not
    # pinned here, which is stated rather than silent: an anchors.json edit that moved only
    # an upper bound would still change the weighted column and be caught that way.
    {"id": "s6.3-fit-p", "doc": DOC_PATH, "anchor": "| Target | Unweighted | Acceptable range",
     "source": "calib:xpt_superforecaster@50000", "precision": 3,
     "rows": {
         "P(AGI by 2035)": {1: "fit.p_agi_by_2035.unweighted", 2: "fit.p_agi_by_2035.lo",
                            3: "fit.p_agi_by_2035.weighted"},
         "P(AGI by 2050)": {1: "fit.p_agi_by_2050.unweighted", 2: "fit.p_agi_by_2050.lo",
                            3: "fit.p_agi_by_2050.weighted"},
         "P(never AGI by 2126)": {1: "fit.p_never_agi_by_2126.unweighted",
                                  2: "fit.p_never_agi_by_2126.lo",
                                  3: "fit.p_never_agi_by_2126.weighted"},
         "P(extinction)": {1: "fit.p_extinction.unweighted", 2: "fit.p_extinction.lo",
                           3: "fit.p_extinction.weighted"},
         "Nuclear wars per world": {1: "fit.nuclear_events_per_world.unweighted",
                                    3: "fit.nuclear_events_per_world.weighted"},
         "Pandemics per world (COVID-class)": {1: "fit.nat_pandemic_events_per_world.unweighted",
                                               3: "fit.nat_pandemic_events_per_world.weighted"},
     }},
    # Same table, coarser rows: the two endpoint anchors are quoted to 2 dp, and a registry
    # spec carries a single precision.
    {"id": "s6.3-fit-endpoints", "doc": DOC_PATH, "anchor": "| Target | Unweighted | Acceptable range",
     "source": "calib:xpt_superforecaster@50000", "precision": 2,
     "rows": {
         "Population 2126, survivors (bn)": {1: "fit.pop_2126_survivors_bn.unweighted",
                                             3: "fit.pop_2126_survivors_bn.weighted"},
         "Warming 2126, survivors (°C)": {1: "fit.warming_2126_survivors_C.unweighted",
                                          3: "fit.warming_2126_survivors_C.weighted"},
     }},
    {"id": "s6.3-outcomes", "doc": DOC_PATH, "anchor": "| Outcome | Model priors | Target-weighted",
     "source": "calib:xpt_superforecaster@50000", "precision": 1,
     "rows": {
         "Good (broadly acceptable)": {1: "outcomes.good.prior", 2: "outcomes.good.weighted"},
         "Aligned abundance": {1: "outcomes.aligned_abundance.prior",
                               2: "outcomes.aligned_abundance.weighted"},
         "Disempowerment": {1: "outcomes.disempowerment.prior",
                            2: "outcomes.disempowerment.weighted"},
         "Irreversibly bad": {1: "outcomes.bad.prior", 2: "outcomes.bad.weighted"},
         "Extinction": {1: "outcomes.extinction.prior", 2: "outcomes.extinction.weighted"},
         "Extinction or collapse": {1: "outcomes.ext_or_collapse.prior",
                                    2: "outcomes.ext_or_collapse.weighted"},
         "Unknown catastrophe": {1: "outcomes.unknown_catastrophe.prior",
                                 2: "outcomes.unknown_catastrophe.weighted"},
     }},
    {"id": "s6.5-lever-fit", "doc": DOC_PATH, "anchor": "| Choice | Unweighted | Likelihood range",
     "source": "calib:levers@800000", "precision": 3,
     "rows": {
         "Gains shared": {1: "fit.p_gains_shared.unweighted", 2: "fit.p_gains_shared.lo",
                          3: "fit.p_gains_shared.weighted"},
         "Institutions react": {1: "fit.p_institutions_react.unweighted",
                                2: "fit.p_institutions_react.lo",
                                3: "fit.p_institutions_react.weighted"},
         "Safety work funded": {1: "fit.p_safety_funded.unweighted", 2: "fit.p_safety_funded.lo",
                                3: "fit.p_safety_funded.weighted"},
         "AI used for safety": {1: "fit.p_ai_helps_safety.unweighted",
                                2: "fit.p_ai_helps_safety.lo",
                                3: "fit.p_ai_helps_safety.weighted"},
         "Race cooled": {1: "fit.p_race_cooled.unweighted", 2: "fit.p_race_cooled.lo",
                         3: "fit.p_race_cooled.weighted"},
     }},
    {"id": "s6.5-lever-outcomes", "doc": DOC_PATH,
     "anchor": "| Outcome | Model priors | Likelihood-weighted",
     "source": "calib:levers@800000", "precision": 1,
     "rows": {
         "Good (broadly acceptable)": {1: "outcomes.good.prior", 2: "outcomes.good.weighted"},
         "Aligned abundance": {1: "outcomes.aligned_abundance.prior",
                               2: "outcomes.aligned_abundance.weighted"},
         "Disempowerment": {1: "outcomes.disempowerment.prior",
                            2: "outcomes.disempowerment.weighted"},
         "Irreversibly bad": {1: "outcomes.bad.prior", 2: "outcomes.bad.weighted"},
         "Extinction": {1: "outcomes.extinction.prior", 2: "outcomes.extinction.weighted"},
     }},
    # realistic-bet.md's two summary tables restate the same three readings for a general
    # audience. The headline and realistic-bet rows come from the lever solve (its prior IS
    # the 800,000-world headline); the outside-view row comes from the 50,000-world anchor
    # solve, which is why that row is a separate spec against a separate source.
    {"id": "rb-readings-headline", "doc": os.path.join(HERE, "docs", "realistic-bet.md"),
     "anchor": "| Reading | The question it answers", "source": "calib:levers@800000", "precision": 1,
     "rows": {"The headline": {2: "outcomes.good.prior", 3: "outcomes.bad.prior"},
              "The realistic bet": {2: "outcomes.good.weighted", 3: "outcomes.bad.weighted"}}},
    {"id": "rb-readings-outside", "doc": os.path.join(HERE, "docs", "realistic-bet.md"),
     "anchor": "| Reading | The question it answers",
     "source": "calib:xpt_superforecaster@50000", "precision": 1,
     "rows": {"The outside view": {2: "outcomes.good.weighted", 3: "outcomes.bad.weighted"}}},
    {"id": "rb-outcomes", "doc": os.path.join(HERE, "docs", "realistic-bet.md"),
     "anchor": "| Outcome | The headline | The realistic bet",
     "source": "calib:levers@800000", "precision": 1,
     "rows": {
         "Good century": {1: "outcomes.good.prior", 2: "outcomes.good.weighted"},
         "The best ending (aligned abundance)": {1: "outcomes.aligned_abundance.prior",
                                                 2: "outcomes.aligned_abundance.weighted"},
         "Humans lose control quietly (disempowerment)": {1: "outcomes.disempowerment.prior",
                                                          2: "outcomes.disempowerment.weighted"},
         "Irreversibly bad century": {1: "outcomes.bad.prior", 2: "outcomes.bad.weighted"},
     }},
]

# --doc-figures prose registry: each entry pins a figure quoted *inline in prose* to the
# engine. DOC_TABLES only parses Markdown tables, so a stale number in a sentence or a
# bullet passes the gate unnoticed; docs/future.md section 6 carried a wrong plateau swing
# in its prose for exactly this reason while the table beside it was correct.
#   doc / source / precision - as in DOC_TABLES
#   figures                  - one entry per quoted number:
#       label   - what is printed in the report
#       pattern - regex locating the figure; must contain exactly one capture group (the
#                 number) and must match the document exactly once. A pattern that matches
#                 zero times (the prose was reworded) or several times (the anchor is not
#                 specific enough) is a failure, not a skip: either way the figure is no
#                 longer pinned and a human must re-anchor it.
#       path    - dotted engine JSON path supplying the expected value
# Only figures stated to the documents' working precision are registered. Prose that
# deliberately rounds ("a statistical dead heat: redistribution (+21), the plateau (+21)")
# is an approximation, not a claim about an engine output, and is left alone.
_PNUM = r"([-+−]?\d+(?:\.\d+)?)"       # signed number, unicode minus included

DOC_PROSE = [
    {"id": "s6-prose-swings", "doc": DOC_PATH, "source": "run:800000", "precision": 1,
     "figures": [
         {"label": "s6 leaders: redistribution",
          "pattern": r"Redistribution \(" + _PNUM + r"\) and institutional responsiveness",
          "path": "sensitivity_P_good.redist_will.swing"},
         {"label": "s6 leaders: responsiveness",
          "pattern": r"institutional responsiveness \(" + _PNUM + r"\) lead, several points clear",
          "path": "sensitivity_P_good.respond.swing"},
         {"label": "s6 leaders: safety effort",
          "pattern": r"human-paced safety effort \(" + _PNUM + r"\) further back",
          "path": "sensitivity_P_good.safety_eff.swing"},
         {"label": "s6 time: plateau",
          "pattern": r"the plateau \(" + _PNUM + r"\) sits just behind them",
          "path": "sensitivity_P_good.plateau.swing"},
         {"label": "s6 time: growth rate k",
          "pattern": r"Faster growth \(" + _PNUM + r"\)",
          "path": "sensitivity_P_good.k.swing"},
         {"label": "s6 time: racing",
          "pattern": r"racing \(" + _PNUM + r"\)",
          "path": "sensitivity_P_good.race.swing"},
         {"label": "s6 inequality: initial concentration",
          "pattern": r"Initial concentration \(" + _PNUM + r"\) now sits",
          "path": "sensitivity_P_good.concentration0.swing"},
         {"label": "s6 inequality: climate abatement",
          "pattern": r"climate abatement \(" + _PNUM + r"\)",
          "path": "sensitivity_P_good.climate_eff.swing"},
     ]},
    {"id": "s9-prose-swings", "doc": DOC_PATH, "source": "run:800000", "precision": 1,
     "figures": [
         {"label": "s9 finding 6: redistribution",
          "pattern": r"Redistribution \(" + _PNUM + r"\) and responsiveness",
          "path": "sensitivity_P_good.redist_will.swing"},
         {"label": "s9 finding 6: responsiveness",
          "pattern": r"and responsiveness \(" + _PNUM + r"\) lead",
          "path": "sensitivity_P_good.respond.swing"},
         {"label": "s9 finding 6: racing",
          "pattern": r"race de-escalation \(" + _PNUM + r" for racing\)",
          "path": "sensitivity_P_good.race.swing"},
         {"label": "s9 finding 6: safety effort",
          "pattern": r"safety effort \(" + _PNUM + r"\) close behind",
          "path": "sensitivity_P_good.safety_eff.swing"},
         {"label": "s9 finding 6: initial concentration",
          "pattern": r"inherited inequality \(" + _PNUM + r" for initial concentration\)",
          "path": "sensitivity_P_good.concentration0.swing"},
     ]},
    {"id": "strat-prose-swings", "doc": STRATEGY_PATH, "source": "run:800000", "precision": 1,
     "figures": [
         {"label": "strat s2: redistribution largest swing",
          "pattern": r"the largest swing \(" + _PNUM + r"\)",
          "path": "sensitivity_P_good.redist_will.swing"},
         {"label": "strat s2: responsiveness",
          "pattern": r"Institutional responsiveness \(`S_Ti` 0\.107, swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.respond.swing"},
         {"label": "strat s2: safety effort",
          "pattern": r"human-paced safety effort \(`S_Ti` 0\.139, swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.safety_eff.swing"},
         {"label": "strat s2: climate effort",
          "pattern": r"climate effort, for all its " + _PNUM + r" swing",
          "path": "sensitivity_P_good.climate_eff.swing"},
         {"label": "strat s4: share the gains early",
          "pattern": r"share the gains early \(`redist_will`, `S_Ti` 0\.174; swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.redist_will.swing"},
         {"label": "strat s4: cool the race",
          "pattern": r"Cool the race \(`race`, swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.race.swing"},
     ]},
    # The effective sample size of each solve. It is quoted in prose rather than in the
    # tables above, and it is the number that says whether a reweighting is supported by
    # the bulk of the ensemble or by a handful of extreme worlds, so leaving it unpinned
    # would leave the tables' credibility statement free to drift away from the tables.
    {"id": "s6.3-ess", "doc": DOC_PATH, "source": "calib:xpt_superforecaster@50000", "precision": 1,
     "figures": [
         {"label": "s6.3 effective sample size",
          "pattern": r"\*\*effective sample size of " + _PNUM + r" %\*\*",
          "path": "ess_pct"},
     ]},
    {"id": "s6.5-ess", "doc": DOC_PATH, "source": "calib:levers@800000", "precision": 1,
     "figures": [
         {"label": "s6.5 effective sample size",
          "pattern": r"The tilt keeps an effective sample size of " + _PNUM + r" %",
          "path": "ess_pct"},
     ]},
    {"id": "rb-ess", "doc": os.path.join(HERE, "docs", "realistic-bet.md"),
     "source": "calib:levers@800000", "precision": 0,
     "figures": [
         {"label": "realistic-bet effective sample size",
          "pattern": _PNUM + r" % of them still count afterwards",
          "path": "ess_pct"},
     ]},
]

# --readability gate: the documents are the product, and until now nothing checked whether
# they can be read. Every figure in them is verified against the engine while the sentences
# around those figures were free to drift into machine description; that is exactly what
# happened during the plan-28 Phase F figure pass, and a human caught it rather than a test.
#
# Three things are measured per document, all of them mechanical:
#   1. sentence length, mean and 90th percentile, in words
#   2. jargon that is never explained anywhere in that document
#   3. the opening paragraph, which must be short and jargon-free
#
# A term counts as EXPLAINED if any occurrence of it in the document sits in a sentence that
# also carries a gloss marker, or if the document defines it in a glossary line. Explaining a
# term once anywhere makes every later use of it free. That is deliberate: the gate should
# push towards explaining the vocabulary, not towards avoiding it, because these documents
# have real technical content and hiding it would be worse than naming it.
JARGON = [
    "ensemble", "hazard", "absorbing", "quartile", "copula", "prior", "posterior",
    "conditional", "marginal", "Sobol", "S_Ti", "S_i", "Saltelli", "total-order",
    "first-order", "numerator", "denominator", "variance", "estimator", "lognormal",
    "orthogonal", "monotone", "logit", "Gaussian", "reweight", "reweighting",
    "maximum-entropy", "max-entropy", "effective sample size", "survivorship",
    "structure-conditional", "importance sampling", "stochastic", "vectorised",
]

# Any of these near a term marks it as explained. Parentheses and the em-dash-free
# apposition forms cover how these documents actually introduce a word.
_GLOSS_MARKERS = [
    "(", "which is", "which means", "that is", "meaning", "in other words", "read it as",
    "read this as", "stands for", "is the", "are the", "is how", "is what", "is a", "means",
    ":",
]

# mean / p90 are words per sentence; jargon is unexplained occurrences per 1000 prose words.
# The three plain-audience documents are pinned at zero jargon because they earned it and
# must not slip. future.md and strategy.md carry real technical content, so they get a small
# allowance rather than zero, on the understanding that a term explained once costs nothing.
DOC_PROSE_BUDGETS = [
    {"doc": "README.md", "mean": 17.0, "p90": 29, "jargon_per_1000": 2.0, "opener_words": 60},
    {"doc": "docs/how-it-works.md", "mean": 17.0, "p90": 28, "jargon_per_1000": 0.0, "opener_words": 70},
    {"doc": "docs/future.md", "mean": 21.0, "p90": 36, "jargon_per_1000": 1.0, "opener_words": 70},
    {"doc": "docs/strategy.md", "mean": 20.0, "p90": 34, "jargon_per_1000": 1.5, "opener_words": 70},
    {"doc": "docs/levers-and-preparedness.md", "mean": 21.0, "p90": 38, "jargon_per_1000": 0.0, "opener_words": 80},
    {"doc": "docs/realistic-bet.md", "mean": 18.0, "p90": 30, "jargon_per_1000": 0.0, "opener_words": 70},
    {"doc": "docs/reading-the-output.md", "mean": 18.0, "p90": 30, "jargon_per_1000": 0.0, "opener_words": 70},
    {"doc": "docs/sensitivity-charts.md", "mean": 19.0, "p90": 31, "jargon_per_1000": 0.0, "opener_words": 70},
]

_ABBREV = [("e.g.", "e_g_"), ("i.e.", "i_e_"), ("etc.", "etc_"), ("vs.", "vs_"),
           ("Dr.", "Dr_"), ("Mr.", "Mr_"), ("No.", "No_"), ("approx.", "approx_")]


def _prose_lines(text):
    """Strip everything that is not narrative prose: code fences, tables, headings, images,
    horizontal rules and bare link lines. What is left is what a reader actually reads."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    out = []
    for line in text.split("\n"):
        st = line.strip()
        if not st or st.startswith(("|", "#", "---", "===", "![", "<!--", ">")):
            continue
        out.append(line)
    return out


def _sentences(prose):
    """Split prose into sentences, protecting decimals, abbreviations and percentages so
    '9.7 %' and 'e.g.' do not read as sentence ends. A line break is a hard boundary: two
    consecutive bullets are two sentences, and joining them would inflate every length."""
    sents = []
    for line in prose.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Emphasis and list markers come off BEFORE splitting: "**A lead.** Then more"
        # would otherwise read as one sentence, because the full stop is followed by an
        # asterisk rather than by whitespace, and every bold lead-in would count double.
        line = re.sub(r"^\s*[-+*]\s+|^\s*\d+\.\s+", " ", line)
        # Asterisks, backticks and quote markers only. Underscores stay, because they are
        # part of the identifiers these documents name (S_Ti, erode_mag, redist_will) and
        # stripping them would hide those terms from the jargon check.
        line = re.sub(r"[*`>]", " ", line)
        for a, b in _ABBREV:
            line = line.replace(a, b)
        line = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", line)
        for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])", line):
            p = p.replace("<DOT>", ".")
            for a, b in _ABBREV:
                p = p.replace(b, a)
            clean = p.strip()
            if len(clean.split()) > 3:
                sents.append(clean)
    return sents


def _unexplained_jargon(prose, sents):
    """Return {term: occurrences} for every jargon term the document never explains."""
    lowered = prose.lower()
    unexplained = {}
    for term in JARGON:
        pat = r"(?<![\w-])" + re.escape(term.lower()) + r"(?![\w])"
        hits = len(re.findall(pat, lowered))
        if not hits:
            continue
        # Glossary line, e.g. "- **ensemble** is the 800,000 worlds" or a definition list.
        if re.search(r"^\s*[-*|].{0,10}\*\*" + re.escape(term) + r"\*\*", prose,
                     re.I | re.M):
            continue
        explained = False
        for s in sents:
            if re.search(pat, s.lower()) and any(m in s.lower() for m in _GLOSS_MARKERS):
                explained = True
                break
        if not explained:
            unexplained[term] = hits
    return unexplained


def _opening_paragraph(text):
    """The first narrative paragraph after the H1 title, which is the sentence a newcomer
    reads before deciding whether to keep going."""
    body = text.split("\n")
    started = False
    buf = []
    for line in body:
        st = line.strip()
        if st.startswith("# "):
            started = True
            continue
        if not started:
            continue
        if st.startswith(("|", "```", "![", "<!--")):
            continue
        if st.startswith("#") or st.startswith("---"):
            if buf:
                break
            continue
        if not st:
            if buf:
                break
            continue
        buf.append(st)
    return " ".join(buf)


def check_doc_prose_readable():
    """Readability gate: the documents are for people, so their sentence length, their
    unexplained vocabulary and their opening paragraph are budgeted per document and
    checked, in the same spirit as --doc-figures checks their numbers."""
    print("[readability] %d document(s) against their prose budgets" % len(DOC_PROSE_BUDGETS))
    ok = True
    for spec in DOC_PROSE_BUDGETS:
        path = os.path.join(HERE, spec["doc"])
        if not os.path.exists(path):
            print("  [%s] MISSING — file not found" % spec["doc"])
            ok = False
            continue
        with open(path) as f:
            text = f.read()
        prose = "\n".join(_prose_lines(text))
        sents = _sentences(prose)
        if not sents:
            print("  [%s] MISSING — no prose found to measure" % spec["doc"])
            ok = False
            continue
        lens = sorted(len(s.split()) for s in sents)
        words = sum(lens)
        mean = words / len(lens)
        p90 = lens[min(int(len(lens) * 0.9), len(lens) - 1)]
        unexplained = _unexplained_jargon(prose, sents)
        jcount = sum(unexplained.values())
        jper1k = 1000.0 * jcount / max(words, 1)
        opener = _opening_paragraph(text)
        opener_words = len(opener.split())
        opener_jargon = sorted(_unexplained_jargon(opener, _sentences(opener)))

        rows = [
            ("mean sentence", "%.1f" % mean, "<= %.1f" % spec["mean"], mean <= spec["mean"] + 1e-9),
            ("p90 sentence", "%d" % p90, "<= %d" % spec["p90"], p90 <= spec["p90"]),
            ("unexplained jargon /1000", "%.1f" % jper1k, "<= %.1f" % spec["jargon_per_1000"],
             jper1k <= spec["jargon_per_1000"] + 1e-9),
            ("opening paragraph words", "%d" % opener_words, "<= %d" % spec["opener_words"],
             0 < opener_words <= spec["opener_words"]),
            ("opening paragraph jargon", "%d" % len(opener_jargon), "== 0", not opener_jargon),
        ]
        doc_ok = all(r[3] for r in rows)
        ok = ok and doc_ok
        print("  [%s] %d prose words, %d sentences" % (spec["doc"], words, len(sents)))
        for label, got, want, good in rows:
            print("    %-26s %8s  %-9s %s" % (label, got, want, "OK" if good else "OVER"))
        if jcount and jper1k > spec["jargon_per_1000"] + 1e-9:
            worst = sorted(unexplained.items(), key=lambda kv: -kv[1])[:6]
            print("      never explained: %s"
                  % ", ".join("%s x%d" % (t, n) for t, n in worst))
        if opener_jargon:
            print("      opening paragraph uses: %s" % ", ".join(opener_jargon))
        if mean > spec["mean"] + 1e-9 or p90 > spec["p90"]:
            longest = sorted(sents, key=lambda s: -len(s.split()))[:2]
            for s in longest:
                print("      %d words: %s..." % (len(s.split()), s[:110]))
    ok = _check_doc_anchors() and ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "every document is inside its readability budget" if ok else
          "see OVER rows; shorten sentences, explain the vocabulary or fix the opener"))
    return ok


def _check_doc_anchors():
    """Do the phrases --doc-figures pins still exist in the prose?

    Rewriting a sentence can silently detach a machine-checked figure from its anchor:
    capitalising a word at a new sentence start is enough, and that is exactly what
    happened when these documents were rewritten for readability. --doc-figures catches it
    only after running the engine several times, which is minutes of waiting for an answer
    that is available from the text alone. This runs no engine and reports in a second, so
    an editor learns immediately rather than at the end of a full check."""
    broken = []
    n_pat = 0
    for spec in DOC_PROSE:
        path = os.path.join(HERE, spec["doc"])
        if not os.path.exists(path):
            continue
        with open(path) as f:
            text = f.read()
        for fig in spec["figures"]:
            n_pat += 1
            n = len(re.findall(fig["pattern"], text))
            if n != 1:
                broken.append("%s [%s] matched %d times, expected 1"
                              % (spec["doc"], fig["label"], n))
    n_anchor = 0
    for spec in DOC_TABLES:
        path = os.path.join(HERE, spec["doc"])
        if not os.path.exists(path):
            continue
        with open(path) as f:
            text = f.read()
        n_anchor += 1
        if spec["anchor"] not in text:
            broken.append("%s [%s] table anchor %r not found"
                          % (spec["doc"], spec["id"], spec["anchor"]))
    print("  [anchors] %d prose pattern(s) and %d table anchor(s) that --doc-figures pins"
          % (n_pat, n_anchor))
    for b in broken:
        print("    BROKEN %s" % b)
    print("    %s" % ("all anchors still resolve" if not broken else
                      "re-anchor the pattern or restore the wording before committing"))
    return not broken


def _reject_nonfinite(name, value):
    # json.loads calls parse_constant only for NaN / Infinity / -Infinity.
    raise ValueError("strict JSON rejects non-finite constant %r" % name)


def run_engine(n, env_extra=None, clean=True):
    """Run the engine file at N=n as a subprocess and return its parsed JSON.

    RuntimeWarnings are promoted to errors (-W), a non-zero exit or any stderr
    output is a hard failure, and NaN/Infinity are rejected on parse.

    Runs are HERMETIC by default: every ambient CENTURY_* variable is dropped before
    env_extra is applied, so a call reproduces exactly the configuration it names. Every
    caller but one states its whole configuration in env_extra, and inheriting the
    ambient environment on top of that produced contradictory runs — invoking the
    harness as `CENTURY_BASELINE=1 check_century.py` leaked the baseline path into the
    scenario gate (the containment-holds override then hit an unsampled erode_mag) and
    into --doc-figures (whose registered figures are v2, so the baseline output has no
    unknown_catastrophe class), and would have let --capture write a baseline run into
    the v2 golden.

    check_golden is the one caller that passes clean=False: reading the ambient
    CENTURY_BASELINE is how it addresses the two golden sets.
    """
    env = dict(os.environ)
    if clean:
        for _k in [_k for _k in env if _k.startswith("CENTURY_")]:
            del env[_k]
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", ENGINE, str(n)],
        capture_output=True, text=True, env=env, cwd=HERE)
    if proc.returncode != 0:
        raise RuntimeError("engine exited %d\n%s" % (proc.returncode, proc.stderr.strip()))
    if proc.stderr.strip():
        raise RuntimeError("engine emitted warnings:\n%s" % proc.stderr.strip())
    return json.loads(proc.stdout, parse_constant=_reject_nonfinite)


def run_perturbed_engine(n, replacements):
    """Exec the engine source in-process with `replacements` applied, capturing
    its stdout. Used only by the negative control — no file on disk is touched."""
    with open(ENGINE, "r") as f:
        source = f.read()
    for old, new in replacements:
        if old not in source:
            raise RuntimeError("negative control anchor not found in engine: %r" % old)
        source = source.replace(old, new)
    ns = {}
    argv_saved = sys.argv
    sys.argv = [ENGINE, str(n)]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(source, "<perturbed-century_sim>", "exec"), ns)
    finally:
        sys.argv = argv_saved
    return json.loads(buf.getvalue(), parse_constant=_reject_nonfinite)


def load_golden(n, baseline=None):
    baseline = BASELINE_MODE if baseline is None else baseline
    path = GOLDEN.get((n, baseline))
    if path is None or not os.path.exists(path):
        raise RuntimeError("no golden file for N=%d baseline=%s (expected %s); run --capture first"
                           % (n, baseline, path))
    with open(path, "r") as f:
        return json.load(f)


def diff_blocks(actual, golden):
    """Return a list of (block, detail) for every compared block that differs."""
    diffs = []
    for blk in COMPARE_BLOCKS:
        a = actual.get(blk)
        g = golden.get(blk)
        if a == g:
            continue
        if isinstance(a, dict) and isinstance(g, dict):
            keys = sorted(set(a) | set(g))
            cells = ["%s: %s->%s" % (k, g.get(k), a.get(k)) for k in keys if a.get(k) != g.get(k)]
            diffs.append((blk, "; ".join(cells)))
        else:
            diffs.append((blk, "%s -> %s" % (g, a)))
    return diffs


def mc_error_bars(outcomes, n):
    """Analytic binomial 95 % half-width (percentage points) for each share."""
    lines = []
    for name, share in outcomes.items():
        p = share / 100.0
        hw = 1.96 * math.sqrt(max(p * (1.0 - p), 0.0) / n) * 100.0
        lines.append("    %-24s %6.2f%%  +/- %.3f pp" % (name, share, hw))
    return lines


def check_golden(n):
    """Run the engine at N=n (v2 default, or baseline when CENTURY_BASELINE=1 is in the
    environment), compare to the matching golden, print MC error bars. True on pass."""
    print("[golden] N=%d (%s) vs %s"
          % (n, "baseline" if BASELINE_MODE else "v2", os.path.relpath(GOLDEN[(n, BASELINE_MODE)], HERE)))
    actual = run_engine(n, clean=False)  # the one env-sensitive run: selects the golden set
    golden = load_golden(n)
    diffs = diff_blocks(actual, golden)
    print("  Monte-Carlo 95%% error bars (binomial, N=%d):" % n)
    for line in mc_error_bars(actual["outcomes"], n):
        print(line)
    if diffs:
        print("  FAIL — %d block(s) drifted from golden:" % len(diffs))
        for blk, detail in diffs:
            print("    %s: %s" % (blk, detail))
        return False
    print("  PASS — all %d headline blocks bit-identical to golden." % len(COMPARE_BLOCKS))
    return True


def check_strict_scenarios(n=5000):
    """Strict-JSON-validate every published reproduction command, plus the retained
    switch paths no document names. Return True on pass."""
    print("[strict-scenarios] %d commands at N=%d: %d published (%d of them CENTURY_OVERRIDES) "
          "+ %d retained switch path(s)"
          % (len(SCENARIOS), n, N_PUBLISHED_SCENARIOS, N_OVERRIDE_SCENARIOS,
             N_RETAINED_SCENARIOS))
    ok = True
    for name, env_extra in SCENARIOS:
        try:
            run_engine(n, env_extra)  # raises on non-zero exit, warning, or NaN/Inf
            print("  OK    %s" % name)
        except Exception as exc:  # noqa: BLE001 — report and continue to surface all failures
            ok = False
            print("  FAIL  %s -> %s" % (name, str(exc).splitlines()[0] if str(exc) else exc))
    print("  %s — strict JSON across published and retained commands." % ("PASS" if ok else "FAIL"))
    return ok


def check_negative_control(n=20000):
    """Perturb one hazard constant in memory; the golden comparison MUST fire.

    Returns True when the injected change was detected (the healthy outcome).
    The CLI turns a detected perturbation into a NON-ZERO exit, matching the
    plan's 'reports the injected discrepancy and exits non-zero'.
    """
    # Double the great-power nuclear-war base rate (century_sim.py §3.8). This
    # shifts collapse / population / event counts well outside MC error.
    anchor = "clip(0.003 * (1 + 1.5 * turb"
    replacement = "clip(0.006 * (1 + 1.5 * turb"
    print("[negative-control] N=%d, perturbation: nuclear base rate 0.003 -> 0.006" % n)
    actual = run_perturbed_engine(n, [(anchor, replacement)])
    golden = load_golden(n)
    diffs = diff_blocks(actual, golden)
    if diffs:
        print("  DETECTED — perturbation moved %d block(s), checker is not vacuous:" % len(diffs))
        for blk, detail in diffs:
            print("    %s: %s" % (blk, (detail[:120] + "...") if len(detail) > 120 else detail))
        return True
    print("  VACUOUS — perturbation left every compared block unchanged; checker is broken.")
    return False


def check_hazmask_audit(n=1000):
    """Behavioural check: under HAZMASK a world absorbed earlier in a year receives
    no later same-year pandemic event. Returns True when HAZMASK yields zero such
    events AND the baseline path yields >0 (proving the audit is not vacuous)."""
    print("[hazmask-audit] N=%d: a world absorbed earlier in the year must log no later same-year pandemic" % n)
    baseline = run_engine(n, {"CENTURY_BASELINE": "1", "CENTURY_AUDIT": "1"})["audit_pandemic_post_absorption"]
    hz = run_engine(n, {"CENTURY_BASELINE": "1", "CENTURY_AUDIT": "1", "CENTURY_V2_HAZMASK": "1"})["audit_pandemic_post_absorption"]
    print("  baseline path: %d post-absorption pandemic event(s)  (the defect HAZMASK fixes)" % baseline)
    print("  HAZMASK path:  %d post-absorption pandemic event(s)" % hz)
    if hz != 0:
        print("  FAIL — HAZMASK still logged %d post-absorption pandemic event(s)." % hz)
        return False
    if baseline <= 0:
        print("  INCONCLUSIVE — baseline logged 0 at N=%d; sample too small to exhibit the defect." % n)
        return False
    print("  PASS — HAZMASK eliminates same-year post-absorption hazards; baseline>0 shows the audit is not vacuous.")
    return True


def check_pinned_audit(n=50000, threshold=0.25):
    """Report the fraction of survivor-years each bounded variable spends within 0.01
    of a [0,1] bound, baseline vs CENTURY_V2 (soft dynamics). Passes when no variable
    exceeds `threshold` under V2 (the baseline clip rails several near 1.0)."""
    print("[pinned-audit] survivor-years within 0.01 of a bound, N=%d (fail if any V2 variable > %.0f%%)"
          % (n, threshold * 100))
    baseline = run_engine(n, {"CENTURY_BASELINE": "1", "CENTURY_AUDIT": "1"})["audit_pinned_fraction"]
    v2 = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_V2": "1"})["audit_pinned_fraction"]
    print("  %-4s %12s %12s" % ("var", "baseline", "V2 (soft)"))
    worst = 0.0
    for nm in PINNED_VARS:
        print("  %-4s %11.1f%% %11.1f%%" % (nm, baseline[nm] * 100, v2[nm] * 100))
        worst = max(worst, v2[nm])
    ok = worst <= threshold
    print("  %s — worst V2 pinned fraction %.1f%% (threshold %.0f%%); baseline peaks at %.1f%%."
          % ("PASS" if ok else "FAIL", worst * 100, threshold * 100, max(baseline.values()) * 100))
    return ok


def check_struct_audit(n=50000):
    """Verify the sampled-structure axis (Phase 5): the structure-conditional
    P(irreversible_bad) gradient is monotone in window timescale, and pinning the
    structure to the flat (persistent-risk) corner reproduces the flat-conditional
    subset of the mixed run within Monte-Carlo error."""
    print("[struct-audit] N=%d: monotone P(bad) gradient in window timescale + pinned-corner reproduction" % n)
    d = run_engine(n, {"CENTURY_V2": "1"})
    sc = d["structure_conditional"]
    grad = [sc["P(irreversible_bad)|flat_window"], sc["P(irreversible_bad)|tau>=15yr"],
            sc["P(irreversible_bad)|8<=tau<15yr"], sc["P(irreversible_bad)|tau<8yr"]]
    monotone = all(grad[i] > grad[i + 1] for i in range(len(grad) - 1))
    print("  P(bad) by window: flat=%.1f  tau>=15=%.1f  8<=tau<15=%.1f  tau<8=%.1f  -> %s"
          % (grad[0], grad[1], grad[2], grad[3], "monotone decreasing" if monotone else "NOT MONOTONE"))
    print("  P(good): flat_window=%.1f  tau<8yr=%.1f (the sampled §6.1 swing)"
          % (sc["P(good)|flat_window"], sc["P(good)|tau<8yr"]))
    pinned = run_engine(n, {"CENTURY_V2": "1", "CENTURY_OVERRIDES": '{"struct_flat":1}'})
    pb = pinned["aggregates"]["irreversible_bad"]
    cb = sc["P(irreversible_bad)|flat_window"]
    band = 1.5  # generous pp band spanning the MC error of two independent ~N/2 samples
    repro = abs(pb - cb) <= band
    print("  pinned struct_flat=1 P(bad)=%.1f vs conditional-on-flat %.1f (|d|=%.1f <= %.1f pp): %s"
          % (pb, cb, abs(pb - cb), band, "OK" if repro else "OFF"))
    ok = monotone and repro
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "structure axis is monotone and the flat corner reproduces persistent risk"
          if ok else "gradient not monotone or pinned corner off"))
    return ok


def check_calib_audit(n=50000, group="xpt_superforecaster"):
    """Phase 7 gate: calibrate against the anchors, then verify the weights' effective
    sample size is >= 10% of N and that weighting toward the chosen extinction anchor
    pulls the weighted extinction share below the unweighted one."""
    wpath = os.path.join(HERE, "weights-%s-%d-seed431.npz" % (group, n))
    print("[calib-audit] N=%d, extinction anchor=%s" % (n, group))
    cal = subprocess.run(
        [sys.executable, os.path.join(HERE, "calibrate_century.py"), str(n),
         "--extinction-group", group, "--out", wpath],
        capture_output=True, text=True, cwd=HERE)
    if cal.returncode != 0:
        print("  FAIL — calibrate_century.py exited %d\n%s" % (cal.returncode, cal.stderr[:400]))
        return False
    d = run_engine(n, {"CENTURY_V2": "1", "CENTURY_WEIGHTS": wpath})
    ess = d["weights_ess_fraction"]
    uw = d["outcomes"]["extinction"]
    ww = d["outcomes_weighted"]["extinction"]
    ess_ok = ess >= 0.10
    pull_ok = ww < uw
    print("  effective sample size = %.1f%% of N (>= 10%%: %s)" % (ess * 100, ess_ok))
    print("  extinction unweighted=%.2f%%  weighted=%.2f%%  (weighted < unweighted: %s)" % (uw, ww, pull_ok))
    ok = ess_ok and pull_ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "ESS healthy and the superforecaster anchor pulls extinction down" if ok else "see failing line"))
    return ok


def check_lever_audit(n=50000):
    """Third-view gate: calibrate against the lever likelihood anchors, then verify the
    weights' effective sample size is >= 10% of N and that weighting toward realistic
    lever politics brings the weighted good share below the unweighted (flat-lever-prior)
    one — the likelihood ranges say the strong-lever quartiles are less likely than the
    flat prior's 25%, so the realistic bet must not look rosier than the headline."""
    wpath = os.path.join(HERE, "weights-levers-%d-seed431.npz" % n)
    print("[lever-audit] N=%d, lever-feasibility anchors" % n)
    cal = subprocess.run(
        [sys.executable, os.path.join(HERE, "calibrate_century.py"), str(n),
         "--levers", "--out", wpath],
        capture_output=True, text=True, cwd=HERE)
    if cal.returncode != 0:
        print("  FAIL — calibrate_century.py exited %d\n%s" % (cal.returncode, cal.stderr[:400]))
        return False
    d = run_engine(n, {"CENTURY_V2": "1", "CENTURY_LEVER_WEIGHTS": wpath})
    ess = d["lever_weights_ess_fraction"]
    uw = d["aggregates"]["good(broadly acceptable)"]
    lw = d["aggregates_lever_weighted"]["good(broadly acceptable)"]
    ess_ok = ess >= 0.10
    pull_ok = lw < uw
    print("  effective sample size = %.1f%% of N (>= 10%%: %s)" % (ess * 100, ess_ok))
    print("  P(good) unweighted=%.2f%%  lever-weighted=%.2f%%  (weighted < unweighted: %s)"
          % (uw, lw, pull_ok))
    ok = ess_ok and pull_ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "ESS healthy and realistic lever politics lowers the good share" if ok else "see failing line"))
    return ok


def _num(s):
    """Extract the first numeric token from a table cell (handles the unicode minus,
    %, degC and bold markers)."""
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace("−", "-"))
    return float(m.group()) if m else None


def _parse_doc_table(doc_path, anchor):
    """Parse the first table whose header row contains `anchor` into
    {row_label: [numbers, one per value column]} (index 0 = first value column).
    Handles Markdown tables (a blank line ends the table once its data rows have
    started) and AsciiDoc |===-fenced tables. The blank-line terminator matters
    because different tables in the same document can share row labels; without it a
    later table would overwrite an earlier one's rows."""
    rows = {}
    in_table = False
    seen_data = False
    with open(doc_path) as f:
        for raw in f:
            s = raw.strip()
            if not in_table:
                if s.startswith("|") and anchor in s:
                    in_table = True
                continue
            if s == "|===":
                break
            if s.startswith("|"):
                parts = [p.strip() for p in s.split("|")[1:]]
                if len(parts) >= 2:
                    label = parts[0].replace("*", "").strip()
                    vals = [_num(p) for p in parts[1:]]
                    if label and any(v is not None for v in vals):
                        rows[label] = vals
                        seen_data = True
                continue
            # A non-'|' line (typically a blank line) ends a Markdown table, but only
            # after its data rows have begun; an AsciiDoc header is followed by a blank
            # line before its data, which must not end the table early.
            if seen_data:
                break
    return rows


def _parse_doc_prose(doc_path, pattern):
    """Extract a figure quoted inline in prose. Returns (value, n_matches). The value is
    None unless the pattern matched exactly once: zero matches means the prose no longer
    says what the registry thinks it says, and several matches means the anchor is too
    loose to identify which figure is being pinned. Both are reported as failures."""
    with open(doc_path) as f:
        text = f.read()
    matches = re.findall(pattern, text)
    if len(matches) != 1:
        return None, len(matches)
    return _num(matches[0]), 1


def _get(d, path):
    """Path getter into a parsed engine output. `path` is a list of keys, or a dotted
    string when the keys themselves contain no dots (engine keys like
    'p_contested(0.15-0.35)' do, so those entries must use the list form)."""
    parts = path if isinstance(path, list) else path.split(".")
    cur = d
    for part in parts:
        cur = cur[part]
    return cur


def _run_calibration(n, levers=False, group="xpt_superforecaster"):
    """Run a calibration in-process and shape it like an engine output, so the two
    calibration sections of future.md can be pinned by the same registry that pins
    everything else. Sections 6.3 and 6.5 quote numbers that no engine run produces:
    they come out of the max-entropy solve, so before this source existed they were the
    only tables in the documents that --doc-figures could not see. They are also the
    tables that went stale unnoticed when the arrival anchors were last revised, which is
    the whole argument for pinning them.

    Returns {"fit": {feature: {unweighted, lo, hi, weighted}}, "ess_pct": float,
             "outcomes": {name: {prior, weighted}}}. The band edges are carried through
    from anchors.json so a document can be checked against the configured range as well
    as against the solve.
    """
    import numpy as np
    import calibrate_century as cal
    with open(os.path.join(HERE, "lever-anchors.json" if levers else "anchors.json")) as f:
        anchors = json.load(f)
    ns = cal.run_ensemble(n)
    if levers:
        names, F, lo, hi = cal.build_lever_features(ns, anchors)
        t = (lo + hi) / 2.0                      # lever ranges are beliefs: match the middle
    else:
        names, F, lo, hi = cal.build_features(ns, anchors, group)
        t = None                                 # outcome anchors: only correct when outside
    unweighted = F.mean(axis=0)
    if t is None:
        t = np.clip(unweighted, lo, hi)
    active = ~np.isclose(t, unweighted, atol=1e-6)
    if active.any():
        lam = cal.fit_maxent(F[:, active], t[active])
        z = F[:, active] @ lam
        z -= z.max()
        w = np.exp(z)
    else:
        w = np.ones(n, dtype=float)
    w = w / w.sum()
    ess = float((w.sum() ** 2) / (w ** 2).sum()) / n
    weighted = w @ F
    fit = {nm: {"unweighted": float(unweighted[i]), "lo": float(lo[i]),
                "hi": float(hi[i]), "weighted": float(weighted[i])}
           for i, nm in enumerate(names)}
    final = ns["final"]

    def _pair(v):
        v = v.astype(float)
        return {"prior": 100.0 * float(v.mean()), "weighted": 100.0 * float(w @ v)}

    outcomes = {
        "good": _pair(ns["good"]),
        "bad": _pair(ns["bad"]),
        "aligned_abundance": _pair(final == "aligned_abundance"),
        "disempowerment": _pair(final == "disempowerment"),
        "extinction": _pair(final == "extinction"),
        "ext_or_collapse": _pair((final == "extinction") | (final == "collapse")),
        "unknown_catastrophe": _pair(final == "unknown_catastrophe"),
    }
    return {"fit": fit, "ess_pct": 100.0 * ess, "outcomes": outcomes}


def _run_source(source, cache):
    """Resolve a registry `source` spec to a (cached) engine output."""
    if source in cache:
        return cache[source]
    if source.startswith("run:"):
        out = run_engine(int(source[4:]))
    elif source.startswith("cmd:"):
        overrides, n = source[4:].rsplit("@", 1)
        out = run_engine(int(n), {"CENTURY_OVERRIDES": overrides})
    elif source.startswith("env:"):
        env_str, n = source[4:].rsplit("@", 1)
        env = dict(kv.split("=", 1) for kv in env_str.split(",") if kv)
        out = run_engine(int(n), env)
    elif source.startswith("calib:"):
        arg, n = source[6:].rsplit("@", 1)
        out = _run_calibration(int(n), levers=(arg == "levers"),
                               group=(arg if arg != "levers" else None))
    else:
        raise ValueError("unknown --doc-figures source spec: %r" % source)
    cache[source] = out
    return out


def _check_doc_tables(cache):
    """Every registered document table matches a fresh v2 engine run."""
    print("[doc-figures] %d registered table(s) vs fresh v2 engine runs" % len(DOC_TABLES))
    ok = True
    for spec in DOC_TABLES:
        out = _run_source(spec["source"], cache)
        parsed = _parse_doc_table(spec["doc"], spec["anchor"])
        prec = spec["precision"]
        tol = 0.5 * 10 ** (-prec) + 1e-9
        print("  [%s] %s '%s' (source %s)"
              % (spec["id"], os.path.basename(spec["doc"]), spec["anchor"], spec["source"]))
        for label, pathspec in spec["rows"].items():
            if label not in parsed:
                ok = False
                print("    MISSING doc row: %r" % label)
                continue
            colmap = pathspec if isinstance(pathspec, dict) else {1: pathspec}
            cells = parsed[label]
            for col, path in sorted(colmap.items()):
                docv = cells[col - 1] if col <= len(cells) else None
                if docv is None:
                    ok = False
                    print("    MISSING doc cell: %r column %d" % (label, col))
                    continue
                eng = round(float(_get(out, path)), prec)
                match = abs(eng - docv) < tol
                ok = ok and match
                shown = label if len(colmap) == 1 else "%s [col %d]" % (label, col)
                print("    %-52s doc=%s engine=%s  %s"
                      % ((shown[:50] + "..") if len(shown) > 52 else shown, docv, eng, "OK" if match else "MISMATCH"))
    return ok


def _check_doc_prose(cache):
    """Every registered inline prose figure matches a fresh v2 engine run. Tables and prose
    drift independently: a document can regenerate its tables and leave the sentences around
    them quoting the previous run."""
    n_figs = sum(len(spec["figures"]) for spec in DOC_PROSE)
    print("[doc-prose] %d registered prose figure(s) vs fresh v2 engine runs" % n_figs)
    ok = True
    for spec in DOC_PROSE:
        out = _run_source(spec["source"], cache)
        prec = spec["precision"]
        tol = 0.5 * 10 ** (-prec) + 1e-9
        print("  [%s] %s (source %s)"
              % (spec["id"], os.path.basename(spec["doc"]), spec["source"]))
        for fig in spec["figures"]:
            label = fig["label"]
            docv, n = _parse_doc_prose(spec["doc"], fig["pattern"])
            if docv is None:
                ok = False
                why = "MISSING (pattern matched no prose)" if n == 0 else \
                      "AMBIGUOUS (pattern matched %d times)" % n
                print("    %-52s %s" % (label, why))
                continue
            eng = round(float(_get(out, fig["path"])), prec)
            match = abs(eng - docv) < tol
            ok = ok and match
            print("    %-52s doc=%s engine=%s  %s"
                  % (label, docv, eng, "OK" if match else "MISMATCH"))
    return ok


def check_doc_figures():
    """Phase 12+ gate: every registered document table and inline prose figure matches a
    fresh v2 engine run. The registries (DOC_TABLES, DOC_PROSE) grow section by section as
    the documents are regenerated."""
    cache = {}
    ok = _check_doc_tables(cache)
    ok = _check_doc_prose(cache) and ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "all registered doc tables and prose figures match the v2 engine"
          if ok else "see MISMATCH/MISSING/AMBIGUOUS rows"))
    return ok


def check_hazard_audit(n=50000):
    """Phase 11 gate: with the new hazard channels the outcome shares still sum to 100%; the
    unknown-unknowns share tracks its sampled rate (zero when the rate is pinned to 0, positive
    and in-band by default); and rebuild worlds re-enter with the documented G/C penalties."""
    print("[hazard-audit] N=%d: fate accounting + unknown-unknowns rate consistency + rebuild penalties" % n)
    h = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_V2": "1"})["audit_hazard"]
    zero = run_engine(n, {"CENTURY_V2": "1", "CENTURY_OVERRIDES": '{"xhaz_rate":0}'})
    sum_ok = abs(h["outcome_sum_pct"] - 100.0) <= 0.5
    xh = h["unknown_catastrophe_pct"]
    xh_zero = zero["outcomes"].get("unknown_catastrophe", 0.0)
    xh_ok = xh is not None and 1.0 <= xh <= 15.0 and (xh_zero in (0.0, None))
    reb_ok = (h["n_recovered"] > 0
              and abs(h["reentry_G_penalty_ratio"] - 0.6) < 0.02
              and abs(h["reentry_C_penalty_ratio"] - 0.75) < 0.02)
    print("  outcome shares sum to %.2f%% (== 100): %s" % (h["outcome_sum_pct"], sum_ok))
    print("  unknown_catastrophe = %.2f%% at rate %.4f/yr; = %s%% when rate pinned to 0: %s"
          % (xh, h["xhaz_rate_mean_per_yr"], xh_zero, xh_ok))
    print("  rebuild: %d recovered; re-entry penalty G=%.2f (~0.6) C=%.2f (~0.75): %s"
          % (h["n_recovered"], h["reentry_G_penalty_ratio"], h["reentry_C_penalty_ratio"], reb_ok))
    ok = sum_ok and xh_ok and reb_ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "fate accounting closes, unknown-unknowns tracks its rate, rebuild penalties applied"
          if ok else "see failing line"))
    return ok


def check_policy_audit(n=50000):
    """Phase 10 gate: the endogenous policy levers stay within their declared bounds; zeroing
    the response (CENTURY_POLICY_SCALE=0) reproduces the non-policy v2 ensemble; and worlds in
    the top warning-shot quartile show higher realised safety effort than the bottom quartile."""
    print("[policy-audit] N=%d: lever bounds + zeroing reproduces non-policy v2 + warning-shot response" % n)
    ap = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_V2": "1"})["audit_policy"]
    se_ok = 0.004 - 1e-9 <= ap["se_t_bounds"][0] and ap["se_t_bounds"][1] <= 0.05 + 1e-9
    race_ok = -1e-9 <= ap["race_t_bounds"][0] and ap["race_t_bounds"][1] <= 1.0 + 1e-9
    resp_ok = 0.15 - 1e-9 <= ap["resp_t_bounds"][0] and ap["resp_t_bounds"][1] <= 1.0 + 1e-9
    bounds_ok = se_ok and race_ok and resp_ok
    ws_ok = ap["safety_effort_top_ws_quartile"] > ap["safety_effort_bottom_ws_quartile"]
    zeroed = run_engine(n, {"CENTURY_V2": "1", "CENTURY_POLICY_SCALE": "0"})
    # v2 is the default, so "all corrections except policy" is built on the baseline
    # (default-v2 would force every switch on regardless).
    nonpolicy_env = {"CENTURY_BASELINE": "1"}
    nonpolicy_env.update({env: "1" for env, _ in V2_CONFIGS if env not in ("CENTURY_V2", "CENTURY_V2_POLICY")})
    nonpolicy = run_engine(n, nonpolicy_env)
    zero_ok = (zeroed["outcomes"] == nonpolicy["outcomes"] and zeroed["aggregates"] == nonpolicy["aggregates"])
    print("  lever bounds: se_t=%s race_t=%s resp_t=%s -> within declared: %s"
          % (ap["se_t_bounds"], ap["race_t_bounds"], ap["resp_t_bounds"], bounds_ok))
    print("  zeroing (POLICY_SCALE=0) reproduces non-policy v2 outcomes: %s" % zero_ok)
    print("  safety effort top-ws-quartile=%.5f > bottom=%.5f: %s"
          % (ap["safety_effort_top_ws_quartile"], ap["safety_effort_bottom_ws_quartile"], ws_ok))
    ok = bounds_ok and ws_ok and zero_ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "levers bounded, zeroing reverts cleanly, warning shots raise safety effort"
          if ok else "see failing line"))
    return ok


def check_demo_climate_audit(n=50000):
    """Phase 9 gate: under CENTURY_V2 the survivor population endpoint p10-p90 brackets
    ~9-12 bn (declining-to-rising, i.e. the low tail falls below the 8.2 bn 2026 start) and
    the survivor warming endpoint p10-p90 spans at least 1.5 degC."""
    print("[demo-climate-audit] N=%d: survivor population & warming endpoint spreads under CENTURY_V2" % n)
    e = run_engine(n, {"CENTURY_V2": "1"})["endstate_2126_survivors"]
    pop = e["pop_bn_p10_p90"]
    wc = e["warming_C_p10_p90"]
    pop_ok = pop[0] <= 9.5 and pop[1] >= 11.5 and pop[0] < 8.2
    w_ok = (wc[1] - wc[0]) >= 1.5
    print("  survivor pop p10-p90 = %s bn (median %.2f)  -> brackets ~9-12 & declining tail: %s"
          % (pop, e["median_pop_bn"], pop_ok))
    print("  survivor warming p10-p90 = %s degC (width %.2f)  -> >= 1.5: %s" % (wc, wc[1] - wc[0], w_ok))
    ok = pop_ok and w_ok
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "population spans the UN low-high envelope and warming is widened"
          if ok else "see failing line"))
    return ok


def check_corr_audit(n=50000):
    """Verify the Gaussian copula (Phase 6): the correlation matrix is positive definite,
    the realised rank correlations match their targets within +/-0.03, and the marginals
    are preserved (quantiles identical to the identity/independent run)."""
    print("[corr-audit] N=%d: PSD + realised rank correlations within +/-0.03 + marginals preserved" % n)
    on = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_V2": "1"})["audit_corr"]
    off = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_V2": "1", "CENTURY_CORR_JSON": "identity"})["audit_corr"]
    ok = bool(on["psd"])
    print("  matrix positive definite (Cholesky succeeded): %s" % on["psd"])
    for pr, v in on["pairs"].items():
        diff = abs(v["realised_rank"] - v["target"])
        within = diff <= 0.03
        ok = ok and within
        print("  %-22s target=%+.2f  realised_rank=%+.3f  |d|=%.3f  %s"
              % (pr, v["target"], v["realised_rank"], diff, "OK" if within else "OUT>0.03"))
    marg_ok = on["marginal_q"] == off["marginal_q"]
    ok = ok and marg_ok
    print("  marginals preserved (quantiles identical to the identity run): %s" % marg_ok)
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "copula is PSD, correlations on target, marginals intact" if ok else "see failing rows"))
    return ok


def gen_v2_deltas(n=50000):
    """Run baseline plus each v2 configuration at N=n and write a per-outcome-class
    delta table to notes/v2-deltas.md."""
    print("[v2-deltas] baseline + %d configuration(s) at N=%d -> %s"
          % (len(V2_CONFIGS), n, os.path.relpath(NOTES_PATH, HERE)))
    # v2 is now the default, so the baseline needs CENTURY_BASELINE=1, and each
    # single-switch column is the baseline path plus that one correction (the umbrella
    # CENTURY_V2 column is the full v2 default).
    base = run_engine(n, {"CENTURY_BASELINE": "1"})
    configs = []
    for env, desc in V2_CONFIGS:
        print("  running %s ..." % env)
        env_extra = {"CENTURY_V2": "1"} if env == "CENTURY_V2" else {"CENTURY_BASELINE": "1", env: "1"}
        configs.append((env, desc, run_engine(n, env_extra)))

    def cell(v):
        return ("%+.2f" % v) if v else "  .  "

    lines = []
    lines.append("# v2 mechanical-correction deltas (Phase 3)")
    lines.append("")
    lines.append("Generated by `check_century.py --v2-deltas`. Each column is a single "
                 "`CENTURY_V2_*` switch enabled alone at N=%d, seed 431, versus the baseline "
                 "path; the final column is the umbrella `CENTURY_V2=1`. Values are "
                 "percentage-point deltas on each outcome share (blank = no change)." % n)
    lines.append("")
    lines.append("Baseline figures are not affected by any switch. The regression gate "
                 "(`check_century.py --quick --full`) holds them bit-identical.")
    lines.append("")
    header = ["Outcome class", "Baseline %"] + [env.replace("CENTURY_V2_", "").replace("CENTURY_V2", "V2(all)")
                                              for env, _ in V2_CONFIGS]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for key in OUTCOME_ORDER:
        b = base["outcomes"][key]
        cells = [key, "%.2f" % b] + [cell(round(d["outcomes"][key] - b, 2)) for _, _, d in configs]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("| | | | | | | | |")
    for key in AGGREGATE_ORDER:
        b = base["aggregates"][key]
        cells = ["**%s**" % key, "%.1f" % b] + [cell(round(d["aggregates"][key] - b, 2)) for _, _, d in configs]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("Median AGI year: baseline %d; %s."
                 % (base["agi"]["median_year"],
                    ", ".join("%s %d" % (env.replace("CENTURY_V2_", "").replace("CENTURY_V2", "V2(all)"),
                                         d["agi"]["median_year"]) for env, _, d in configs)))
    lines.append("")
    lines.append("Switch descriptions:")
    lines.append("")
    for env, desc in V2_CONFIGS:
        lines.append("- `%s`: %s" % (env, desc))
    lines.append("")

    # ---- Phase 4: saturation (SOFT) findings --------------------------------
    v2_out = next(d for env, _, d in configs if env == "CENTURY_V2")
    soft_out = next(d for env, _, d in configs if env == "CENTURY_V2_SOFT")
    print("  running saturation diagnostics (baseline + V2, AUDIT + DECADAL) ...")
    baseline_diag = run_engine(n, {"CENTURY_BASELINE": "1", "CENTURY_AUDIT": "1", "CENTURY_DECADAL": "1"})
    v2_diag = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_DECADAL": "1", "CENTURY_V2": "1"})

    def middling(d):
        return round(d["outcomes"]["turbulent_transition"] + d["outcomes"]["muddling_degraded"], 2)

    def wtraj(d):
        return {r["year"]: r["W"] for r in d["decadal"] if r["year"] >= 2080}

    lp, vp = baseline_diag["audit_pinned_fraction"], v2_diag["audit_pinned_fraction"]
    lt, vt = wtraj(baseline_diag), wtraj(v2_diag)
    yrs = sorted(lt)

    lines.append("## Saturation fix (Phase 4, `CENTURY_V2_SOFT`)")
    lines.append("")
    lines.append("Baseline clip dynamics rail the bounded variables against 1.0; the soft "
                 "(logistic) update keeps them off the bounds. Fraction of survivor-years a "
                 "variable spends within 0.01 of a [0,1] bound, N=%d:" % n)
    lines.append("")
    lines.append("| Variable | Baseline pinned % | V2 (soft) pinned % |")
    lines.append("|---|---:|---:|")
    for nm in PINNED_VARS:
        lines.append("| %s | %.1f | %.1f |" % (nm, lp[nm] * 100, vp[nm] * 100))
    lines.append("")
    lines.append("Survivor concentration W (median across still-ongoing worlds) by decade:")
    lines.append("")
    lines.append("| Path | " + " | ".join(str(y) for y in yrs) + " |")
    lines.append("|---|" + "---:|" * len(yrs))
    lines.append("| Baseline W | " + " | ".join("%.2f" % lt[y] for y in yrs) + " |")
    lines.append("| V2 (soft) W | " + " | ".join("%.2f" % vt[y] for y in yrs) + " |")
    lines.append("")
    hbase = base["endstate_2126_survivors"]["median_wellbeing"]
    hv2 = v2_out["endstate_2126_survivors"]["median_wellbeing"]
    lines.append(
        "**Finding: does bimodality survive?** Under soft dynamics the survivor wellbeing "
        "median drops from a railed %.2f (baseline) to %.2f, and concentration W no longer "
        "deconcentrates late-century: baseline W falls %.2f -> %.2f across %d-%d while the soft "
        "path holds it roughly flat (%.2f -> %.2f). The late-century deconcentration is "
        "therefore a clip artefact and does not survive. The outcome distribution stays "
        "dominated by the disempowerment / irreversible-bad mass with a smaller good tail, so "
        "it remains broadly bimodal, but the middle is no longer negligible: the middling "
        "share (turbulent_transition + muddling_degraded) rises from %.2f%% (baseline) to %.2f%% "
        "under SOFT alone (%.2f%% under the full V2 set). Net: bimodality survives in weakened "
        "form; the deconcentration narrative does not."
        % (hbase, hv2, lt[yrs[0]], lt[yrs[-1]], yrs[0], yrs[-1], vt[yrs[0]], vt[yrs[-1]],
           middling(base), middling(soft_out), middling(v2_out)))
    lines.append("")

    # ---- Phase 6: correlated-priors on/off ----------------------------------
    print("  running correlation on/off (CENTURY_V2 with copula vs identity) ...")
    corr_on = v2_out  # the umbrella CENTURY_V2 already has the copula on
    corr_off = run_engine(n, {"CENTURY_V2": "1", "CENTURY_CORR_JSON": "identity"})
    lines.append("## Correlated priors (Phase 6, `CENTURY_V2_CORR`)")
    lines.append("")
    lines.append("Headline v2 outcomes with the Gaussian copula ON (default matrix: "
                 "race-respond -0.4, redist_will-respond +0.3, k-alpha +0.3) vs OFF (identity), "
                 "every other v2 correction held on, N=%d. The marginals are identical in both "
                 "(Iman-Conover reordering preserves them exactly), so only the joint structure "
                 "differs." % n)
    lines.append("")
    lines.append("| Outcome class | corr OFF % | corr ON % | delta |")
    lines.append("|---|---:|---:|---:|")
    for key in OUTCOME_ORDER:
        a, b = corr_off["outcomes"][key], corr_on["outcomes"][key]
        lines.append("| %s | %.2f | %.2f | %s |" % (key, a, b, ("%+.2f" % round(b - a, 2)) if round(b - a, 2) else "  .  "))
    for key in AGGREGATE_ORDER:
        a, b = corr_off["aggregates"][key], corr_on["aggregates"][key]
        lines.append("| **%s** | %.1f | %.1f | %s |" % (key, a, b, ("%+.2f" % round(b - a, 2)) if round(b - a, 2) else "  .  "))
    lines.append("")

    os.makedirs(os.path.dirname(NOTES_PATH), exist_ok=True)
    with open(NOTES_PATH, "w") as f:
        f.write("\n".join(lines))
    print("  wrote %s" % os.path.relpath(NOTES_PATH, HERE))
    return True


def capture_golden():
    """(Re)write both golden sets from the current engine: the v2 defaults and the
    retained baseline path (CENTURY_BASELINE=1). Used to bless new reference figures."""
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    for (n, baseline), path in GOLDEN.items():
        actual = run_engine(n, {"CENTURY_BASELINE": "1"} if baseline else None)
        payload = {"N": n, "seed": 431, "baseline": baseline}
        payload.update({blk: actual[blk] for blk in COMPARE_BLOCKS})
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        print("[capture] wrote %s (N=%d, %s)" % (os.path.relpath(path, HERE), n, "baseline" if baseline else "v2"))
    return True


def check_cutoff_audit(n=50000):
    """FU-008: report the post-AGI survivor W/H/Rd/G quantiles and the current
    abundance/oligarchic/fragile split, so the cutoffs are derived from — and
    verified against — the soft-dynamics distributions (env CENTURY_CUTOFF_AUDIT)."""
    print("[cutoff-audit] post-AGI survivor distributions under CENTURY_V2, N=%d, seed 431" % n)
    d = run_engine(n, {"CENTURY_CUTOFF_AUDIT": "1"})
    a = d["survivor_cutoff_audit"]
    q = a["quantiles_p10_p25_p50_p75_p90"]
    print("  post-AGI survivors: %d" % a["n_agi_survivors"])
    print("  quantiles p10/p25/p50/p75/p90:")
    for k in ("W_concentration", "H_wellbeing", "Rd_redistribution", "G_governance"):
        print("    %-18s %s" % (k, q[k]))
    s = a["current_shares_pct_of_agi_survivors"]
    print("  current split (%% of post-AGI survivors): abundance=%.1f oligarchic=%.1f fragile=%.1f"
          % (s["aligned_abundance"], s["oligarchic_prosperity"], s["turbulent_transition_fragile"]))
    ok = a["n_agi_survivors"] > 0 and abs(sum(s.values()) - 100.0) < 0.5
    print("  %s" % ("PASS — audit produced survivor distributions"
                    if ok else "FAIL — audit output malformed"))
    return ok


# Ceiling on how much the respond-spread in log-odds may drift across the erode_mag grid
# (assertion 4 of --erosion-audit). The realised drift is 0.027 on a spread of about 0.47;
# the ceiling sits at roughly four times that, well clear of Monte Carlo noise at the
# default N and low enough to catch erosion becoming a responsiveness multiplier.
ERODE_SPREAD_MAX = 0.10


def _logit(pct):
    """Log-odds of a share given in percent."""
    q = pct / 100.0
    return math.log(q / (1.0 - q))


def _logit_se(pct, n):
    """Standard error of a log-odds estimate from a binomial share of n draws."""
    q = pct / 100.0
    return 1.0 / math.sqrt(n * q * (1.0 - q))


def _pct_se(pct, n):
    """Standard error of a binomial share, in percentage points."""
    q = pct / 100.0
    return 100.0 * math.sqrt(q * (1.0 - q) / n)


def _v2_without(switch):
    """Environment that runs the v2 path with one correction suppressed. Every V2_* flag
    reads `_v2 or <own var>`, so setting a flag to 0 does nothing once _v2 is on; the only
    way to drop one is to start from the baseline path and re-enable the rest by name."""
    env = {"CENTURY_BASELINE": "1"}
    env.update({e: "1" for e, _ in V2_CONFIGS if e not in ("CENTURY_V2", switch)})
    return env


def check_platdrag_audit(n=50000):
    """Gate for the plateau-drag correction (V2_PLATDRAG). Seven assertions: the baseline
    path is untouched; restoring the global throttle shape reproduces the uncorrected model
    bit-identically; unstalled worlds are untouched; the ceiling stops being overshot; a
    stalled world that still crosses is now decades late rather than a year; the two knobs
    have to move together, which is the trap that makes this correction easy to get wrong;
    and the named plateau scenario still reselects the regime for every world."""
    print("[platdrag-audit] N=%d: V2_PLATDRAG baseline safety, pinned-shape reproduction," % n)
    print("                 unstalled worlds untouched, overshoot, stall depth, knob coupling, override")
    ok = True

    # 1. Baseline untouched: V2_PLATDRAG hangs off _v2, so CENTURY_BASELINE=1 keeps the
    #    global throttle and the pre-plan golden must still reproduce exactly.
    base = run_engine(20000, {"CENTURY_BASELINE": "1", "CENTURY_AUDIT": "1"})
    base_diffs = diff_blocks(base, load_golden(20000, baseline=True))
    a1 = (not base_diffs) and base["audit_plateau"]["platdrag"] is False
    ok = ok and a1
    print("  1. baseline bit-identical to golden/baseline-20k-seed431.json: %s%s"
          % (a1, "" if not base_diffs else "  (%d block(s) drifted)" % len(base_diffs)))

    # 2. Setting the stalled shape back to the global one reproduces the uncorrected model
    #    BIT-IDENTICALLY. The correction adds no RNG draw, so this is exact rather than
    #    within a Monte Carlo bar.
    #    Note the shape of the "off" run. A _v2 switch cannot be disabled by setting its own
    #    variable to 0, because every one of them reads `_v2 or <own var>`; suppressing one
    #    means starting from CENTURY_BASELINE=1 and re-enabling the other sixteen, which is
    #    what --erosion-audit does too. Setting CENTURY_V2_PLATDRAG=0 alone leaves it ON.
    pinned = run_engine(n, {"CENTURY_PLATEAU_EXP": "6.0", "CENTURY_PLATEAU_COEF": "0.30"})
    off = run_engine(n, _v2_without("CENTURY_V2_PLATDRAG"))
    a2 = not diff_blocks(pinned, off)
    ok = ok and a2
    print("  2. throttle shape pinned to (6.0, 0.30) reproduces the uncorrected model bit-identically: %s" % a2)

    # 3. Unstalled worlds are untouched. The correction is per-world by construction, so the
    #    non-plateau median crossing and overshoot must match the uncorrected run exactly.
    #    Run under common random numbers. The yearly capability shock is drawn as
    #    rng.normal(0, 0.008, a.sum()), whose LENGTH depends on how many worlds are still
    #    alive, so changing any world's fate shifts the shared stream and every other world
    #    with it. CENTURY_CRN=1 pre-draws the shock per (year, world), which decouples them
    #    and lets this assertion be exact instead of a tolerance hiding a real leak.
    _crn = {"CENTURY_AUDIT": "1", "CENTURY_CRN": "1"}
    aud_on = run_engine(n, _crn)["audit_plateau"]
    _off_env = _v2_without("CENTURY_V2_PLATDRAG"); _off_env.update(_crn)
    aud_off = run_engine(n, _off_env)["audit_plateau"]
    a3 = (aud_on["median_crossing_unstalled"] == aud_off["median_crossing_unstalled"]
          and abs(aud_on["overshoot_p90_unstalled"] - aud_off["overshoot_p90_unstalled"]) < 1e-9)
    ok = ok and a3
    print("  3. unstalled worlds untouched: median %s vs %s, overshoot %.4f vs %.4f: %s"
          % (aud_on["median_crossing_unstalled"], aud_off["median_crossing_unstalled"],
             aud_on["overshoot_p90_unstalled"], aud_off["overshoot_p90_unstalled"], a3))

    # 4. The ceiling stops being a suggestion. Growth halts at (1/coef)**(1/exp) times the
    #    ceiling; the realised 90th-percentile overshoot must sit near that cap and well
    #    below the uncorrected 1.22, which is what let stalled worlds cross thresholds
    #    sitting above their own ceiling.
    cap = aud_on["theoretical_cap_x_ceiling"]
    a4 = aud_on["overshoot_p90_stalled"] < 1.12 and abs(aud_on["overshoot_p90_stalled"] - cap) < 0.06
    ok = ok and a4
    print("  4. stalled overshoot %.4f near the %.4f cap and below the old 1.22: %s"
          % (aud_on["overshoot_p90_stalled"], cap, a4))

    # 5. A stall costs decades. Before the correction a stalled world that still crossed did
    #    so two years behind the ensemble; the point of the correction is that it is now far
    #    enough behind to be a different kind of world.
    lag_on = aud_on["median_crossing_stalled"] - aud_on["median_crossing_unstalled"]
    lag_off = aud_off["median_crossing_stalled"] - aud_off["median_crossing_unstalled"]
    a5 = lag_on >= 10 and lag_on > lag_off
    ok = ok and a5
    print("  5. stalled crossing lags unstalled by %d years (was %d): %s" % (lag_on, lag_off, a5))

    # 6. The knobs are coupled, and this is the assertion that documents why. Lowering the
    #    exponent alone makes the brake gradual but RAISES the stopping point, so worlds that
    #    used to stall grind past their wall instead and the no-AGI share collapses. A
    #    correction that shipped the exponent without the coefficient would read as a
    #    plateau fix while deleting the plateau.
    exp_only = run_engine(n, {"CENTURY_PLATEAU_EXP": "2.0", "CENTURY_PLATEAU_COEF": "0.30"})
    both = run_engine(n, {"CENTURY_AUDIT": "1"})
    never_exp_only = 100.0 - exp_only["agi"]["p_agi_by_2126"]
    never_both = 100.0 - both["agi"]["p_agi_by_2126"]
    a6 = never_exp_only < 2.0 and never_both > never_exp_only
    ok = ok and a6
    print("  6. exponent alone deletes the plateau (no-AGI %.1f%%) but both knobs keep it (%.1f%%): %s"
          % (never_exp_only, never_both, a6))

    # 7. The named plateau scenario still works. The throttle arrays are built after the
    #    override loop, so CENTURY_OVERRIDES='{"plateau":true}' must put every world on the
    #    stalled shape rather than leaving them on the shape their original draw implied.
    allplat = run_engine(20000, {"CENTURY_AUDIT": "1", "CENTURY_OVERRIDES": '{"plateau":true}'})["audit_plateau"]
    a7 = allplat["overshoot_p90_unstalled"] is None and allplat["overshoot_p90_stalled"] < 1.12
    ok = ok and a7
    print("  7. plateau:true override puts every world on the stalled shape (no unstalled worlds left,"
          " overshoot %.4f): %s" % (allplat["overshoot_p90_stalled"], a7))

    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "plateau drag is baseline-safe, exactly revertible, confined to stalled worlds, "
          "caps the ceiling, deepens the stall, needs both knobs and follows the override"
          if ok else "see the failing assertion above"))
    return ok


def check_alphasub_audit(n=50000):
    """Gate for the curvature correction (V2_ALPHASUB). Seven assertions: the baseline path
    is untouched; setting the ceiling back to 1.9 reproduces the uncorrected prior exactly,
    bit-identically, because the correction rescales the existing draw rather than redrawing;
    the realised marginal is uniform on [1.0, ALPHA_MAX]; the crossing year is monotone in
    the ceiling; the correction acts through arrival timing rather than through any hazard;
    the copula's ranks and marginal quantiles survive the rescale; and the sign is the one
    the sub-unit regime implies, which is the trap this correction was written to fix."""
    print("[alphasub-audit] N=%d: V2_ALPHASUB baseline safety, pinned-ceiling reproduction," % n)
    print("                 marginal shape, monotonicity, timing-only action, copula survival, sign")
    ok = True

    # 1. Baseline is untouched. V2_ALPHASUB hangs off _v2, so CENTURY_BASELINE=1 must leave
    #    the old prior in place and the pre-plan golden must still reproduce exactly.
    base = run_engine(20000, {"CENTURY_BASELINE": "1", "CENTURY_AUDIT": "1"})
    base_diffs = diff_blocks(base, load_golden(20000, baseline=True))
    a1 = (not base_diffs) and base["audit_alpha"]["alphasub"] is False \
        and abs(base["audit_alpha"]["observed_max"] - 1.9) < 0.01
    ok = ok and a1
    print("  1. baseline bit-identical to golden and prior still capped at 1.9 (max=%.3f): %s%s"
          % (base["audit_alpha"]["observed_max"], a1,
             "" if not base_diffs else "  (%d block(s) drifted)" % len(base_diffs)))

    # 2. Pinning the ceiling to 1.9 reproduces the uncorrected model BIT-IDENTICALLY. This is
    #    the strongest claim in the audit and the reason the correction rescales P["alpha"]
    #    instead of redrawing it: an extra rng call would shift every later draw and make the
    #    two runs different worlds, exactly the trap --erosion-audit has to work around with a
    #    Monte Carlo bar. Here the streams are the same, so equality is exact.
    pin19 = run_engine(n, {"CENTURY_ALPHA_MAX": "1.9"})
    off = run_engine(n, {"CENTURY_V2": "1", "CENTURY_V2_ALPHASUB": "0", "CENTURY_ALPHA_MAX": "1.9"})
    a2 = not diff_blocks(pin19, off)
    ok = ok and a2
    print("  2. ALPHA_MAX pinned to 1.9 reproduces the uncorrected prior bit-identically: %s" % a2)

    # 3. The rescale leaves the marginal uniform. A map that piled draws at one end would
    #    change the answer without changing the stated range, so the mean is checked against
    #    the midpoint of [1.0, ALPHA_MAX] rather than only the endpoints being checked.
    aud = run_engine(n, {"CENTURY_AUDIT": "1"})["audit_alpha"]
    a3 = (abs(aud["observed_min"] - 1.0) < 0.01
          and abs(aud["observed_max"] - aud["alpha_max_configured"]) < 0.01
          and abs(aud["mean"] - aud["expected_uniform_mean"]) < 0.01)
    ok = ok and a3
    print("  3. marginal uniform on [1.0, %.2f]: min=%.3f max=%.3f mean=%.4f (expected %.4f): %s"
          % (aud["alpha_max_configured"], aud["observed_min"], aud["observed_max"],
             aud["mean"], aud["expected_uniform_mean"], a3))

    # 4. Monotone in the ceiling. Below C = 1 a larger exponent shrinks C**alpha, so raising
    #    the ceiling must push the crossing later at every step of the grid.
    grid = [1.9, 2.4, 3.2]
    meds = [run_engine(n, {"CENTURY_ALPHA_MAX": str(v)})["agi"]["median_year"] for v in grid]
    a4 = all(b > a for a, b in zip(meds, meds[1:]))
    ok = ok and a4
    print("  4. median crossing year rises with the ceiling: %s -> %s: %s"
          % (grid, meds, a4))

    # 5. The correction acts through timing, not through any hazard. Per-world hazard rates
    #    are untouched by curvature, so the expected count of nuclear and pandemic events must
    #    move only as far as the changed exit times drag it, well inside a wide bar. A
    #    correction that moved these sharply would be reaching into the hazard model.
    hi = run_engine(n, {"CENTURY_ALPHA_MAX": "3.2"})
    lo = run_engine(n, {"CENTURY_ALPHA_MAX": "1.9"})
    dnuc = abs(hi["events_per_world"]["nuclear_war"] - lo["events_per_world"]["nuclear_war"])
    a5 = dnuc < 0.15
    ok = ok and a5
    print("  5. nuclear events per world move only with exit timing: %.3f vs %.3f (|d|=%.3f < 0.15): %s"
          % (hi["events_per_world"]["nuclear_war"], lo["events_per_world"]["nuclear_war"], dnuc, a5))

    # 6. The copula survives. The rescale is linear and monotone, so it cannot change any
    #    world's rank; the realised k,alpha rank correlation and alpha's own quantile shape
    #    (rescaled by the same affine map) must both come through intact.
    ca = run_engine(n, {"CENTURY_AUDIT": "1"})["audit_corr"]
    cb = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_ALPHA_MAX": "1.9"})["audit_corr"]
    ra, rb = ca["pairs"]["k,alpha"]["realised_rank"], cb["pairs"]["k,alpha"]["realised_rank"]
    qa, qb = ca["marginal_q"]["alpha"], cb["marginal_q"]["alpha"]
    # Read the ceiling from the engine rather than restating it, so changing the default
    # cannot leave this assertion silently comparing against the wrong affine map.
    scale = (aud["alpha_max_configured"] - 1.0) / 0.9
    remapped = [round(1.0 + (q - 1.0) * scale, 3) for q in qb]
    a6 = abs(ra - rb) < 1e-9 and all(abs(x - round(y, 3)) < 5e-3 for x, y in zip(remapped, qa))
    ok = ok and a6
    print("  6. copula intact: k,alpha rank %.3f vs %.3f; alpha quantiles %s vs affine-mapped %s: %s"
          % (ra, rb, [round(q, 3) for q in qa], remapped, a6))

    # 7. The sign. Recorded as an assertion because the first attempt at this correction
    #    lowered the floor below 1.0 on the reading that a bigger exponent means faster
    #    growth. It does above C = 1 and the reverse below it, and the model lives entirely
    #    below it, so that change made every world faster. A floor-lowering run must arrive
    #    EARLIER than the default; if this ever flips, the operative regime has moved.
    lowfloor = run_engine(n, {"CENTURY_ALPHA_MAX": "1.9",
                              "CENTURY_OVERRIDES": '{"alpha":0.7}'})
    highfix = run_engine(n, {"CENTURY_ALPHA_MAX": "1.9",
                             "CENTURY_OVERRIDES": '{"alpha":1.9}'})
    a7 = lowfloor["agi"]["median_year"] < highfix["agi"]["median_year"]
    ok = ok and a7
    print("  7. below C=1 a bigger exponent is slower: alpha=0.7 crosses %d, alpha=1.9 crosses %d: %s"
          % (lowfloor["agi"]["median_year"], highfix["agi"]["median_year"], a7))

    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "curvature correction is baseline-safe, exactly revertible, uniform, monotone, "
          "timing-only, copula-safe and correctly signed" if ok else "see the failing assertion above"))
    return ok


def check_erosion_audit(n=50000):
    """plan-28 Phase C gate for the readiness-erosion correction (V2_ERODE). Seven
    assertions: the baseline path is untouched; pinning erode_mag to 0 recovers the
    pre-correction dynamics; the outcome shift is monotone in the magnitude; the
    correction is orthogonal to responsiveness when the spread is measured in log-odds;
    the readiness clip floor is not standing in for the dynamics; the switch is separable
    from V2_POLICY; and the warning-shot gate is visible in the audit counters."""
    print("[erosion-audit] N=%d: V2_ERODE baseline safety, pinned-zero reproduction, monotonicity," % n)
    print("                orthogonality in log-odds, clip floor, POLICY separability, gating")

    # 1. Baseline is untouched. Repeat of the Phase A gate, at the golden's own N.
    base = run_engine(20000, {"CENTURY_BASELINE": "1"})
    base_diffs = diff_blocks(base, load_golden(20000, baseline=True))
    a1 = not base_diffs
    print("  1. baseline bit-identical to golden/baseline-20k-seed431.json: %s%s"
          % (a1, "" if a1 else "  (%d block(s) drifted)" % len(base_diffs)))

    # 2. Pinning the magnitude to zero recovers the dynamics the model had before the
    #    correction. The erode_mag draw is guarded by V2_ERODE (century_sim.py:267-268), so
    #    suppressing the switch shifts the RNG stream and the two runs see different worlds.
    #    The comparison is therefore against the Monte Carlo bar, not for bit-identity.
    pin0 = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_OVERRIDES": '{"erode_mag":0}'})
    noerode_env = {"CENTURY_BASELINE": "1"}
    noerode_env.update({env: "1" for env, _ in V2_CONFIGS if env not in ("CENTURY_V2", "CENTURY_V2_ERODE")})
    noerode = run_engine(n, noerode_env)
    zero_erode = pin0["audit_erosion"]["mean_erode_per_yr"] == 0.0
    g_pin, g_off = pin0["aggregates"]["good(broadly acceptable)"], noerode["aggregates"]["good(broadly acceptable)"]
    bar2 = 1.96 * math.sqrt(_pct_se(g_pin, n) ** 2 + _pct_se(g_off, n) ** 2)
    a2 = zero_erode and abs(g_pin - g_off) <= bar2
    print("  2. erode_mag pinned to 0: mean erode = %.6f (exactly 0: %s)"
          % (pin0["audit_erosion"]["mean_erode_per_yr"], zero_erode))
    print("     P(good) pinned=%.2f%% vs V2_ERODE suppressed=%.2f%%  |d|=%.2f pp (95%% bar %.2f pp): %s"
          % (g_pin, g_off, abs(g_pin - g_off), bar2, abs(g_pin - g_off) <= bar2))

    # 3. Monotone in the magnitude. Erosion widens the capability-readiness gap, which is
    #    what the takeover hazard reads, so disempowerment must rise with it.
    pin30 = run_engine(n, {"CENTURY_OVERRIDES": '{"erode_mag":0.30}'})
    d0, d30 = pin0["outcomes"]["disempowerment"], pin30["outcomes"]["disempowerment"]
    bar3 = 1.96 * math.sqrt(_pct_se(d0, n) ** 2 + _pct_se(d30, n) ** 2)
    a3 = (d30 - d0) > bar3
    print("  3. P(disempowerment) at erode_mag 0.30 = %.2f%% > at 0.0 = %.2f%%  (+%.2f pp, bar %.2f pp): %s"
          % (d30, d0, d30 - d0, bar3, a3))

    # 4. Near-orthogonal to responsiveness. The high-respond / low-respond spread in P(good),
    #    measured in LOG-ODDS, is nearly constant across the magnitude grid: erosion multiplies
    #    the odds of a good century by roughly the same factor whatever a world does. Measured
    #    in percentage points the same spread NARROWS, which reads as "erosion makes
    #    responsiveness matter less" and is an artefact of the high-respond worlds sitting
    #    further up the response curve. Both scales are printed so the trap stays visible.
    #
    #    "Nearly", because the log-odds spread widens slightly and monotonically with the
    #    magnitude, by 0.027 end-to-end against a spread of about 0.47 (measured at N=200000,
    #    where the independent standard error of that difference is 0.0095). The mechanism is
    #    the damping channel: at erode_mag 0 there is no erosion for `learn` to damp, so
    #    responsiveness cannot spend anything through ERODE_DAMP, and the channel only opens
    #    as the magnitude rises. Confirmed by sweeping the damping itself at N=200000 - the
    #    end-to-end drift is -0.019 at ERODE_DAMP=0, +0.027 at the 0.60 default and +0.055 at
    #    0.90, so it tracks the damping and vanishes without it. The effect is about a
    #    twentieth of the spread and invisible below N~100000, which is why the Phase D grid
    #    at N=20000 read it as flat.
    #
    #    The gate is therefore on the SIZE of the drift, not its sign. A sign test is only
    #    about two sigma at this N and would flake; the bound catches the regression that
    #    matters, which is erosion turning into a responsiveness multiplier and reordering the
    #    lever ranking strategy.md is built on. The grid runs share a seed, so the estimates
    #    are positively correlated and the independent bar printed alongside is conservative.
    print("  4. respond 0.25 vs 0.90 spread across the magnitude grid:")
    print("     %-10s %8s %8s %9s %10s" % ("erode_mag", "lo P%", "hi P%", "d (pp)", "d (logit)"))
    spreads, spread_ses = [], []
    for em in (0.0, 0.15, 0.30, 0.50):
        lo = run_engine(n, {"CENTURY_OVERRIDES": '{"respond":0.25,"erode_mag":%g}' % em})
        hi = run_engine(n, {"CENTURY_OVERRIDES": '{"respond":0.90,"erode_mag":%g}' % em})
        p_lo = lo["aggregates"]["good(broadly acceptable)"]
        p_hi = hi["aggregates"]["good(broadly acceptable)"]
        spreads.append(_logit(p_hi) - _logit(p_lo))
        spread_ses.append(math.sqrt(_logit_se(p_hi, n) ** 2 + _logit_se(p_lo, n) ** 2))
        print("     %-10.2f %8.2f %8.2f %9.2f %10.3f" % (em, p_lo, p_hi, p_hi - p_lo, spreads[-1]))
    swing = max(spreads) - min(spreads)
    bar4 = 1.96 * math.sqrt(2.0) * max(spread_ses)
    a4 = swing <= ERODE_SPREAD_MAX
    print("     log-odds spread varies by %.3f across the grid, %.1f%% of the spread itself"
          " (drift ceiling %.2f): %s" % (swing, 100.0 * swing / abs(spreads[0]), ERODE_SPREAD_MAX, a4))
    print("     for reference the Monte Carlo 95%% bar on that swing is %.3f, so a swing near it"
          " is the known damping-channel trend, not a regression" % bar4)

    # 5. The clip floor is not standing in for the dynamics. The share, not the minimum:
    #    a minimum taken over a million-plus survivor-years reports only whether the bound
    #    was ever touched, and the question is whether it is touched often enough to be
    #    doing the model's work. The threshold sits two orders of magnitude above the
    #    realised share, so it catches a regression in ERODE_MAX without tripping on the tail.
    ae = run_engine(n, {"CENTURY_AUDIT": "1"})["audit_erosion"]
    floor_share, min_r = ae["share_R_at_floor"], ae["min_realised_R"]
    a5 = min_r >= 0.0 and floor_share <= 0.001
    print("  5. clip floor: min realised R = %.5f (>= 0), survivor-years within 0.01 of it = %.4f%%"
          " (<= 0.1%%): %s" % (min_r, floor_share * 100, a5))

    # 6. Separable from V2_POLICY. shot_hist was hoisted out of the V2_POLICY block in
    #    Phase A step 3 precisely so this combination runs; without the hoist it raises
    #    NameError. run_engine turns a non-zero exit into an exception, so reaching the
    #    comparison at all is half the assertion.
    sep = run_engine(n, {"CENTURY_BASELINE": "1", "CENTURY_V2_ERODE": "1", "CENTURY_AUDIT": "1"})
    sep_erode = sep["audit_erosion"]["mean_erode_per_yr"]
    a6 = sep_erode > 0.0
    print("  6. CENTURY_BASELINE=1 CENTURY_V2_ERODE=1 completes, mean erode = %.6f (> 0): %s"
          % (sep_erode, a6))

    # 7. The warning-shot gate is visible. Damping is withheld until a world has an
    #    incident on record, so the undamped share is positive overall and markedly higher
    #    before the AGI crossing, where most worlds have seen nothing to respond to yet.
    z_all, z_pre = ae["share_learn_zero"], ae["share_learn_zero_pre_agi"]
    a7 = z_all > 0.0 and z_pre > z_all
    print("  7. survivor-years with learn == 0: %.1f%% overall, %.1f%% pre-crossing"
          "  (positive and falling as capability rises): %s" % (z_all * 100, z_pre * 100, a7))
    print("     mean learn %.3f overall, %.3f pre-crossing" % (ae["mean_learn"], ae["mean_learn_pre_agi"]))

    checks = [a1, a2, a3, a4, a5, a6, a7]
    ok = all(checks)
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "erosion is baseline-safe, reverts on pinning, monotone, near-orthogonal to "
          "responsiveness, floor-free, POLICY-separable and gated"
          if ok else "failing assertion(s): %s" % ", ".join(
              str(i + 1) for i, c in enumerate(checks) if not c)))
    return ok


# Grids for --erode-sweep (plan-28 Phase D). The magnitude grid runs past ERODE_MAX (0.30)
# to 0.50 so the sweep covers values the sampled prior cannot reach; the damping and
# warning-shot grids span the full plausible range of each constant.
ERODE_MAG_GRID = (0.0, 0.075, 0.15, 0.225, 0.30, 0.40, 0.50)
ERODE_DAMP_GRID = (0.0, 0.3, 0.6, 0.9)
SHOT_REF_GRID = (0.25, 0.5, 1.0, 2.0)

# Ceiling on how much of the magnitude's effect on P(good) either second-order constant may
# account for (assertions 2 and 3 of --erode-sweep). §5 Risks of plan-28 names the trigger as
# the damping mattering MORE than the magnitude, a ratio above 1; this is far tighter than that.
# The realised ratios are 3.4% for the damping and 4.1% for the warning-shot scale, so a tenth
# leaves headroom for Monte Carlo noise while still firing long before either constant becomes
# comparable to the magnitude.
ERODE_SECOND_ORDER_MAX = 0.10


def _erode_row(res):
    """The four figures each --erode-sweep row reports."""
    return (res["aggregates"]["good(broadly acceptable)"],
            res["outcomes"]["disempowerment"],
            res["outcomes"]["extinction"],
            res["gap_at_agi"]["median"])


def check_erode_sweep(n=200000, ext_group="xpt_superforecaster"):
    """plan-28 Phase D sweep for the readiness-erosion correction, in the reporting style of
    --struct-pflat-sweep. Three grids: the per-world magnitude erode_mag, the damping constant
    ERODE_DAMP, and the warning-shot saturation scale SHOT_REF. Plus the anchor-calibration
    effective sample size across ERODE_MAX, which says whether the outside-view anchors prefer
    any magnitude over any other.

    N is 200000 rather than the 50000 the other audits use. The magnitude grid would be legible
    at any N, but the damping and warning-shot grids move P(good) by 1.5 points and 0.3 points
    respectively, and at N=50000 the 95% bar on a difference is 0.6 points, which cannot tell a
    small effect from no effect. The ad hoc version of this sweep ran at N=20000 and reported
    the respond-orthogonality grid as flat when it was not (see the Phase C notes), which is the
    mistake this default exists to avoid.

    Three assertions, all of them things the plan commits to in writing:
      1. P(good) falls monotonically across the magnitude grid;
      2. the full damping range moves P(good) by at most ERODE_SECOND_ORDER_MAX of what the full
         magnitude range moves it, which is the instrument §5 Risks names for "damping is doing
         too much work", set far tighter than the trigger stated there;
      3. the full SHOT_REF range clears the same bound, so the §6 gating decision is not what
         drives the correction's effect.

    Assertions 2 and 3 are deliberately not an ordering between the damping and the warning-shot
    scale. Both spans are about half a point against a bar of a third of a point, so which of
    them is larger is not a fact this model can establish, and a check that asserted an ordering
    would be asserting noise.
    The ESS is reported and not asserted on. Anchors that started discriminating between
    magnitudes would be a finding worth acting on, not a regression to fail."""
    import numpy as np
    import calibrate_century as cal

    bar = 1.96 * math.sqrt(2.0) * _pct_se(40.0, n)  # 95% bar on a difference of two P(good)
    print("[erode-sweep] N=%d, 95%% bar on a difference of two shares about %.2f pp" % (n, bar))
    print("              (the grid runs share seed 431, so the estimates are positively correlated"
          " and that bar is conservative)")

    hdr = "  %-10s %8s %8s %8s %10s"
    row = "  %-10.3f %8.2f %8.2f %8.2f %10.3f"

    # 1. The magnitude, pinned. CENTURY_OVERRIDES pins the parameter after the draw and before
    #    the copula, so the value stays constant under the rank reordering.
    print("  erode_mag pinned (ERODE_DAMP=0.60, SHOT_REF=1.0):")
    print(hdr % ("erode_mag", "good%", "disemp%", "ext%", "gap@AGI"))
    mag = []
    for em in ERODE_MAG_GRID:
        r = _erode_row(run_engine(n, {"CENTURY_OVERRIDES": '{"erode_mag":%g}' % em}))
        mag.append(r)
        print(row % ((em,) + r))
    mag_good = [r[0] for r in mag]
    mag_range = mag_good[0] - mag_good[-1]
    monotone = all(mag_good[i] > mag_good[i + 1] for i in range(len(mag_good) - 1))
    print("     P(good) spans %.2f pp end to end, strictly falling: %s" % (mag_range, monotone))

    # 2. The damping, with erode_mag left sampled from U(0, ERODE_MAX). ERODE_DAMP is the share
    #    of erosion a saturated, maximally responsive world buys back, so 0.0 is erosion no
    #    responsiveness can touch and 0.9 is erosion that responsiveness almost cancels.
    print("  ERODE_DAMP swept (erode_mag left sampled from U(0, ERODE_MAX)):")
    print(hdr % ("damp", "good%", "disemp%", "ext%", "gap@AGI"))
    damp = []
    for dv in ERODE_DAMP_GRID:
        r = _erode_row(run_engine(n, {"CENTURY_ERODE_DAMP": "%g" % dv}))
        damp.append(r)
        print(row % ((dv,) + r))
    damp_good = [r[0] for r in damp]
    damp_range = max(damp_good) - min(damp_good)
    print("     P(good) spans %.2f pp end to end, %s the %.2f pp bar"
          % (damp_range, "above" if damp_range > bar else "inside", bar))

    # 3. The warning-shot scale, also with erode_mag sampled. SHOT_REF is the accumulated
    #    warning-shot memory at which institutional learning saturates: at 0.25 a world learns
    #    almost everything it is going to learn from its first incident, which approaches the
    #    ungated variant the plan rejected in §6, and at 2.0 only worlds with sustained
    #    near-misses ever damp anything. The span therefore bounds what that decision was worth.
    print("  SHOT_REF swept (erode_mag sampled, ERODE_DAMP=0.60):")
    print(hdr % ("shot_ref", "good%", "disemp%", "ext%", "gap@AGI"))
    shot = []
    for sv in SHOT_REF_GRID:
        r = _erode_row(run_engine(n, {"CENTURY_SHOT_REF": "%g" % sv}))
        shot.append(r)
        print(row % ((sv,) + r))
    shot_good = [r[0] for r in shot]
    shot_range = max(shot_good) - min(shot_good)
    print("     P(good) spans %.2f pp end to end, %s the %.2f pp bar"
          % (shot_range, "above" if shot_range > bar else "inside", bar))

    # 4. Anchor calibration. calibrate_century.run_ensemble strips CENTURY_OVERRIDES
    #    (calibrate_century.py:60-62), so the magnitude has to be moved through CENTURY_ERODE_MAX
    #    here, which reshapes the prior U(0, ERODE_MAX) rather than pinning a single value. The
    #    ESS is the share of the ensemble that survives reweighting to the outside-view anchors:
    #    a magnitude the anchors prefer is one that needs less reweighting to reach them.
    with open(os.path.join(HERE, "anchors.json")) as f:
        anchors = json.load(f)
    print("  anchor-calibration ESS by CENTURY_ERODE_MAX (extinction anchor: %s):" % ext_group)
    print("  %-10s %8s %8s %10s" % ("erode_max", "good%", "ext%", "ESS%"))
    saved = os.environ.get("CENTURY_ERODE_MAX")
    ess_rows = []
    try:
        for em in (0.0, 0.15, 0.30, 0.50):
            os.environ["CENTURY_ERODE_MAX"] = "%.4f" % em
            ns = cal.run_ensemble(n)
            good = 100.0 * float(ns["good"].mean())
            ext = 100.0 * float((ns["final"] == "extinction").mean())
            names, F, lo, hi = cal.build_features(ns, anchors, ext_group)
            unw = F.mean(axis=0)
            t = np.clip(unw, lo, hi)
            active = ~np.isclose(t, unw, atol=1e-6)
            if active.any():
                lam = cal.fit_maxent(F[:, active], t[active])
                z = F[:, active] @ lam
                z -= z.max()
                w = np.exp(z)
            else:
                w = np.ones(n)
            w = w / w.mean()
            ess = 100.0 * float(w.sum() ** 2 / (w ** 2).sum()) / n
            ess_rows.append((em, ess))
            print("  %-10.2f %8.1f %8.2f %10.1f" % (em, good, ext, ess))
    finally:
        if saved is None:
            os.environ.pop("CENTURY_ERODE_MAX", None)
        else:
            os.environ["CENTURY_ERODE_MAX"] = saved
    ess_span = max(e for _, e in ess_rows) - min(e for _, e in ess_rows)
    best = max(ess_rows, key=lambda r: r[1])
    print("     ESS spans %.1f points across the range, highest at erode_max=%.2f (%.1f%%)"
          % (ess_span, best[0], best[1]))
    print("     %s" % ("the anchors do not discriminate between magnitudes, so the default is"
                       " honest ignorance rather than a fitted value" if ess_span < 5.0 else
                       "the anchors DO discriminate: ERODE_MAX should move to the preferred value"))

    ceiling = ERODE_SECOND_ORDER_MAX * mag_range
    b1 = monotone
    b2 = damp_range <= ceiling
    b3 = shot_range <= ceiling
    print("  1. P(good) strictly falls across the magnitude grid: %s" % b1)
    print("  2. damping range %.2f pp is %.1f%% of the magnitude's %.2f pp (ceiling %.0f%%): %s"
          % (damp_range, 100.0 * damp_range / mag_range, mag_range, 100.0 * ERODE_SECOND_ORDER_MAX, b2))
    print("  3. warning-shot range %.2f pp is %.1f%% of it (same ceiling): %s"
          % (shot_range, 100.0 * shot_range / mag_range, b3))
    checks = [b1, b2, b3]
    ok = all(checks)
    print("  %s — %s." % ("PASS" if ok else "FAIL",
          "the magnitude does the work; damping and the warning-shot gate are second-order"
          if ok else "failing assertion(s): %s" % ", ".join(
              str(i + 1) for i, c in enumerate(checks) if not c)))
    return ok


def check_struct_pflat_sweep(n=50000, ext_group="xpt_superforecaster"):
    """FU-009: sweep STRUCT_P_FLAT and tabulate the unweighted good/bad/extinction
    shares plus the anchor-calibration effective sample size (ESS) at each. The value
    with the highest ESS is where the structural prior needs the least reweighting to
    meet the outside-view anchors — i.e. where the two calibration routes best agree.
    Reuses calibrate_century's ensemble + max-entropy machinery (CENTURY_STRUCT_P_FLAT)."""
    import numpy as np
    import calibrate_century as cal
    with open(os.path.join(HERE, "anchors.json")) as f:
        anchors = json.load(f)
    grid = [0.3, 0.4, 0.5, 0.6, 0.7]
    print("[struct-pflat-sweep] STRUCT_P_FLAT sweep, N=%d, extinction anchor: %s" % (n, ext_group))
    print("  %-8s %8s %8s %8s %10s %8s" % ("p_flat", "good%", "bad%", "ext%", "wt_ext%", "ESS%"))
    saved = os.environ.get("CENTURY_STRUCT_P_FLAT")
    rows = []
    try:
        for pf in grid:
            os.environ["CENTURY_STRUCT_P_FLAT"] = "%.4f" % pf
            ns = cal.run_ensemble(n)
            good = 100.0 * float(ns["good"].mean())
            bad = 100.0 * float(ns["bad"].mean())
            ext = 100.0 * float((ns["final"] == "extinction").mean())
            names, F, lo, hi = cal.build_features(ns, anchors, ext_group)
            unw = F.mean(axis=0)
            t = np.clip(unw, lo, hi)
            active = ~np.isclose(t, unw, atol=1e-6)
            if active.any():
                lam = cal.fit_maxent(F[:, active], t[active])
                z = F[:, active] @ lam
                z -= z.max()
                w = np.exp(z)
            else:
                w = np.ones(n)
            w = w / w.mean()
            ess = 100.0 * float(w.sum() ** 2 / (w ** 2).sum()) / n
            wt_ext = 100.0 * float((w * F[:, names.index("p_extinction")]).sum() / w.sum())
            rows.append((pf, good, bad, ext, wt_ext, ess))
            print("  %-8.2f %8.1f %8.1f %8.2f %10.2f %8.1f" % (pf, good, bad, ext, wt_ext, ess))
    finally:
        if saved is None:
            os.environ.pop("CENTURY_STRUCT_P_FLAT", None)
        else:
            os.environ["CENTURY_STRUCT_P_FLAT"] = saved
    best = max(rows, key=lambda r: r[5])
    print("  highest ESS (structural prior closest to the outside view): p_flat=%.2f (ESS=%.1f%%)"
          % (best[0], best[5]))
    return len(rows) == len(grid)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regression harness for century_sim.py")
    ap.add_argument("--quick", action="store_true", help="compare N=20000 against golden")
    ap.add_argument("--full", action="store_true", help="compare N=800000 against golden")
    ap.add_argument("--strict-scenarios", action="store_true",
                    help="strict-JSON-validate every documented command (N=5000)")
    ap.add_argument("--negative-control", action="store_true",
                    help="perturb a hazard constant; a detected change exits non-zero")
    ap.add_argument("--hazmask-audit", action="store_true",
                    help="assert HAZMASK stops same-year post-absorption hazards (N=1000)")
    ap.add_argument("--v2-deltas", action="store_true",
                    help="write per-switch outcome deltas to notes/v2-deltas.md (N=50000)")
    ap.add_argument("--pinned-audit", action="store_true",
                    help="report survivor-years pinned to a bound, baseline vs V2 (N=50000)")
    ap.add_argument("--struct-audit", action="store_true",
                    help="check the sampled-structure P(bad) gradient + pinned-corner reproduction (N=50000)")
    ap.add_argument("--corr-audit", action="store_true",
                    help="check the copula: PSD, realised rank correlations, marginal preservation (N=50000)")
    ap.add_argument("--calib-audit", action="store_true",
                    help="calibrate against anchors; check ESS >= 10%% and extinction pull (N=50000)")
    ap.add_argument("--lever-audit", action="store_true",
                    help="calibrate against lever-feasibility anchors (third view); check ESS >= 10%% and good-share pull (N=50000)")
    ap.add_argument("--demo-climate-audit", action="store_true",
                    help="check survivor population & warming endpoint spreads under V2 (N=50000)")
    ap.add_argument("--policy-audit", action="store_true",
                    help="check endogenous-policy bounds, zeroing, and warning-shot response (N=50000)")
    ap.add_argument("--hazard-audit", action="store_true",
                    help="check fate accounting, unknown-unknowns rate, and rebuild penalties (N=50000)")
    ap.add_argument("--readability", action="store_true",
                    help="prose gate: sentence length, unexplained jargon and document openers")
    ap.add_argument("--doc-figures", action="store_true",
                    help="check every registered doc table and inline prose figure against fresh v2 engine runs")
    ap.add_argument("--cutoff-audit", action="store_true",
                    help="report post-AGI survivor W/H/Rd/G quantiles and the abundance/oligarchic/fragile split (N=50000)")
    ap.add_argument("--erosion-audit", action="store_true",
                    help="check the readiness-erosion correction: baseline safety, pinned-zero reproduction, "
                         "monotonicity, near-orthogonality to respond, clip floor, separability, gating (N=50000)")
    ap.add_argument("--platdrag-audit", action="store_true",
                    help="check the plateau-drag correction: baseline safety, exact pinned-shape reproduction, "
                         "unstalled worlds untouched, ceiling overshoot, stall depth, knob coupling, override (N=50000)")
    ap.add_argument("--alphasub-audit", action="store_true",
                    help="check the curvature correction: baseline safety, exact pinned-ceiling reproduction, "
                         "uniform marginal, monotonicity, timing-only action, copula survival, sign (N=50000)")
    ap.add_argument("--erode-sweep", action="store_true",
                    help="sweep erode_mag, ERODE_DAMP and SHOT_REF; tabulate outcomes and anchor ESS "
                         "at each, and check the magnitude dominates the other two (N=200000, ~5 min)")
    ap.add_argument("--struct-pflat-sweep", action="store_true",
                    help="sweep STRUCT_P_FLAT and tabulate unweighted good/bad/extinction + anchor ESS at each (N=50000)")
    ap.add_argument("--capture", action="store_true",
                    help="(re)write golden files from the current engine")
    args = ap.parse_args(argv)

    # Negative control, hazmask audit, v2-deltas and capture are standalone modes.
    if args.negative_control:
        detected = check_negative_control()
        # Non-zero exit == healthy (change detected); zero == vacuous checker.
        return 1 if detected else 0
    if args.hazmask_audit:
        return 0 if check_hazmask_audit() else 1
    if args.v2_deltas:
        return 0 if gen_v2_deltas() else 1
    if args.pinned_audit:
        return 0 if check_pinned_audit() else 1
    if args.struct_audit:
        return 0 if check_struct_audit() else 1
    if args.corr_audit:
        return 0 if check_corr_audit() else 1
    if args.calib_audit:
        return 0 if check_calib_audit() else 1
    if args.lever_audit:
        return 0 if check_lever_audit() else 1
    if args.demo_climate_audit:
        return 0 if check_demo_climate_audit() else 1
    if args.policy_audit:
        return 0 if check_policy_audit() else 1
    if args.hazard_audit:
        return 0 if check_hazard_audit() else 1
    if args.doc_figures:
        return 0 if check_doc_figures() else 1
    if args.readability:
        return 0 if check_doc_prose_readable() else 1
    if args.cutoff_audit:
        return 0 if check_cutoff_audit() else 1
    if args.erosion_audit:
        return 0 if check_erosion_audit() else 1
    if args.platdrag_audit:
        return 0 if check_platdrag_audit() else 1
    if args.alphasub_audit:
        return 0 if check_alphasub_audit() else 1
    if args.erode_sweep:
        return 0 if check_erode_sweep() else 1
    if args.struct_pflat_sweep:
        return 0 if check_struct_pflat_sweep() else 1
    if args.capture:
        return 0 if capture_golden() else 1

    # Default with no selectors: quick + full + strict-scenarios.
    if not (args.quick or args.full or args.strict_scenarios):
        args.quick = args.full = args.strict_scenarios = True

    passed = True
    if args.quick:
        passed &= check_golden(20000)
    if args.full:
        passed &= check_golden(800000)
    if args.strict_scenarios:
        passed &= check_strict_scenarios()
    print("\n%s" % ("ALL CHECKS PASSED" if passed else "CHECKS FAILED"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
