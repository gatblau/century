#!/usr/bin/env python3
"""
sobol_century.py — variance-based (Sobol) sensitivity for century_sim.py.

The quartile-swing sensitivity in century_sim.py is marginal-only: it moves one parameter
at a time and cannot see interactions such as "safety effort matters more given a race".
This driver replaces it with first-order (S_i) and total-order (S_Ti) Sobol indices for
P(good) and P(disempowerment), estimated with a hand-rolled Saltelli design (Saltelli 2010
first-order, Jansen 1999 total-order estimators) — NumPy only, no SciPy.

The estimator is validated against the analytic Ishigami indices before it is used on the
engine (--self-test). On the engine, each Saltelli sample is a matrix of the 13 continuous
parameters (CORR_VARS order) injected via CENTURY_PARAM_NPZ; plateau, the sampled structure
and the yearly shocks stay internally drawn, so at fixed seed/N those nuisance draws are
COMMON across the (2 + k) evaluations (partial common-random-numbers), which is what makes
the indices converge.

Usage:
  python3 sobol_century.py --self-test           # validate the estimator on Ishigami
  python3 sobol_century.py [--base 8192]          # engine Sobol for P(good) & P(disempowerment)
  python3 sobol_century.py --converge             # 2^13 vs 2^14, report max index drift
  python3 sobol_century.py --notes                # write notes/sobol.md

Runs the engine under CENTURY_V2. Standard library + NumPy only.
"""

import argparse
import contextlib
import io
import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "century_sim.py")
NOTES_PATH = os.path.join(HERE, "notes", "sobol.md")

# The 13 continuous parameters, in the CORR_VARS order century_sim.py expects for injection.
CORR_VARS = ["alpha", "k", "threshold", "R0", "safety_eff", "assist", "race", "respond",
             "concentration0", "redist_will", "bio_defense", "climate_eff", "fragility"]

with open(ENGINE) as _f:
    _ENGINE_SRC = compile(_f.read(), "<century_sim>", "exec")


def sample_marginals(m, rng):
    """Draw an (m, 13) sample from the engine's independent marginal priors (CORR_VARS
    order). Columns are independent, so a Saltelli column-swap yields a valid sample."""
    return np.column_stack([
        rng.uniform(1.0, 1.9, m),                     # alpha
        rng.lognormal(np.log(0.095), 0.60, m),        # k
        rng.uniform(0.68, 0.92, m),                   # threshold
        rng.uniform(0.18, 0.34, m),                   # R0
        rng.uniform(0.004, 0.020, m),                 # safety_eff
        rng.beta(1.6, 2.4, m) * 0.65,                 # assist
        rng.uniform(0.25, 1.0, m),                    # race
        rng.uniform(0.15, 1.0, m),                    # respond
        rng.uniform(0.55, 0.75, m),                   # concentration0
        rng.uniform(0.2, 0.9, m),                     # redist_will
        rng.uniform(0.2, 0.9, m),                     # bio_defense
        rng.uniform(0.3, 1.0, m),                     # climate_eff
        rng.uniform(0.5, 1.5, m),                     # fragility
    ])


def saltelli_design(A, B):
    """Return the k matrices AB_i (column i from B, the rest from A)."""
    k = A.shape[1]
    out = []
    for i in range(k):
        Ab = A.copy()
        Ab[:, i] = B[:, i]
        out.append(Ab)
    return out


def sobol_indices(yA, yB, yABi):
    """First-order (Saltelli 2010) and total-order (Jansen 1999) Sobol indices."""
    varY = np.var(np.concatenate([yA, yB]), ddof=1)
    if varY <= 0:
        z = np.zeros(len(yABi))
        return z, z.copy()
    S = np.array([np.mean(yB * (yAb - yA)) / varY for yAb in yABi])
    ST = np.array([0.5 * np.mean((yA - yAb) ** 2) / varY for yAb in yABi])
    return S, ST


# ---------------------------------------------------------------------------
# Ishigami validation
# ---------------------------------------------------------------------------
def ishigami(X, a=7.0, b=0.1):
    return np.sin(X[:, 0]) + a * np.sin(X[:, 1]) ** 2 + b * (X[:, 2] ** 4) * np.sin(X[:, 0])


def ishigami_analytic(a=7.0, b=0.1):
    pi = math.pi
    V = a * a / 8 + b * pi ** 4 / 5 + b * b * pi ** 8 / 18 + 0.5
    V1 = 0.5 + b * pi ** 4 / 5 + b * b * pi ** 8 / 50
    V2 = a * a / 8
    VT1 = V1 + 8 * b * b * pi ** 8 / 225
    VT3 = 8 * b * b * pi ** 8 / 225
    S = np.array([V1 / V, V2 / V, 0.0])
    ST = np.array([VT1 / V, V2 / V, VT3 / V])
    return S, ST


def self_test(base=2 ** 16, tol=0.02):
    rng = np.random.default_rng(0)
    A = rng.uniform(-np.pi, np.pi, (base, 3))
    B = rng.uniform(-np.pi, np.pi, (base, 3))
    ABi = saltelli_design(A, B)
    yA, yB = ishigami(A), ishigami(B)
    yABi = [ishigami(m) for m in ABi]
    S, ST = sobol_indices(yA, yB, yABi)
    Sa, STa = ishigami_analytic()
    print("[self-test] Ishigami, base=%d, tolerance=%.3f" % (base, tol))
    print("  %-4s %8s %8s | %8s %8s" % ("var", "S(est)", "S(true)", "ST(est)", "ST(true)"))
    ok = True
    for i in range(3):
        ds, dt = abs(S[i] - Sa[i]), abs(ST[i] - STa[i])
        ok = ok and ds <= tol and dt <= tol
        print("  x%-3d %8.3f %8.3f | %8.3f %8.3f   |dS|=%.3f |dST|=%.3f%s"
              % (i + 1, S[i], Sa[i], ST[i], STa[i], ds, dt, "" if ds <= tol and dt <= tol else "  OUT"))
    print("  %s — estimator reproduces the analytic Ishigami indices within %.3f."
          % ("PASS" if ok else "FAIL", tol))
    return ok


# ---------------------------------------------------------------------------
# Engine Sobol
# ---------------------------------------------------------------------------
def eval_engine(param_matrix, tmp_path):
    """Inject the (N, 13) parameter matrix and exec the v2 engine; return per-world
    (good, disempowerment) binary vectors. Nuisance draws (plateau/structure/shocks) are
    seeded at 431, so they are common across calls at equal N (partial CRN)."""
    np.save(tmp_path, param_matrix)
    env_saved = dict(os.environ)
    argv_saved = sys.argv
    for _k in ("CENTURY_WEIGHTS", "CENTURY_AUDIT", "CENTURY_DECADAL", "CENTURY_OVERRIDES"):
        os.environ.pop(_k, None)
    os.environ["CENTURY_V2"] = "1"
    os.environ["CENTURY_CRN"] = "1"     # common random numbers: makes P(good)/P(disemp) deterministic in the params
    os.environ["CENTURY_PARAM_NPZ"] = tmp_path
    sys.argv = [ENGINE, str(param_matrix.shape[0])]
    ns = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(_ENGINE_SRC, ns)
    finally:
        os.environ.clear()
        os.environ.update(env_saved)
        sys.argv = argv_saved
    final = ns["final"]
    good = np.isin(final, ["aligned_abundance", "constrained_flourishing", "oligarchic_prosperity"]).astype(float)
    disemp = (final == "disempowerment").astype(float)
    return good, disemp


def engine_sobol(base, seed=20260706):
    """Return {'good': (S, ST), 'disemp': (S, ST)} for the 13 parameters at Saltelli base N."""
    rng = np.random.default_rng(seed)
    A = sample_marginals(base, rng)
    B = sample_marginals(base, rng)
    ABi = saltelli_design(A, B)
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "pm.npy")
        gA, dA = eval_engine(A, tmp)
        gB, dB = eval_engine(B, tmp)
        gABi, dABi = [], []
        for M in ABi:
            g, d = eval_engine(M, tmp)
            gABi.append(g)
            dABi.append(d)
    return {"good": sobol_indices(gA, gB, gABi), "disemp": sobol_indices(dA, dB, dABi)}


def print_indices(title, S, ST):
    order = np.argsort(-ST)
    print("\n=== %s: Sobol indices (ranked by total-order) ===" % title)
    print("  %-16s %10s %10s %s" % ("parameter", "S_i (1st)", "S_Ti (tot)", "interaction (ST-S)"))
    for i in order:
        print("  %-16s %10.3f %10.3f %+.3f" % (CORR_VARS[i], S[i], ST[i], ST[i] - S[i]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sobol sensitivity for century_sim.py")
    ap.add_argument("--self-test", action="store_true", help="validate the estimator on Ishigami")
    ap.add_argument("--converge", action="store_true", help="2^13 vs 2^14, report max index drift (<0.03)")
    ap.add_argument("--notes", action="store_true", help="write notes/sobol.md")
    ap.add_argument("--base", type=int, default=2 ** 13, help="Saltelli base sample size (default 8192)")
    args = ap.parse_args(argv)

    if args.self_test:
        return 0 if self_test() else 1

    if args.converge:
        print("[converge] running engine Sobol at base 2^13 and 2^14 ...")
        r13 = engine_sobol(2 ** 13)
        r14 = engine_sobol(2 ** 14)
        drift = 0.0
        for tgt in ("good", "disemp"):
            for a, b in zip(r13[tgt], r14[tgt]):      # (S, ST) pairs
                drift = max(drift, float(np.max(np.abs(a - b))))
        print("  max |index(2^13) - index(2^14)| = %.4f  (gate < 0.03: %s)"
              % (drift, "PASS" if drift < 0.03 else "FAIL"))
        print_indices("P(good), base 2^14", *r14["good"])
        print_indices("P(disempowerment), base 2^14", *r14["disemp"])
        se = CORR_VARS.index("safety_eff")
        Sg, STg = r14["good"]
        print("\nsafety_eff on P(good): S_i=%.3f  S_Ti=%.3f  (total > first-order: %s)"
              % (Sg[se], STg[se], STg[se] > Sg[se]))
        return 0 if drift < 0.03 else 1

    # default: single engine Sobol run
    res = engine_sobol(args.base)
    print("[sobol] engine Sobol at base N=%d (CENTURY_V2)" % args.base)
    print_indices("P(good)", *res["good"])
    print_indices("P(disempowerment)", *res["disemp"])
    se = CORR_VARS.index("safety_eff")
    Sg, STg = res["good"]
    print("\nsafety_eff on P(good): S_i=%.3f  S_Ti=%.3f  (interaction, total > first-order: %s)"
          % (Sg[se], STg[se], STg[se] > Sg[se]))
    if args.notes:
        write_notes(res, args.base)
    return 0


def write_notes(res, base):
    Sg, STg = res["good"]
    Sd, STd = res["disemp"]
    se = CORR_VARS.index("safety_eff")
    lines = ["# Sobol sensitivity (Phase 8)", ""]
    lines.append("Variance-based first-order (S_i) and total-order (S_Ti) Sobol indices for "
                 "P(good) and P(disempowerment), hand-rolled Saltelli (NumPy only), engine under "
                 "CENTURY_V2, Saltelli base N=%d. Unlike the marginal quartile swings in "
                 "century_sim.py, these capture interactions (S_Ti > S_i). The estimator is "
                 "validated against the analytic Ishigami indices (`--self-test`)." % base)
    for title, (S, ST) in (("P(good)", (Sg, STg)), ("P(disempowerment)", (Sd, STd))):
        lines += ["", "## %s" % title, "", "| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |",
                  "|---|---:|---:|---:|"]
        for i in np.argsort(-ST):
            lines.append("| %s | %.3f | %.3f | %+.3f |" % (CORR_VARS[i], S[i], ST[i], ST[i] - S[i]))
    interaction = STg[se] > Sg[se]
    lines += ["", "**Interaction finding.** For `safety_eff` on P(good), S_i=%.3f and S_Ti=%.3f. "
              "%s" % (Sg[se], STg[se],
                      "The total-order index exceeds the first-order index, confirming that safety "
                      "effort acts partly through interactions (e.g. safety-effort-given-race) that "
                      "the marginal quartile swings cannot see."
                      if interaction else
                      "The total-order index does NOT exceed the first-order index at this base — the "
                      "interaction the strategy asserts is weak or below estimator resolution here; "
                      "reported for the record rather than asserted."), ""]
    os.makedirs(os.path.dirname(NOTES_PATH), exist_ok=True)
    with open(NOTES_PATH, "w") as f:
        f.write("\n".join(lines))
    print("wrote %s" % os.path.relpath(NOTES_PATH, HERE))


if __name__ == "__main__":
    sys.exit(main())
