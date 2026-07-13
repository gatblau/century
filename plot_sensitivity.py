#!/usr/bin/env python3
"""
plot_sensitivity.py - graphical sensitivity analysis for century_sim.py.

Three figures, all built on the same injection hook that sobol_century.py uses
(CENTURY_PARAM_NPZ overrides the internally sampled continuous priors, so the
Gaussian copula is bypassed and the nuisance draws - plateau, sampled structure,
yearly shocks - stay common under CENTURY_CRN). Every run reuses the calibrated
marginal priors via sobol_century.sample_marginals, so these plots are consistent
with the engine's own priors rather than a hand-rolled grid.

  1. Sobol bar chart (notes/sensitivity_sobol.png)
     First-order S_i and total-order S_Ti per parameter, for P(good) and
     P(irreversibly bad). Bars sorted by S_Ti. The gap S_Ti - S_i is the
     interaction share. This is the honest lever ranking: the Saltelli design
     resamples from independent marginals, so it is not confounded by the copula
     the way the marginal quartile swings in century_sim.py are.

  2. One-way partial-dependence curves (notes/sensitivity_partial_dependence.png)
     For each studied parameter, pin it to a grid of values, draw the other twelve
     from their marginals, and plot P(good) and P(irreversibly bad) against the
     pinned value. Shows the SHAPE of each effect (linear, saturating, threshold),
     which a single swing number cannot. The other inputs are marginalised over
     their independent priors, so each curve is deconfounded.

  3. Two-parameter interaction heatmap (notes/sensitivity_interaction_race_safety.png)
     P(good) and P(irreversibly bad) over a race x safety_eff grid, the pair the
     Sobol interaction term (S_Ti > S_i for safety_eff) points at. Visualises
     "safety effort matters more given a race".

Usage:
  python3 plot_sensitivity.py                 # all three, default resolution
  python3 plot_sensitivity.py --quick         # coarse + small N, for a fast look
  python3 plot_sensitivity.py --only sobol    # one figure: sobol | pd | heatmap
  python3 plot_sensitivity.py --pd-params safety_eff race k

Standard library + NumPy + matplotlib. Reuses sobol_century.py for the engine harness.
"""

import argparse
import contextlib
import io
import os
import sys
import tempfile

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sobol_century as sob

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "notes")

CORR_VARS = sob.CORR_VARS

# Outcome aggregates, matching century_sim.py: okset (good) at line 872 and the
# _bad_classes list at line 875 (extinction / collapse / lockin / disempowerment,
# plus unknown_catastrophe under XHAZ). lockin and unknown_catastrophe contribute
# zero when a configuration never produces them, so listing them is always safe.
GOOD = ["aligned_abundance", "constrained_flourishing", "oligarchic_prosperity"]
BAD = ["extinction", "collapse", "lockin", "disempowerment", "unknown_catastrophe"]


def run_engine(param_matrix, tmp_path):
    """Inject the (N, 13) parameter matrix and exec the v2 engine; return the per-world
    `final` fate array. Mirrors sobol_century.eval_engine's env harness exactly, but
    returns the full fate vector so any aggregate (good / bad / disempowerment) can be
    computed. Nuisance draws are seeded, so they are common across calls at equal N."""
    np.save(tmp_path, param_matrix)
    env_saved = dict(os.environ)
    argv_saved = sys.argv
    for _k in ("CENTURY_WEIGHTS", "CENTURY_AUDIT", "CENTURY_DECADAL", "CENTURY_OVERRIDES"):
        os.environ.pop(_k, None)
    os.environ["CENTURY_V2"] = "1"
    os.environ["CENTURY_CRN"] = "1"
    os.environ["CENTURY_PARAM_NPZ"] = tmp_path
    sys.argv = [sob.ENGINE, str(param_matrix.shape[0])]
    ns = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(sob._ENGINE_SRC, ns)
    finally:
        os.environ.clear()
        os.environ.update(env_saved)
        sys.argv = argv_saved
    return ns["final"]


def frac(final, classes):
    """Fraction of worlds whose fate is in `classes`."""
    return float(np.isin(final, classes).mean())


def marginal_ranges(rng, m=200000):
    """Per-parameter (1st, 99th) percentile of the calibrated marginals, used as the
    sweep range for partial-dependence grids. For the uniform priors this is the true
    support trimmed by 1%; for k (lognormal) and assist (beta) it trims the long tail."""
    big = sob.sample_marginals(m, rng)
    return {name: (float(np.quantile(big[:, i], 0.01)), float(np.quantile(big[:, i], 0.99)))
            for i, name in enumerate(CORR_VARS)}


# ---------------------------------------------------------------------------
# 1. Sobol bar chart
# ---------------------------------------------------------------------------
def plot_sobol(base, out_path):
    print("[sobol] engine Sobol at base N=%d (this runs the engine %d times) ..."
          % (base, 2 + len(CORR_VARS)))
    res = sob.engine_sobol(base)
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), sharey=False)
    panels = [("P(good)", res["good"]), ("P(irreversibly bad): disempowerment only*", res["disemp"])]
    for ax, (title, (S, ST)) in zip(axes, panels):
        order = np.argsort(ST)  # ascending, so largest ends up on top of a barh
        names = [CORR_VARS[i] for i in order]
        y = np.arange(len(order))
        ax.barh(y + 0.19, ST[order], height=0.36, color="#c44", label="S_Ti (total)")
        ax.barh(y - 0.19, S[order], height=0.36, color="#48c", label="S_i (first-order)")
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=9)
        ax.set_xlabel("Sobol index (share of output variance)")
        ax.set_title(title, fontsize=11)
        ax.axvline(0, color="k", lw=0.6)
        ax.grid(axis="x", alpha=0.3)
        ax.legend(loc="lower right", fontsize=9)
    fig.suptitle("Variance-based sensitivity: how much each parameter drives the outcome\n"
                 "(gap between the two bars = interaction share; base N=%d)" % base,
                 fontsize=12)
    fig.text(0.5, 0.005,
             "* the Sobol driver targets P(disempowerment) specifically; it is the single "
             "largest irreversibly-bad class. Bars are deconfounded from the copula.",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print("  wrote %s" % os.path.relpath(out_path, HERE))


# ---------------------------------------------------------------------------
# 2. One-way partial-dependence curves
# ---------------------------------------------------------------------------
def plot_partial_dependence(params, n, points, out_path, rng):
    ranges = marginal_ranges(rng)
    base = sob.sample_marginals(n, rng)  # shared background sample (CRN across grid points)
    idx = {name: CORR_VARS.index(name) for name in params}
    ncol = 3
    nrow = int(np.ceil(len(params) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.0 * ncol, 3.6 * nrow), squeeze=False)
    total = len(params) * points
    done = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "pm.npy")
        for pos, name in enumerate(params):
            lo, hi = ranges[name]
            grid = np.linspace(lo, hi, points)
            pg = np.empty(points)
            pb = np.empty(points)
            col = idx[name]
            for j, val in enumerate(grid):
                M = base.copy()
                M[:, col] = val
                final = run_engine(M, tmp)
                pg[j] = frac(final, GOOD)
                pb[j] = frac(final, BAD)
                done += 1
            print("  [pd] %-14s done (%d/%d grid points run)" % (name, done, total))
            ax = axes[pos // ncol][pos % ncol]
            ax.plot(grid, pg, color="#2a8", lw=2, marker="o", ms=3, label="P(good)")
            ax.plot(grid, pb, color="#c33", lw=2, marker="s", ms=3, label="P(irreversibly bad)")
            ax.set_title(name, fontsize=11)
            ax.set_xlabel("%s (pinned value)" % name)
            ax.set_ylabel("probability")
            ax.set_ylim(0, 1)
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8, loc="best")
        for pos in range(len(params), nrow * ncol):
            axes[pos // ncol][pos % ncol].axis("off")
    fig.suptitle("One-way partial dependence: outcome vs each parameter\n"
                 "(parameter pinned across its 1-99%% range; other twelve drawn from their "
                 "marginals, N=%d per point)" % n, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print("  wrote %s" % os.path.relpath(out_path, HERE))


# ---------------------------------------------------------------------------
# 3. Two-parameter interaction heatmap
# ---------------------------------------------------------------------------
def plot_heatmap(xvar, yvar, n, res, out_path, rng):
    ranges = marginal_ranges(rng)
    base = sob.sample_marginals(n, rng)
    xi, yi = CORR_VARS.index(xvar), CORR_VARS.index(yvar)
    xlo, xhi = ranges[xvar]
    ylo, yhi = ranges[yvar]
    xgrid = np.linspace(xlo, xhi, res)
    ygrid = np.linspace(ylo, yhi, res)
    good = np.empty((res, res))   # [row=y, col=x]
    bad = np.empty((res, res))
    total = res * res
    done = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "pm.npy")
        for r, yv in enumerate(ygrid):
            for c, xv in enumerate(xgrid):
                M = base.copy()
                M[:, xi] = xv
                M[:, yi] = yv
                final = run_engine(M, tmp)
                good[r, c] = frac(final, GOOD)
                bad[r, c] = frac(final, BAD)
                done += 1
            print("  [heat] row %d/%d done (%d/%d cells)" % (r + 1, res, done, total))
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    for ax, field, title, cmap in [(axes[0], good, "P(good)", "viridis"),
                                    (axes[1], bad, "P(irreversibly bad)", "magma")]:
        im = ax.pcolormesh(xgrid, ygrid, field, cmap=cmap, shading="auto", vmin=0, vmax=1)
        cs = ax.contour(xgrid, ygrid, field, levels=6, colors="white", linewidths=0.6, alpha=0.7)
        ax.clabel(cs, inline=True, fontsize=7, fmt="%.2f")
        ax.set_xlabel(xvar)
        ax.set_ylabel(yvar)
        ax.set_title(title, fontsize=11)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Interaction: outcome over %s x %s (other eleven drawn, N=%d per cell)"
                 % (xvar, yvar, n), fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print("  wrote %s" % os.path.relpath(out_path, HERE))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Graphical sensitivity analysis for century_sim.py")
    ap.add_argument("--only", choices=["sobol", "pd", "heatmap"], help="produce a single figure")
    ap.add_argument("--quick", action="store_true", help="coarse grids and small N for a fast look")
    ap.add_argument("--sobol-base", type=int, default=2048, help="Saltelli base N for the Sobol figure")
    ap.add_argument("--pd-params", nargs="+",
                    default=["safety_eff", "race", "threshold", "k", "assist", "respond"],
                    help="parameters to sweep in the partial-dependence figure")
    ap.add_argument("--pd-n", type=int, default=4000, help="worlds per partial-dependence grid point")
    ap.add_argument("--pd-points", type=int, default=21, help="grid points per parameter")
    ap.add_argument("--heat-x", default="race", help="x-axis parameter for the heatmap")
    ap.add_argument("--heat-y", default="safety_eff", help="y-axis parameter for the heatmap")
    ap.add_argument("--heat-n", type=int, default=3000, help="worlds per heatmap cell")
    ap.add_argument("--heat-res", type=int, default=16, help="heatmap grid resolution per axis")
    ap.add_argument("--seed", type=int, default=20260709, help="RNG seed for the background samples")
    args = ap.parse_args(argv)

    if args.quick:
        args.sobol_base = min(args.sobol_base, 512)
        args.pd_n = min(args.pd_n, 1500)
        args.pd_points = min(args.pd_points, 9)
        args.heat_n = min(args.heat_n, 1500)
        args.heat_res = min(args.heat_res, 8)

    for name in args.pd_params + [args.heat_x, args.heat_y]:
        if name not in CORR_VARS:
            ap.error("unknown parameter %r; choose from %s" % (name, ", ".join(CORR_VARS)))

    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    want = {args.only} if args.only else {"sobol", "pd", "heatmap"}
    if "sobol" in want:
        plot_sobol(args.sobol_base, os.path.join(OUT_DIR, "sensitivity_sobol.png"))
    if "pd" in want:
        plot_partial_dependence(args.pd_params, args.pd_n, args.pd_points,
                                os.path.join(OUT_DIR, "sensitivity_partial_dependence.png"), rng)
    if "heatmap" in want:
        plot_heatmap(args.heat_x, args.heat_y, args.heat_n, args.heat_res,
                     os.path.join(OUT_DIR, "sensitivity_interaction_%s_%s.png"
                                  % (args.heat_x, args.heat_y)), rng)
    return 0


if __name__ == "__main__":
    sys.exit(main())
