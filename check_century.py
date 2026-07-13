#!/usr/bin/env python3
"""
check_century.py — regression harness for century_sim.py.

Guards the invariant the accuracy-upgrade plan was built on: the legacy engine
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
# defaults (headline-*) and the retained legacy path (legacy-*, reproduced by
# CENTURY_LEGACY=1). check_golden picks the set from LEGACY_MODE, so
# `check_century.py --full` checks the v2 goldens and `CENTURY_LEGACY=1
# check_century.py --full` checks the legacy goldens.
LEGACY_MODE = bool(int(os.environ.get("CENTURY_LEGACY", "0")))
GOLDEN = {
    (20000, False): os.path.join(GOLDEN_DIR, "headline-20k-seed431.json"),
    (800000, False): os.path.join(GOLDEN_DIR, "headline-800k-seed431.json"),
    (20000, True): os.path.join(GOLDEN_DIR, "legacy-20k-seed431.json"),
    (800000, True): os.path.join(GOLDEN_DIR, "legacy-800k-seed431.json"),
}

# Every documented reproduction command (future.md §9 + strategy.md §6). The
# eight documented CENTURY_OVERRIDES commands (seven distinct — prepared-world
# appears in both documents) are all present, alongside the CENTURY_* switch
# commands, so the strict-JSON gate covers the full published surface.
SCENARIOS = [
    ("headline", {}),
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
N_OVERRIDE_SCENARIOS = sum(1 for name, _ in SCENARIOS if name.startswith("override:"))

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
    ("CENTURY_V2", "umbrella: all fourteen corrections together"),
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
         {"label": "s6 dead heat: redistribution",
          "pattern": r"Redistribution \(" + _PNUM + r"\), the physics plateau",
          "path": "sensitivity_P_good.redist_will.swing"},
         {"label": "s6 dead heat: plateau",
          "pattern": r"the physics plateau \(" + _PNUM + r"\)",
          "path": "sensitivity_P_good.plateau.swing"},
         {"label": "s6 dead heat: responsiveness",
          "pattern": r"institutional responsiveness \(" + _PNUM + r"\) form a statistical dead heat",
          "path": "sensitivity_P_good.respond.swing"},
         {"label": "s6 dead heat: safety effort",
          "pattern": r"ahead of human-paced safety effort \(" + _PNUM + r"\)",
          "path": "sensitivity_P_good.safety_eff.swing"},
         {"label": "s6 time: plateau",
          "pattern": r"The plateau \(" + _PNUM + r"\) shares the top of the table",
          "path": "sensitivity_P_good.plateau.swing"},
         {"label": "s6 time: growth rate k",
          "pattern": r"faster growth \(" + _PNUM + r"\)",
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
          "pattern": r"Institutional responsiveness \(`S_Ti` 0\.108, swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.respond.swing"},
         {"label": "strat s2: safety effort",
          "pattern": r"human-paced safety effort \(`S_Ti` 0\.123, swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.safety_eff.swing"},
         {"label": "strat s2: climate effort",
          "pattern": r"climate effort, for all its " + _PNUM + r" swing",
          "path": "sensitivity_P_good.climate_eff.swing"},
         {"label": "strat s4: share the gains early",
          "pattern": r"share the gains early \(`redist_will`, `S_Ti` 0\.184; swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.redist_will.swing"},
         {"label": "strat s4: cool the race",
          "pattern": r"Cool the race \(`race`, swing " + _PNUM + r"\)",
          "path": "sensitivity_P_good.race.swing"},
     ]},
]


def _reject_nonfinite(name, value):
    # json.loads calls parse_constant only for NaN / Infinity / -Infinity.
    raise ValueError("strict JSON rejects non-finite constant %r" % name)


def run_engine(n, env_extra=None):
    """Run the engine file at N=n as a subprocess and return its parsed JSON.

    RuntimeWarnings are promoted to errors (-W), a non-zero exit or any stderr
    output is a hard failure, and NaN/Infinity are rejected on parse.
    """
    env = dict(os.environ)
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


def load_golden(n, legacy=None):
    legacy = LEGACY_MODE if legacy is None else legacy
    path = GOLDEN.get((n, legacy))
    if path is None or not os.path.exists(path):
        raise RuntimeError("no golden file for N=%d legacy=%s (expected %s); run --capture first"
                           % (n, legacy, path))
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
    """Run the engine at N=n (v2 default, or legacy when CENTURY_LEGACY=1 is in the
    environment), compare to the matching golden, print MC error bars. True on pass."""
    print("[golden] N=%d (%s) vs %s"
          % (n, "legacy" if LEGACY_MODE else "v2", os.path.relpath(GOLDEN[(n, LEGACY_MODE)], HERE)))
    actual = run_engine(n)
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
    """Strict-JSON-validate every documented reproduction command. Return True on pass."""
    print("[strict-scenarios] %d documented commands at N=%d (%d are CENTURY_OVERRIDES commands)"
          % (len(SCENARIOS), n, N_OVERRIDE_SCENARIOS))
    ok = True
    for name, env_extra in SCENARIOS:
        try:
            run_engine(n, env_extra)  # raises on non-zero exit, warning, or NaN/Inf
            print("  OK    %s" % name)
        except Exception as exc:  # noqa: BLE001 — report and continue to surface all failures
            ok = False
            print("  FAIL  %s -> %s" % (name, str(exc).splitlines()[0] if str(exc) else exc))
    print("  %s — strict JSON across documented commands." % ("PASS" if ok else "FAIL"))
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
    events AND the legacy path yields >0 (proving the audit is not vacuous)."""
    print("[hazmask-audit] N=%d: a world absorbed earlier in the year must log no later same-year pandemic" % n)
    legacy = run_engine(n, {"CENTURY_LEGACY": "1", "CENTURY_AUDIT": "1"})["audit_pandemic_post_absorption"]
    hz = run_engine(n, {"CENTURY_LEGACY": "1", "CENTURY_AUDIT": "1", "CENTURY_V2_HAZMASK": "1"})["audit_pandemic_post_absorption"]
    print("  legacy path : %d post-absorption pandemic event(s)  (the defect HAZMASK fixes)" % legacy)
    print("  HAZMASK path: %d post-absorption pandemic event(s)" % hz)
    if hz != 0:
        print("  FAIL — HAZMASK still logged %d post-absorption pandemic event(s)." % hz)
        return False
    if legacy <= 0:
        print("  INCONCLUSIVE — legacy logged 0 at N=%d; sample too small to exhibit the defect." % n)
        return False
    print("  PASS — HAZMASK eliminates same-year post-absorption hazards; legacy>0 shows the audit is not vacuous.")
    return True


def check_pinned_audit(n=50000, threshold=0.25):
    """Report the fraction of survivor-years each bounded variable spends within 0.01
    of a [0,1] bound, legacy vs CENTURY_V2 (soft dynamics). Passes when no variable
    exceeds `threshold` under V2 (the legacy clip rails several near 1.0)."""
    print("[pinned-audit] survivor-years within 0.01 of a bound, N=%d (fail if any V2 variable > %.0f%%)"
          % (n, threshold * 100))
    legacy = run_engine(n, {"CENTURY_LEGACY": "1", "CENTURY_AUDIT": "1"})["audit_pinned_fraction"]
    v2 = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_V2": "1"})["audit_pinned_fraction"]
    print("  %-4s %12s %12s" % ("var", "legacy", "V2 (soft)"))
    worst = 0.0
    for nm in PINNED_VARS:
        print("  %-4s %11.1f%% %11.1f%%" % (nm, legacy[nm] * 100, v2[nm] * 100))
        worst = max(worst, v2[nm])
    ok = worst <= threshold
    print("  %s — worst V2 pinned fraction %.1f%% (threshold %.0f%%); legacy peaks at %.1f%%."
          % ("PASS" if ok else "FAIL", worst * 100, threshold * 100, max(legacy.values()) * 100))
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
    # v2 is the default, so "all corrections except policy" is built on the legacy base
    # (default-v2 would force every switch on regardless).
    nonpolicy_env = {"CENTURY_LEGACY": "1"}
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
    """Run legacy plus each v2 configuration at N=n and write a per-outcome-class
    delta table to notes/v2-deltas.md."""
    print("[v2-deltas] legacy + %d configuration(s) at N=%d -> %s"
          % (len(V2_CONFIGS), n, os.path.relpath(NOTES_PATH, HERE)))
    # v2 is now the default, so the legacy baseline needs CENTURY_LEGACY=1, and each
    # single-switch column is the legacy path plus that one correction (the umbrella
    # CENTURY_V2 column is the full v2 default).
    base = run_engine(n, {"CENTURY_LEGACY": "1"})
    configs = []
    for env, desc in V2_CONFIGS:
        print("  running %s ..." % env)
        env_extra = {"CENTURY_V2": "1"} if env == "CENTURY_V2" else {"CENTURY_LEGACY": "1", env: "1"}
        configs.append((env, desc, run_engine(n, env_extra)))

    def cell(v):
        return ("%+.2f" % v) if v else "  .  "

    lines = []
    lines.append("# v2 mechanical-correction deltas (Phase 3)")
    lines.append("")
    lines.append("Generated by `check_century.py --v2-deltas`. Each column is a single "
                 "`CENTURY_V2_*` switch enabled alone at N=%d, seed 431, versus the legacy "
                 "path; the final column is the umbrella `CENTURY_V2=1`. Values are "
                 "percentage-point deltas on each outcome share (blank = no change)." % n)
    lines.append("")
    lines.append("Legacy figures are not affected by any switch. The regression gate "
                 "(`check_century.py --quick --full`) holds them bit-identical.")
    lines.append("")
    header = ["Outcome class", "Legacy %"] + [env.replace("CENTURY_V2_", "").replace("CENTURY_V2", "V2(all)")
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
    lines.append("Median AGI year: legacy %d; %s."
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
    print("  running saturation diagnostics (legacy + V2, AUDIT + DECADAL) ...")
    legacy_diag = run_engine(n, {"CENTURY_LEGACY": "1", "CENTURY_AUDIT": "1", "CENTURY_DECADAL": "1"})
    v2_diag = run_engine(n, {"CENTURY_AUDIT": "1", "CENTURY_DECADAL": "1", "CENTURY_V2": "1"})

    def middling(d):
        return round(d["outcomes"]["turbulent_transition"] + d["outcomes"]["muddling_degraded"], 2)

    def wtraj(d):
        return {r["year"]: r["W"] for r in d["decadal"] if r["year"] >= 2080}

    lp, vp = legacy_diag["audit_pinned_fraction"], v2_diag["audit_pinned_fraction"]
    lt, vt = wtraj(legacy_diag), wtraj(v2_diag)
    yrs = sorted(lt)

    lines.append("## Saturation fix (Phase 4, `CENTURY_V2_SOFT`)")
    lines.append("")
    lines.append("Legacy clip dynamics rail the bounded variables against 1.0; the soft "
                 "(logistic) update keeps them off the bounds. Fraction of survivor-years a "
                 "variable spends within 0.01 of a [0,1] bound, N=%d:" % n)
    lines.append("")
    lines.append("| Variable | Legacy pinned % | V2 (soft) pinned % |")
    lines.append("|---|---:|---:|")
    for nm in PINNED_VARS:
        lines.append("| %s | %.1f | %.1f |" % (nm, lp[nm] * 100, vp[nm] * 100))
    lines.append("")
    lines.append("Survivor concentration W (median across still-ongoing worlds) by decade:")
    lines.append("")
    lines.append("| Path | " + " | ".join(str(y) for y in yrs) + " |")
    lines.append("|---|" + "---:|" * len(yrs))
    lines.append("| Legacy W | " + " | ".join("%.2f" % lt[y] for y in yrs) + " |")
    lines.append("| V2 (soft) W | " + " | ".join("%.2f" % vt[y] for y in yrs) + " |")
    lines.append("")
    hleg = base["endstate_2126_survivors"]["median_wellbeing"]
    hv2 = v2_out["endstate_2126_survivors"]["median_wellbeing"]
    lines.append(
        "**Finding: does bimodality survive?** Under soft dynamics the survivor wellbeing "
        "median drops from a railed %.2f (legacy) to %.2f, and concentration W no longer "
        "deconcentrates late-century: legacy W falls %.2f -> %.2f across %d-%d while the soft "
        "path holds it roughly flat (%.2f -> %.2f). The late-century deconcentration is "
        "therefore a clip artefact and does not survive. The outcome distribution stays "
        "dominated by the disempowerment / irreversible-bad mass with a smaller good tail, so "
        "it remains broadly bimodal, but the middle is no longer negligible: the middling "
        "share (turbulent_transition + muddling_degraded) rises from %.2f%% (legacy) to %.2f%% "
        "under SOFT alone (%.2f%% under the full V2 set). Net: bimodality survives in weakened "
        "form; the deconcentration narrative does not."
        % (hleg, hv2, lt[yrs[0]], lt[yrs[-1]], yrs[0], yrs[-1], vt[yrs[0]], vt[yrs[-1]],
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
    retained legacy path (CENTURY_LEGACY=1). Used to bless a new baseline."""
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    for (n, legacy), path in GOLDEN.items():
        actual = run_engine(n, {"CENTURY_LEGACY": "1"} if legacy else None)
        payload = {"N": n, "seed": 431, "legacy": legacy}
        payload.update({blk: actual[blk] for blk in COMPARE_BLOCKS})
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        print("[capture] wrote %s (N=%d, %s)" % (os.path.relpath(path, HERE), n, "legacy" if legacy else "v2"))
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
                    help="report survivor-years pinned to a bound, legacy vs V2 (N=50000)")
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
    ap.add_argument("--doc-figures", action="store_true",
                    help="check every registered doc table and inline prose figure against fresh v2 engine runs")
    ap.add_argument("--cutoff-audit", action="store_true",
                    help="report post-AGI survivor W/H/Rd/G quantiles and the abundance/oligarchic/fragile split (N=50000)")
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
    if args.cutoff_audit:
        return 0 if check_cutoff_audit() else 1
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
