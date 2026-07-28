#!/usr/bin/env python3
"""
calibrate_century.py — formal calibration of century_sim.py against outside-view anchors.

Turns the informal §1.3 anchor-eyeballing into importance reweighting. It runs the v2
ensemble, scores each world against the anchors in anchors.json via a maximum-entropy
tilt (weights as close to uniform as possible subject to matching the anchor moments),
writes a per-world weights file, and prints an infeasibility report naming any anchor the
model's support cannot reach jointly with the others. CENTURY_WEIGHTS=<weights> then makes
century_sim.py report the anchor-weighted outcome tables next to the unweighted ones, so
the "extinction 15.6% vs outside-view 1-6%" tension becomes a quantified before/after.

A second mode, --levers, produces the THIRD reported view ("the realistic bet"): instead
of the outcome anchors it tilts the ensemble toward the likelihood ranges in
lever-anchors.json — judgement-based probabilities that each social/political choice
actually happens (the world lands in the lever's strong prior quartile) before the
crossing. The same max-entropy machinery applies; CENTURY_LEVER_WEIGHTS=<weights> then
makes century_sim.py report the lever-weighted tables alongside the unweighted (headline)
and anchor-weighted (outside-view) ones.

Usage:
  python3 calibrate_century.py [N] [--extinction-group GROUP] [--levers] [--out PATH]
    N                   number of worlds (default 50000)
    --extinction-group  xpt_superforecaster (default) | domain_expert | ai_researcher
    --levers            calibrate against lever-anchors.json instead of anchors.json
    --out               weights file (default weights-<group>-<N>-seed431.npz,
                        or weights-levers-<N>-seed431.npz under --levers)

Outcome anchors are matched to the nearest edge of their published range (only when the
model's unweighted moment lies outside the range); lever anchors are matched to the
middle of their range, the central estimate. Standard library + NumPy only (no SciPy). The
weights are tied to (seed 431, this N, the CENTURY_V2 switch set): the output is an .npz
carrying the engine's WEIGHTS_FPR configuration fingerprint alongside the weights, and
century_sim.py refuses to load weights whose fingerprint does not match the run — a stale
file after any switch change is a hard error, not a silently wrong weighted table.
"""

import argparse
import contextlib
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "century_sim.py")
ANCHORS = os.path.join(HERE, "anchors.json")
LEVER_ANCHORS = os.path.join(HERE, "lever-anchors.json")


def run_ensemble(n):
    """Exec the v2 engine in-process (seed 431, CENTURY_V2) and return its namespace,
    from which the per-world calibration features are read. No weights/audit/decadal are
    set, so the run is the plain v2 ensemble the CENTURY_WEIGHTS run will reproduce."""
    with open(ENGINE) as f:
        src = f.read()
    env_saved = dict(os.environ)
    argv_saved = sys.argv
    # Hermetic: drop every ambient CENTURY_* variable, then set only what this run intends.
    # The previous allowlist missed CENTURY_BASELINE, so calibrating under it embedded a
    # fingerprint claiming the baseline path while CENTURY_V2 below forced the v2 one.
    for _k in [_k for _k in os.environ if _k.startswith("CENTURY_")]:
        os.environ.pop(_k, None)
    os.environ["CENTURY_V2"] = "1"
    sys.argv = [ENGINE, str(n)]
    ns = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(src, "<century_sim>", "exec"), ns)
    finally:
        os.environ.clear()
        os.environ.update(env_saved)
        sys.argv = argv_saved
    return ns


def build_features(ns, anchors, ext_group):
    """Per-world feature matrix F and each feature's published [lo, hi] target range."""
    agi = ns["agi_year"]
    final = ns["final"]
    ev = ns["ev"]
    # Survivor mask (fate 0 = still ongoing at 2126). The population and warming anchors
    # are survivor-conditional: they describe worlds that avoid a global catastrophe, which
    # is the premise of the UN and IPCC projections. Mean-imputing non-survivors on those
    # two features keeps the matched moment equal to the survivor mean and leaves those
    # rows neutral to the tilt, so the endpoint anchors do not fight the extinction anchor.
    surv = (ns["fate"] == 0)

    def _survivor_conditional(arr):
        col = np.asarray(arr, dtype=float).copy()
        col[~surv] = float(col[surv].mean())
        return col

    feats = {
        "p_agi_by_2035": ((agi > 0) & (agi <= 2035)).astype(float),
        "p_agi_by_2050": ((agi > 0) & (agi <= 2050)).astype(float),
        "p_never_agi_by_2126": (agi < 0).astype(float),
        "p_extinction": (final == "extinction").astype(float),
        "nuclear_events_per_world": ev["nuclear_war"].astype(float),
        "nat_pandemic_events_per_world": ev["nat_pandemic"].astype(float),
        "pop_2126_survivors_bn": _survivor_conditional(ns["POP"]),
        "warming_2126_survivors_C": _survivor_conditional(ns["TEMP"]),
    }
    ranges = {a["feature"]: a["p_range"] for a in anchors["agi_arrival_cdf"]}
    eg = [a for a in anchors["extinction_by_2100"] if a["group"] == ext_group][0]
    ranges["p_extinction"] = eg["p_range"]
    ranges["nuclear_events_per_world"] = anchors["nuclear_per_year"]["count_range"]
    ranges["nat_pandemic_events_per_world"] = anchors["pandemic_per_century"]["count_range"]
    ranges["pop_2126_survivors_bn"] = anchors["population_2126_bn"]["range"]
    ranges["warming_2126_survivors_C"] = anchors["warming_2126_C"]["range"]
    names = list(feats.keys())
    F = np.column_stack([feats[nm] for nm in names])
    lo = np.array([ranges[nm][0] for nm in names], dtype=float)
    hi = np.array([ranges[nm][1] for nm in names], dtype=float)
    return names, F, lo, hi


def build_lever_features(ns, lever_anchors):
    """Per-world indicator matrix F (did this world make the choice?) and each
    feature's judgement [lo, hi] likelihood range. A choice counts as made when the
    world lands in the strong quarter of that lever's prior (top for levers where
    more is better, bottom for race), so every unweighted moment is 0.25 by
    construction and the ranges read as departures from the flat prior."""
    P = ns["P"]
    names, cols, lo, hi = [], [], [], []
    for a in lever_anchors["levers"]:
        v = P[a["lever"]].astype(float)
        q = float(np.quantile(v, a["quantile"]))
        ind = (v >= q) if a["strong_end"] == "top" else (v <= q)
        names.append(a["feature"])
        cols.append(ind.astype(float))
        lo.append(a["p_range"][0])
        hi.append(a["p_range"][1])
    return names, np.column_stack(cols), np.array(lo, dtype=float), np.array(hi, dtype=float)


def fit_maxent(F, t, iters=200, ridge=1e-9):
    """Newton on the max-entropy dual: find lam so softmax(F @ lam) has column means t."""
    lam = np.zeros(F.shape[1])
    for _ in range(iters):
        z = F @ lam
        z -= z.max()
        w = np.exp(z)
        w /= w.sum()
        m = w @ F
        g = m - t
        if np.max(np.abs(g)) < 1e-9:
            break
        Fc = F - m
        H = (w[:, None] * Fc).T @ Fc
        lam = lam - np.linalg.solve(H + ridge * np.eye(len(t)), g)
    return lam


def main(argv=None):
    ap = argparse.ArgumentParser(description="Calibrate century_sim.py against outside-view anchors")
    ap.add_argument("n", nargs="?", type=int, default=50000)
    ap.add_argument("--extinction-group", default="xpt_superforecaster",
                    choices=["xpt_superforecaster", "domain_expert", "ai_researcher"])
    ap.add_argument("--levers", action="store_true",
                    help="calibrate against the lever-feasibility anchors (lever-anchors.json) "
                         "instead of the outside-view outcome anchors — the third reported view")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    n = args.n

    if args.levers:
        with open(LEVER_ANCHORS) as f:
            anchors = json.load(f)
        print("[calibrate] running CENTURY_V2 ensemble, N=%d, lever-feasibility anchors ..." % n)
        ns = run_ensemble(n)
        names, F, lo, hi = build_lever_features(ns, anchors)
    else:
        with open(ANCHORS) as f:
            anchors = json.load(f)
        print("[calibrate] running CENTURY_V2 ensemble, N=%d, extinction anchor: %s ..."
              % (n, args.extinction_group))
        ns = run_ensemble(n)
        names, F, lo, hi = build_features(ns, anchors, args.extinction_group)

    unweighted = F.mean(axis=0)
    if args.levers:
        # The lever ranges are belief intervals for how likely each choice is, so the
        # honest single number is the middle of each range, and every moment is matched
        # to it. (The outcome anchors below are different: they are published bands, so
        # the ensemble is only corrected when it falls outside one.)
        t = (lo + hi) / 2.0
    else:
        # Only push a moment to its nearest range edge if the unweighted value lies outside.
        t = np.clip(unweighted, lo, hi)
    active = ~np.isclose(t, unweighted, atol=1e-6)

    if active.any():
        lam = fit_maxent(F[:, active], t[active])
        z = F[:, active] @ lam
        z -= z.max()
        w = np.exp(z)
    else:
        w = np.ones(n)
    w = w / w.mean()  # normalise to mean 1 (any positive scaling is equivalent downstream)
    ess = float(w.sum() ** 2 / (w ** 2).sum()) / n
    weighted = (w[:, None] * F).sum(axis=0) / w.sum()

    if args.levers:
        print("\n=== lever-feasibility calibration report (third view: the realistic bet) ===")
    else:
        print("\n=== anchor calibration report (extinction group: %s) ===" % args.extinction_group)
    print("%-26s %11s %16s %11s  %s" % ("anchor", "unweighted", "target range", "weighted", "status"))
    infeasible = []
    for i, nm in enumerate(names):
        in_range = lo[i] - 1e-4 <= weighted[i] <= hi[i] + 1e-4
        if not active[i]:
            status = "already on target"
        elif in_range:
            status = "matched to midpoint" if args.levers else "matched to edge"
        else:
            status = "INFEASIBLE (support cannot reach)"
            infeasible.append(nm)
        print("%-26s %11.4f  [%5.3f, %5.3f]  %11.4f  %s"
              % (nm, unweighted[i], lo[i], hi[i], weighted[i], status))
    print("effective sample size: %.1f%% of N (%d / %d)" % (ess * 100, int(ess * n), n))
    if infeasible:
        src = ("lever-feasibility ranges" if args.levers else "outside-view aggregates")
        print("INFEASIBILITY FINDING: no reweighting of this ensemble reaches %s jointly with the "
              "other anchors — a genuine tension between the model's inside-view structure and the "
              "%s, worth citing rather than papering over." % (", ".join(infeasible), src))

    out = args.out or os.path.join(HERE, "weights-%s-%d-seed431.npz"
                                   % ("levers" if args.levers else args.extinction_group, n))
    # meta carries the engine's configuration fingerprint (seed + every ensemble-shaping
    # switch); century_sim.py refuses the file if its own fingerprint differs.
    np.savez(out, w=w, meta=np.array(ns["WEIGHTS_FPR"]))
    print("wrote %s (mean-1 weights, length %d, fingerprinted)" % (os.path.relpath(out, HERE), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
