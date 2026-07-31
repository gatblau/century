#!/usr/bin/env python3
"""
CENTURY — a stochastic world-model of human history 2026–2126.

Successor to an earlier deterministic scenario engine.
Key upgrades over the reference model:
  1. Monte Carlo over DEEP uncertainty: structural parameters are sampled per
     world from distributions anchored to published expert/superforecaster
     ranges, then each world also gets yearly stochastic shocks.
  2. Capability growth is a tunable-curvature law (linear → hyperbolic) with
     bottleneck ceilings and an explicit plateau regime — no linear default.
  3. Catastrophes are annual HAZARD PROCESSES (nuclear war, engineered and
     natural pandemics, misaligned-AI takeover, totalitarian lock-in), not
     threshold flags. Events have graded severity and absorbing states.
  4. Governance is REACTIVE: warning shots and shocks trigger regulation,
     safety investment and coordination with sampled responsiveness.
  5. Demographics, climate and an economy/distribution block are coupled in.
  6. Outputs: outcome distribution at 2126, AGI-year distribution, takeoff
     gap distribution, event frequencies, population/climate endpoints, and
     stratified sensitivity of P(good outcome) to every sampled parameter.

Vectorised across worlds with numpy: N worlds step year-by-year together.
"""

import numpy as np
import json
import sys
import os

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
SEED = 431
YEARS = np.arange(2026, 2127)          # inclusive of 2126
T = len(YEARS)

rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------
# 1. SAMPLED STRUCTURAL PARAMETERS (deep uncertainty, one draw per world)
# ----------------------------------------------------------------------------
# Anchors (documented in future.md):
#  - AGI timing: aggregate of 2023-25 expert surveys / Metaculus: median
#    ~2033-2047 for "transformative/general" AI, long right tail, real chance
#    of plateau. We sample curvature+rate so the induced crossing distribution
#    has median in the late 2030s with ~10-15% no-AGI-by-2126 mass.
#  - Existential risk anchors: XPT superforecasters ~1% extinction by 2100,
#    domain experts ~6%; AI-researcher median P(extremely bad) ~5%.
#    We do NOT hard-code these; hazard parameters are set so the model's
#    output can be compared against them as a sanity check.

P = {}
P["alpha"]        = rng.uniform(1.0, 1.9, N)     # growth curvature. BELOW C=1, WHICH IS THE WHOLE
                                                 # RUN-UP, A HIGHER EXPONENT IS SLOWER: it shrinks
                                                 # C**alpha. The finite-time-singularity reading of
                                                 # alpha > 1 is true of the equation and false of
                                                 # this model, whose capability starts at 0.35 and
                                                 # whose threshold is 0.68-0.92, so nothing ever
                                                 # reaches the accelerating regime. Misreading this
                                                 # produced three separate defects (future.md 6.6,
                                                 # 6.7, 6.8). V2_ALPHASUB rescales the draw to a
                                                 # higher ceiling; see near CENTURY_ALPHA_MAX. The
                                                 # draw itself never changes.
P["k"]            = rng.lognormal(np.log(0.095), 0.60, N)  # base growth rate at C=1
P["threshold"]    = rng.uniform(0.68, 0.92, N)   # AGI threshold (contested definition)
P["plateau"]      = rng.random(N) < 0.14         # paradigm-stall regime
# Both ceiling variants are pre-drawn (same two calls, same order as before, so the
# stream is unchanged) and kept, so the CENTURY_OVERRIDES plateau branch can reselect
# between them without consuming fresh RNG — an override run stays CRN-comparable
# with the unoverridden run instead of shifting every draw after this point.
_ceil_stall  = rng.uniform(0.50, 0.85, N)
_ceil_nostall = rng.uniform(0.95, 1.15, N)
P["ceiling"]      = np.where(P["plateau"], _ceil_stall, _ceil_nostall)
P["R0"]           = rng.uniform(0.18, 0.34, N)   # initial readiness (alignment+interp+governance)
P["safety_eff"]   = rng.uniform(0.004, 0.020, N) # human-paced readiness gain /yr
P["assist"]       = rng.beta(1.6, 2.4, N) * 0.65 # fraction of capability growth convertible to readiness (AI-assisted alignment)
P["race"]         = rng.uniform(0.25, 1.0, N)    # geopolitical/corporate race intensity
P["respond"]      = rng.uniform(0.15, 1.0, N)    # institutional responsiveness to warning shots
P["concentration0"]= rng.uniform(0.55, 0.75, N)  # initial wealth/power concentration
P["redist_will"]  = rng.uniform(0.2, 0.9, N)     # political capacity for redistribution
P["bio_defense"]  = rng.uniform(0.2, 0.9, N)     # investment in biodefence relative to bio-offence diffusion
P["climate_eff"]  = rng.uniform(0.3, 1.0, N)     # decarbonisation effort multiplier
P["fragility"]    = rng.uniform(0.5, 1.5, N)     # systemic fragility multiplier on all conflict hazards

DECADAL = bool(int(os.environ.get("CENTURY_DECADAL", "0")))
_recovery = bool(int(os.environ.get("CENTURY_RECOVERY", "0")))            # enable all three recovery mechanisms
REC_DIVIDEND = _recovery or bool(int(os.environ.get("CENTURY_DIVIDEND", "0")))  # readiness earns an ongoing capability dividend
REC_WINDOW   = _recovery or bool(int(os.environ.get("CENTURY_WINDOW", "0")))    # takeover hazard decays post-AGI
REC_REACT    = _recovery or bool(int(os.environ.get("CENTURY_REACT", "0")))     # warning shots trigger regulation + safety response

# v2 mechanical corrections (Phase 3 of the accuracy-upgrade plan). Each fixes a
# known modelling error and is individually attributable; CENTURY_V2=1 enables
# all of them. Phase 12 flipped the default: v2 is now the engine path, and
# CENTURY_BASELINE=1 restores the original pre-plan model (all corrections off),
# which stays bit-identical at seed 431. CENTURY_V2=1 still forces v2 explicitly.
BASELINE = bool(int(os.environ.get("CENTURY_BASELINE", "0")))                   # restore the pre-plan baseline model
_v2 = (not BASELINE) or bool(int(os.environ.get("CENTURY_V2", "0")))            # umbrella: v2 is the default path
V2_HAZMASK = _v2 or bool(int(os.environ.get("CENTURY_V2_HAZMASK", "0")))        # absorbed worlds drop out of later same-year hazards
V2_NUKE_R  = _v2 or bool(int(os.environ.get("CENTURY_V2_NUKE_R", "0")))         # nuclear exchange degrades readiness R
V2_NATPAND = _v2 or bool(int(os.environ.get("CENTURY_V2_NATPAND", "0")))        # natural-pandemic rate scales with capability x biodefence
V2_GAPNORM = _v2 or bool(int(os.environ.get("CENTURY_V2_GAPNORM", "0")))        # takeover hazard uses threshold-normalised gap
V2_SUBSTEP = _v2 or bool(int(os.environ.get("CENTURY_V2_SUBSTEP", "0")))        # sub-annual capability integration for fast-takeoff worlds
V2_SOFT    = _v2 or bool(int(os.environ.get("CENTURY_V2_SOFT", "0")))           # logistic (soft-saturating) updates for W/Rd/G/Tr/H
V2_STRUCT  = _v2 or bool(int(os.environ.get("CENTURY_V2_STRUCT", "0")))         # per-world sampled structure (replaces the REC_* binaries)
V2_CORR    = _v2 or bool(int(os.environ.get("CENTURY_V2_CORR", "0")))           # correlate the continuous priors via a Gaussian copula
V2_DEMO    = _v2 or bool(int(os.environ.get("CENTURY_V2_DEMO", "0")))           # sampled fertility trajectory (allows structural decline)
V2_CLIMATE = _v2 or bool(int(os.environ.get("CENTURY_V2_CLIMATE", "0")))        # sampled climate sensitivity + optional tipping
V2_POLICY  = _v2 or bool(int(os.environ.get("CENTURY_V2_POLICY", "0")))         # endogenous, state-responsive safety_eff / race / respond
POLICY_SCALE = float(os.environ.get("CENTURY_POLICY_SCALE", "1"))               # scale of the policy response (0 reproduces non-policy v2)
V2_XHAZ    = _v2 or bool(int(os.environ.get("CENTURY_V2_XHAZ", "0")))           # unknown-unknowns catch-all absorbing hazard
V2_REBUILD = _v2 or bool(int(os.environ.get("CENTURY_V2_REBUILD", "0")))        # collapse becomes non-absorbing (rebuild + recover)
V2_BIOUP   = _v2 or bool(int(os.environ.get("CENTURY_V2_BIOUP", "0")))          # post-AGI bio-offence uplift (AGI-grade biotool misuse)
V2_ERODE   = _v2 or bool(int(os.environ.get("CENTURY_V2_ERODE", "0")))          # capability growth erodes containment/evaluation readiness
V2_ALPHASUB = _v2 or bool(int(os.environ.get("CENTURY_V2_ALPHASUB", "0")))     # curvature prior reaches the slow worlds the old ceiling excluded
V2_PLATDRAG = _v2 or bool(int(os.environ.get("CENTURY_V2_PLATDRAG", "0")))     # a stalled paradigm slows growth instead of only capping it
V2_CAPASSIST = _v2 or bool(int(os.environ.get("CENTURY_V2_CAPASSIST", "0")))   # deployed capability accelerates capability research, not only safety research
AUDIT = bool(int(os.environ.get("CENTURY_AUDIT", "0")))                         # emit HAZMASK + saturation diagnostic counters
CRN = bool(int(os.environ.get("CENTURY_CRN", "0")))                             # common random numbers: pre-draw the stochastic stream (for sobol_century.py)

# Phase 7 calibration: CENTURY_WEIGHTS points at a per-world importance-weight file
# written by calibrate_century.py. When set, the report adds anchor-weighted outcome
# tables alongside the unweighted ones. The weights are only valid for the exact
# configuration that produced them — seed, N and every ensemble-shaping switch — so
# calibrate_century.py embeds WEIGHTS_FPR (below) in the .npz and the loader refuses
# a mismatch instead of silently reweighting worlds from a different ensemble.
# Loading draws no RNG, so the simulation is identical to the unweighted run — only
# the reported aggregation differs.
WEIGHTS_FPR = json.dumps({
    "seed": SEED,
    "baseline": BASELINE,
    "rec": [REC_DIVIDEND, REC_WINDOW, REC_REACT],
    "v2": [V2_HAZMASK, V2_NUKE_R, V2_NATPAND, V2_GAPNORM, V2_SUBSTEP, V2_SOFT, V2_STRUCT,
           V2_CORR, V2_DEMO, V2_CLIMATE, V2_POLICY, V2_XHAZ, V2_REBUILD, V2_BIOUP, V2_ERODE,
           V2_ALPHASUB, V2_PLATDRAG, V2_CAPASSIST],
    "alpha_max": os.environ.get("CENTURY_ALPHA_MAX", "2.40"),
    "plateau_exp": os.environ.get("CENTURY_PLATEAU_EXP", "2.0"),
    "plateau_coef": os.environ.get("CENTURY_PLATEAU_COEF", "0.90"),
    "capassist_max": os.environ.get("CENTURY_CAPASSIST_MAX", "0.65"),
    "policy_scale": POLICY_SCALE,
    "crn": CRN,
    "struct_p_flat": os.environ.get("CENTURY_STRUCT_P_FLAT", "0.5"),
    "erode_max": os.environ.get("CENTURY_ERODE_MAX", "0.30"),
    "erode_damp": os.environ.get("CENTURY_ERODE_DAMP", "0.60"),
    "shot_ref": os.environ.get("CENTURY_SHOT_REF", "1.0"),
    "overrides": os.environ.get("CENTURY_OVERRIDES", ""),
    "corr_json": os.environ.get("CENTURY_CORR_JSON", ""),
    "param_npz": bool(os.environ.get("CENTURY_PARAM_NPZ", "")),
}, sort_keys=True)
def _load_weights(envname):
    """Load and fingerprint-check a per-world weights file named by an env var.
    Returns None when the variable is unset. Draws no RNG."""
    _wpath = os.environ.get(envname, "")
    if not _wpath:
        return None
    if not _wpath.endswith(".npz"):
        raise ValueError("%s=%s: bare .npy weights carry no configuration "
                         "fingerprint and are no longer accepted; regenerate with "
                         "calibrate_century.py (writes a fingerprinted .npz)" % (envname, _wpath))
    _wz = np.load(_wpath, allow_pickle=False)
    _w = _wz["w"].astype(float)
    _wfpr = str(_wz["meta"])
    if _wfpr != WEIGHTS_FPR:
        raise ValueError("%s fingerprint mismatch: weights were calibrated "
                         "under a different configuration.\n  weights: %s\n  run:     %s\n"
                         "Regenerate with calibrate_century.py under this configuration."
                         % (envname, _wfpr, WEIGHTS_FPR))
    if _w.shape[0] != N:
        raise ValueError("%s length %d != N %d; regenerate weights for this N"
                         % (envname, _w.shape[0], N))
    return _w

WEIGHTS = _load_weights("CENTURY_WEIGHTS")
# Third view ("the realistic bet"): lever-feasibility weights from
# calibrate_century.py --levers, reweighting the ensemble toward judgement-based
# probabilities that each social/political choice actually happens
# (lever-anchors.json). Reported alongside the unweighted tables (the headline:
# flat lever priors) and the CENTURY_WEIGHTS tables (the outside view).
LEVER_WEIGHTS = _load_weights("CENTURY_LEVER_WEIGHTS")

# v2 sampled structure (Phase 5): promote the three binary REC_* structure switches
# to per-world sampled quantities, so "which structural prior you hold" becomes an
# axis of one ensemble rather than two rival documents. Drawn only when V2_STRUCT is
# on (baseline draws nothing, so the seed-431 stream is unchanged) and before the
# override loop so a run can pin any of these to a baseline corner (e.g. struct_flat=1
# reproduces persistent risk). Priors are judgement calls, documented here inline,
# each a single constant to adjust.
STRUCT_P_FLAT = float(os.environ.get("CENTURY_STRUCT_P_FLAT", "0.5"))
                       # prior mass on "no deadline" (flat takeover window). The single biggest
                       # swing in the model and no survey resolves it. DEFENCE of the 0.5 default
                       # (plan-27 FU-009): it is the maximum-entropy prior between two rival
                       # positions the evidence does not settle — "a misaligned superintelligence
                       # has a deadline" vs "it does not". The sweep (check_century.py
                       # --struct-pflat-sweep) confirms the outside-view anchors do not
                       # discriminate: the anchor-calibration ESS is flat (~74-76%) across
                       # STRUCT_P_FLAT in 0.3-0.7, so no value is favoured on reconciliation
                       # grounds and 50/50 is honest ignorance. Overridable via CENTURY_STRUCT_P_FLAT.
GAPNORM_REF = 0.80     # reference AGI threshold for V2_GAPNORM: the gap is scaled by
                       # GAPNORM_REF / threshold, so a world at the mean threshold
                       # (U(0.68,0.92) mean = 0.80) is left unchanged vs the un-normalised
                       # gap. This makes the normalisation change only the *relative* treatment
                       # of high/low-threshold worlds, not the absolute hazard level (FU-007).
if V2_STRUCT:
    P["struct_flat"]  = (rng.random(N) < STRUCT_P_FLAT).astype(float)   # 1 = flat window (no deadline)
    P["tau_window"]   = rng.lognormal(np.log(10.0), 0.5, N)             # takeover-window timescale, yr (baseline corner = 10)
    P["lethal_share"] = rng.beta(3.0, 7.0, N)                           # takeover lethal fraction, mean 0.30 (baseline constant)
    P["dividend_mag"] = rng.uniform(0.0, 0.012, N)                      # readiness dividend coeff (baseline off=0, on=0.012)
    P["react_scale"]  = rng.uniform(0.0, 1.0, N)                        # reactive-governance magnitude (baseline off=0, on=1)

# v2 climate recalibration (Phase 9): per-world climate-sensitivity multiplier on the
# warming increment, plus an optional sampled tipping feedback above a sampled threshold,
# widening the 2126 warming spread toward the published ~1.8-4 degC envelope. Sampled only
# when V2_CLIMATE is on (baseline draws nothing); abatement coupling is retained below.
if V2_CLIMATE:
    P["clim_sens"]     = rng.lognormal(0.0, 0.30, N)     # equilibrium-sensitivity multiplier, median 1.0 (~+/-35%)
    P["tip_threshold"] = rng.uniform(2.0, 3.5, N)        # warming (degC) above which a tipping feedback engages
    P["tip_rate"]      = rng.uniform(0.0, 0.020, N)      # extra warming/yr past the threshold (0 for worlds with no tipping)

# v2 demographic recalibration (Phase 9): per-world fertility trajectory that turns
# structurally negative after a sampled peak year, so population can decline (not only
# rise), spanning the UN low-high envelope at 2126. Automation-longevity and climate-drag
# terms are retained in the update below. Sampled only when V2_DEMO is on.
if V2_DEMO:
    P["pop_peak_year"] = rng.uniform(2076.0, 2094.0, N)  # year population peaks, then declines
    P["fert_scale"]    = rng.uniform(0.0145, 0.0175, N)  # fertility-slope scale (peak height / decline depth)

# v2 hazard completeness (Phase 11). Unknown-unknowns: a per-world absorbing hazard rate
# for risks outside the model's named channels — the documents' own "a 1926 observer could
# not have named the 2020s hazards" argument. Two calibration notes (plan-25 review F-1):
#   * MAGNITUDE. An annual rate compounds hard over a century: the original U(0, 0.3%)/yr
#     prior absorbed ~10% of ALL worlds — second only to disempowerment, larger than
#     extinction, and ~a fifth of the whole irreversible_bad aggregate — while the comment
#     called it "small". The range is now U(0, 0.07%)/yr, whose century-cumulative mean
#     E[1 - exp(-100r)] ~ 3.3% pre-competition (realised share lower, since other channels
#     absorb first), anchored to Ord (The Precipice, 2020): ~1-in-30/century for
#     "unforeseen anthropogenic risks".
#   * ASYMMETRY. The channel is deliberately bad-only: unknown windfalls exist too, but a
#     windfall is not absorbing (it leaves the world in play, where the named dynamics
#     already reward it), whereas an unmodelled catastrophe removes the world — so only the
#     bad tail needs its own channel. The rate above is therefore a NET-BAD residual, and
#     that is a further reason it must stay small.
# Collapse recovery: a collapsed world rebuilds over a sampled period and re-enters with
# degraded institutions. Sampled only when the switch is on (baseline draws nothing).
if V2_XHAZ:
    P["xhaz_rate"] = rng.uniform(0.0, 0.0007, N)         # unknown-unknowns absorbing hazard, /yr (net-bad residual)
if V2_REBUILD:
    P["rebuild_period"] = rng.uniform(5.0, 20.0, N)      # years a collapsed world takes to re-enter

# v2 readiness erosion (plan-28). Before this correction the readiness update was a sum of
# non-negative terms, so R rose monotonically in every world for a century and capability
# growth fed it only positively (via ai_assist). The one thing that could reduce R anywhere
# in the model was a nuclear exchange (V2_NUKE_R). That asymmetry says containment and
# evaluation capacity never expire, which is indefensible: an evaluation harness built for
# one capability level is invalidated by a system that exceeds it, and a sandbox is only as
# isolated as its weakest dependency. This is a DYNAMICS correction, not a new hazard
# channel — agentic AI risk stays in the takeover hazard, which the C-R gap already drives.
# Three calibration notes:
#   * MAGNITUDE. The competing term is assist * (1 - 0.45*race) * 0.6 * max(dC, 0), where
#     assist is Beta(1.6, 2.4) * 0.65 (mean ~0.26), so its coefficient on capability growth
#     has mean ~0.156 before the race discount. A U(0, 0.30) prior has mean 0.15, putting
#     the median world close to readiness-neutral on capability growth and letting the sign
#     be decided by race and respond rather than assumed. The lower bound of zero reproduces
#     the pre-correction model, so the old assumption stays inside the ensemble instead of
#     being replaced by its opposite. Same maximum-entropy stance as STRUCT_P_FLAT above.
#   * GATING. Damping is gated on accumulated warning-shot memory, so institutions
#     re-validate their evaluations only after an incident. Nothing else in this model
#     improves readiness in the absence of a warning shot (respond is defined as
#     "institutional responsiveness to warning shots" and the reactive-governance block
#     fires only on a shot); unconditional damping would have been the first such mechanism
#     and the most optimistic assumption in the file. Erosion is therefore UNDAMPED before
#     a world's first incident, which front-loads severity into fast-takeoff worlds that
#     cross the threshold before accumulating warnings. That is intended.
#   * SHOT_REF. shot_hist decays at POLICY_SHOT_DECAY (0.92)/yr and gains 1.0 per shot, so a
#     sustained rate of lambda/yr settles at lambda/0.08 = 12.5*lambda. The shot rate is
#     clip(0.02 + 0.10*(C - 0.5), 0, 0.15), so late-century high-capability worlds settle
#     near 1.9 and mid-capability worlds near 0.6. SHOT_REF = 1.0 puts saturation at a
#     sustained 0.08/yr: worlds with repeated near-misses get there, worlds with one or two
#     never do. Driving SHOT_REF toward 0 recovers the rejected unconditional variant.
# Sampled only when the switch is on (baseline draws nothing), and before the override loop so
# a run can pin erode_mag to any corner (0 = the pre-correction dynamics).
# All three are env-overridable (and fingerprinted in WEIGHTS_FPR) so plan-28 Phase D can
# sweep them without editing the source, matching how STRUCT_P_FLAT and POLICY_SCALE work.
ERODE_MAX  = float(os.environ.get("CENTURY_ERODE_MAX", "0.30"))    # ceiling of the per-world containment-decay coefficient
ERODE_DAMP = float(os.environ.get("CENTURY_ERODE_DAMP", "0.60"))   # share of erosion a saturated, maximally responsive
                       # world removes. Bounded below 1: no institution re-validates against
                       # capability that has not appeared yet.
SHOT_REF   = float(os.environ.get("CENTURY_SHOT_REF", "1.0"))      # warning-shot memory at which institutional learning saturates
if V2_ERODE:
    P["erode_mag"] = rng.uniform(0.0, ERODE_MAX, N)      # containment-decay coeff on capability growth

# ---- V2_ALPHASUB: let capability growth grind ------------------------------------------
# Capability runs from 0.35 to a threshold of 0.68-0.92, so the operative regime is entirely
# below C = 1. In that regime the curvature exponent runs backwards from the intuition its
# name suggests: because C < 1, a LARGER exponent shrinks C**alpha and therefore SLOWS
# growth. At C = 0.35 the yearly increment is 0.48k at alpha = 0.7 and 0.14k at alpha = 1.9.
# So the sampled range U(1.0, 1.9) is not "linear to superexponential" as its comment reads;
# in the pre-threshold regime it is "fast to slow", and 1.9 is the slowest world the ensemble
# can build. That ceiling is what truncates the arrival distribution: 8.4% of worlds cross
# after 2050 and 2.8% after 2060, so slow worlds fail to arrive at all instead of arriving
# late, which is why an economic-replacement arrival band is infeasible for this ensemble
# (future.md section 6.3). Pinning the prior to its slow end alone (alpha in [1.85, 1.9])
# moves the median crossing from 2036 to 2040 and the post-2050 mass from 8.4% to 18.7%,
# which identifies the ceiling rather than the floor as the binding constraint.
#
# The correction raises that ceiling: it rescales the existing draw onto [1.0, ALPHA_MAX]
# instead of drawing again, so the RNG stream is bit-identical with the switch on or off —
# the same technique the pre-drawn ceiling variants use above. The map is linear and
# monotone, so V2_CORR's rank reordering sees the same ranks and the copula is unaffected.
# Applied before the override loop, so an explicit CENTURY_OVERRIDES alpha still wins.
#
# This widens the arrival distribution; it does not by itself move the share of worlds that
# never reach AGI, which is set by the plateau ceiling rather than by curvature. The
# ensemble's own design target at the top of this file (10-15% without AGI by 2126, against
# an actual 5.9%) is therefore a separate correction.
#
# ALPHA_MAX is env-tunable and fingerprinted, matching ERODE_MAX and STRUCT_P_FLAT. Setting
# it to 1.9 reproduces the uncorrected prior exactly. Measured at N=200,000, seed 431:
#
#   ALPHA_MAX   median   P(by 2035)   P(by 2050)   never    P(good)   P(bad)
#   1.90 (off)   2036       42.3%        85.7%      5.9%     38.8%    49.0%
#   2.40         2038       31.7%        80.1%      6.0%     40.4%    46.4%
#   2.80         2040       24.6%        73.9%      6.2%     41.6%    44.1%
#   3.20         2042       19.2%        66.1%      6.6%     42.3%    41.7%
#   4.00         2047       12.6%        49.9%      9.1%     42.4%    36.1%
#   5.00         2053        8.6%        35.5%     17.8%     38.6%    29.3%
#
# The default is set by this file's own design target at the top ("median in the late
# 2030s"), which 2.40 meets and 2.80 already overshoots. Every value from 2.40 to 4.00 puts
# P(AGI by 2050) inside the two-family anchor band of [0.40, 0.85], so the published
# forecasts do not discriminate between them; the design target does. Reaching the
# economic-replacement view on its own terms (P(by 2050) near 0.50) needs about 4.00, which
# would move the median crossing by eleven years and is a modelling decision rather than a
# correction — it is deliberately not the default.
ALPHA_MAX = float(os.environ.get("CENTURY_ALPHA_MAX", "2.40"))   # ceiling of the curvature prior under V2_ALPHASUB

# ---- V2_CAPASSIST: let AI accelerate capability research, not only safety research -----
# The readiness step gives deployed capability two routes into safety: a share of this
# year's capability growth and an ongoing dividend from already-deployed capability
# ("aligned-ish systems doing safety research"). The capability step has no counterpart.
# Capability feeds readiness in two directions and feeds itself in none, beyond the fixed
# curvature, so the model contains AI that helps align its successors and never AI that
# helps build them. That asymmetry runs one way: it flatters every outcome that depends on
# readiness keeping pace, which is most of them.
#
# The correction mirrors the readiness dividend on the capability side: growth is multiplied
# by (1 + cap_assist * C), so more deployed capability means faster capability growth. It is
# NOT degraded by racing the way ai_assist is: a racing world cuts corners on safety work and
# hoards results, but racing is exactly when capability research gets the most compute, and
# k_eff already carries a (1 + 0.25 * race) term that would double-count it.
#
# The magnitude is drawn from a SIDE stream rather than the main generator, so the main RNG
# sequence is bit-identical whether the switch is on or off and the correction is exactly
# attributable. (V2_ERODE draws its coefficient from the main stream and therefore shifts
# every later draw, which is why --erosion-audit has to compare against a Monte Carlo bar
# instead of asserting equality.) Set before the override loop, so a run can pin it.
# The ceiling is 0.65, the same ceiling `assist` uses for the readiness side above. That is
# a stated assumption rather than a tuned number: whatever share of capability a world can
# turn to safety research, it can also turn to capability research. Nothing anchors it, so it
# joins erode_mag as an input with no published source behind it (section 8). Measured at
# N=200,000, seed 431:
#
#   CAPASSIST_MAX   median   P(by 2035)   uncontrolled at crossing   P(good)   P(bad)
#   0.00 (off)       2039       32.7%              61.9%              39.2%    44.6%
#   0.20             2038       34.9%              64.0%              38.6%    45.5%
#   0.40             2037       37.0%              66.0%              38.0%    46.3%
#   0.65 (default)   2037       39.5%              68.0%              37.5%    47.3%
#   0.80             2036       40.9%              69.3%              37.0%    47.7%
#
# P(good) is close to linear across the range and spans about 2 points end to end, against
# about 4.6 points for erode_mag, so the headline is not reported as a second pair; the sweep
# is recorded in section 6.9 instead.
CAPASSIST_MAX = float(os.environ.get("CENTURY_CAPASSIST_MAX", "0.65"))   # ceiling of the per-world capability-assist coefficient
P["cap_assist"] = (np.random.default_rng(SEED + 977).uniform(0.0, CAPASSIST_MAX, N)
                   if V2_CAPASSIST else np.zeros(N))
if V2_ALPHASUB:
    P["alpha"] = 1.0 + (P["alpha"] - 1.0) * (ALPHA_MAX - 1.0) / 0.9

# optional fixed overrides for named-scenario runs: CENTURY_OVERRIDES='{"race":0.9,...}'
_ov = json.loads(os.environ.get("CENTURY_OVERRIDES", "{}"))
for _k, _v in _ov.items():
    if _k == "plateau":
        P["plateau"][:] = bool(_v)
        # reselect between the pre-drawn ceiling variants — no fresh RNG, so the draws
        # after this point are identical to the unoverridden run (CRN-comparable)
        P["ceiling"] = np.where(P["plateau"], _ceil_stall, _ceil_nostall)
    else:
        P[_k][:] = float(_v)

# ---- V2_PLATDRAG: make a stalled paradigm slow down instead of only gating -------------
# Growth is throttled by (C/ceiling)**6 * 0.30, and the plateau regime works by lowering
# `ceiling` alone. Both halves of that misfire.
#
# The sixth power does almost nothing until capability is nearly at the ceiling: it removes
# 0.5% of a year's growth at C/ceiling = 0.5, 3.5% at 0.7, and 11.3% at 0.85. A plateau
# world therefore grows at very close to full speed right up to its wall, so the regime
# delays the median crossing by one year (2037 against 2036) in the worlds that still cross.
# A stalled paradigm that costs twelve months is not a stall.
#
# And the wall is not a wall. dC only turns negative once (C/ceiling)**6 * 0.30 exceeds 1,
# i.e. at C = 1.22 * ceiling, so a plateau world overshoots its own ceiling by a fifth. That
# is why 53% of plateau worlds whose ceiling sits BELOW the AGI threshold cross it anyway.
#
# So the regime blocks worlds whose threshold is far above their ceiling and waves the rest
# through on schedule, with nothing in between. The correction gives plateau worlds their own
# throttle shape: a lower exponent, so the brake comes on gradually from further out, and a
# higher coefficient, so the ceiling is approached asymptotically rather than overshot. Both
# are per-world arrays so the sub-annual integration path uses the same values, and both are
# deterministic functions of draws already made, so the RNG stream is untouched.
#
# Computed after the override loop because CENTURY_OVERRIDES='{"plateau":true}' reselects the
# regime for every world (the named plateau scenario in README.md), and the throttle has to
# follow that reselection rather than the original draw.
# The two knobs have to move together. Lowering the exponent alone makes the brake gradual
# but also raises the point where growth stops, (1/coef)**(1/exp) times the ceiling, so worlds
# that used to stall now grind past their wall instead: at (2.0, 0.30) fully 99.1% of plateau
# worlds reach AGI and the no-AGI share collapses to 0.6%. Raising the coefficient alongside
# brings the stopping point back down. Measured at N=200,000, seed 431:
#
#   exp  coef   no AGI by 2126   median crossing, plateau worlds that cross   share crossing
#   6.0  0.30 (off)      6.0%                    2040                             60.6%
#   3.0  0.30            1.9%                    2041                             90.3%
#   2.0  0.30            0.6%                    2041                             99.1%
#   2.0  0.60            4.7%                    2046                             70.2%
#   2.0  0.90 (default) 10.0%                    2051                             32.3%
#   1.5  0.90            9.6%                    2056                             35.1%
#   2.0  1.20           13.2%                    2058                              9.6%
#
# (2.0, 0.90) is chosen on three criteria that do not depend on taste. It puts the no-AGI
# share at 10.0%, the lower bound of this file's own design target at the top (10-15%), which
# the uncorrected model missed at 5.9%. It cuts the ceiling overshoot from 1.22x to 1.05x, so
# the ceiling means what its name says. And it moves the median crossing of a stalled world
# that still crosses from 2040 to 2051, thirteen years behind the ensemble median rather than
# two, which is what distinguishes a stalled paradigm from a mild delay.
PLATEAU_EXP  = float(os.environ.get("CENTURY_PLATEAU_EXP", "2.0"))    # throttle exponent for stalled worlds (6.0 elsewhere)
PLATEAU_COEF = float(os.environ.get("CENTURY_PLATEAU_COEF", "0.90"))  # throttle coefficient for stalled worlds (0.30 elsewhere)
_stalled = P["plateau"] if V2_PLATDRAG else np.zeros(N, dtype=bool)
P["bneck_exp"]  = np.where(_stalled, PLATEAU_EXP, 6.0)
P["bneck_coef"] = np.where(_stalled, PLATEAU_COEF, 0.30)

dec_rows = []

# v2 correlated priors (Phase 6): couple the continuous marginals through a Gaussian
# copula, preserving every marginal exactly via Iman-Conover rank reordering (NumPy
# only, no SciPy). Independent sampling overweights incoherent worlds and distorts
# the tails and the lever ranking strategy.md is built on. Drawn only when V2_CORR is
# on (baseline draws nothing, so the seed-431 stream is unchanged) and after overrides
# so a pinned parameter stays constant. Default correlation signs are fixed by the
# plan; magnitudes were signed off on 2026-07-06. CENTURY_CORR_JSON overrides the
# pairs for experiments ('identity' or 'off' forces independence with an equal draw).
CORR_VARS = ["alpha", "k", "threshold", "R0", "safety_eff", "assist", "race", "respond",
             "concentration0", "redist_will", "bio_defense", "climate_eff", "fragility"]
CORR_DEFAULT = {
    "race,respond": -0.4,        # a world racing hard cuts institutional corners -> less responsive
    "redist_will,respond": 0.3,  # functional institutions both redistribute and heed warning shots
    # Aggressive scaling: a world whose base growth rate is high should also have the
    # curvature that makes progress fast, and in this model's operative range that is a LOW
    # exponent, so the coupling is negative. It was +0.3 until 2026-07-30 on the reading that
    # a higher exponent means faster growth. That is true asymptotically (dC/dt = k*C**alpha
    # with alpha > 1 has a finite-time singularity) and false everywhere this model runs: the
    # crossover is at exactly C = 1, capability starts at 0.35 and the threshold is 0.68-0.92,
    # so the whole run-up sits below it, and the ceiling then caps capability at about 1.05x
    # its own value so the accelerating regime is never reached either. Measured with the
    # coupling switched off, Spearman(alpha, crossing year) is +0.396 (later) against
    # Spearman(k, crossing year) of -0.843 (sooner), and Spearman(alpha, final capability) is
    # +0.038, i.e. nothing. Pairing them positively therefore cancelled the two effects and
    # gave the NARROWEST arrival distribution of the three signs: 22 years between the 10th
    # and 90th percentile at +0.3, 26 at 0, 30 at -0.3. Restore the old value with
    # CENTURY_CORR_JSON=\'{"k,alpha": 0.3}\'.
    "k,alpha": -0.3,
}
corr_pairs = {}
if V2_CORR:
    _cj = os.environ.get("CENTURY_CORR_JSON", "").strip()
    if _cj.lower() in ("identity", "off"):
        corr_pairs = {}
    elif _cj:
        corr_pairs = {**CORR_DEFAULT, **json.loads(_cj)}
    else:
        corr_pairs = dict(CORR_DEFAULT)
    _cidx = {nm: i for i, nm in enumerate(CORR_VARS)}
    corr_mat = np.eye(len(CORR_VARS))
    for _pair, _rho in corr_pairs.items():
        _a, _b = [s.strip() for s in _pair.split(",")]
        corr_mat[_cidx[_a], _cidx[_b]] = corr_mat[_cidx[_b], _cidx[_a]] = float(_rho)
    _L = np.linalg.cholesky(corr_mat)                        # raises LinAlgError if not positive definite
    _Zc = _L @ rng.standard_normal((len(CORR_VARS), N))      # correlated latent scores (always drawn under V2_CORR)
    for _i, _nm in enumerate(CORR_VARS):
        _rank = np.argsort(np.argsort(_Zc[_i]))              # 0..N-1 rank of each world in the latent score
        P[_nm] = np.sort(P[_nm])[_rank]                      # reorder marginal to that rank; the marginal set is unchanged

# Phase 8 Sobol driver hook: CENTURY_PARAM_NPZ points at a matrix of the continuous
# parameters (CORR_VARS order) that sobol_century.py injects to drive the world-step as a
# function of a Saltelli sample. It overrides the internally-sampled (and copula-reordered)
# continuous priors while leaving plateau, the sampled structure and the yearly shocks
# internally drawn — so at fixed seed/N those nuisance draws are common across the Saltelli
# evaluations (partial common-random-numbers). Loading draws no RNG; the hook is a no-op
# when the env var is unset, so baseline runs are untouched.
#
# Two widths are accepted. (N, 13) is the original form and leaves erode_mag at its
# internally-sampled value. Under V2_ERODE the matrix may instead carry a 14th column,
# erode_mag, so the containment-decay coefficient varies BETWEEN the Saltelli evaluations
# rather than only within them; in the narrow form it is drawn once per world at seed 431
# and is therefore identical across A, B and every AB_i, which puts its contribution in the
# variance denominator and in none of the numerators (plan-28 Phase G). The narrow form is
# still accepted so a caller predating the correction keeps working unchanged.
_pnpz = os.environ.get("CENTURY_PARAM_NPZ", "")
if _pnpz:
    _pm = np.load(_pnpz).astype(float)
    _inject = list(CORR_VARS) + (["erode_mag"] if V2_ERODE else [])
    _widths = {len(CORR_VARS), len(_inject)}
    if _pm.ndim != 2 or _pm.shape[0] != N or _pm.shape[1] not in _widths:
        raise ValueError("CENTURY_PARAM_NPZ shape %s != (%d, %s)"
                         % (_pm.shape, N, " or ".join(str(w) for w in sorted(_widths))))
    for _i, _nm in enumerate(_inject[:_pm.shape[1]]):
        P[_nm] = _pm[:, _i].copy()

# ----------------------------------------------------------------------------
# 2. STATE ARRAYS (one value per world, stepped through time)
# ----------------------------------------------------------------------------
C   = np.full(N, 0.35)                  # AI capability (0-1+; threshold ~0.68-0.92)
R   = P["R0"].copy()                    # readiness/alignment-control capacity (0-1)
W   = P["concentration0"].copy()        # wealth/power concentration (0-1)
Rd  = np.full(N, 0.35)                  # redistribution strength (0-1)
G   = np.full(N, 0.45)                  # governance quality (0-1)
Tr  = np.full(N, 0.45)                  # social trust (0-1)
H   = np.full(N, 0.55)                  # wellbeing (0-1)
POP = np.full(N, 8.2)                   # population, billions
TEMP= np.full(N, 1.3)                   # warming above pre-industrial, °C
GDPg= np.full(N, 0.03)                  # trailing growth rate (diagnostic)

agi_year   = np.full(N, -1, dtype=int)  # year AGI threshold crossed (-1 = never)
gap_at_agi = np.full(N, np.nan)         # capability - readiness at crossing
fate       = np.zeros(N, dtype=int)     # 0 ongoing; see FATES
fate_year  = np.full(N, -1, dtype=int)
fate_channel = np.full(N, "", dtype=object)     # takeover | drift | lockin | nuclear | pandemic
snap = {k: np.full(N, np.nan) for k in ["W", "Rd", "H", "G", "C", "R", "POP"]}

def snapshot(idx, channel):
    if len(idx) == 0:
        return
    fate_channel[idx] = channel
    for _n, _arr in (("W", W), ("Rd", Rd), ("H", H), ("G", G), ("C", C), ("R", R), ("POP", POP)):
        snap[_n][idx] = _arr[idx]

FATES = {
    0: "ongoing",
    1: "extinction",              # human extinction / unrecoverable end
    2: "collapse",                # civilisational collapse, survivors, tech regression
    3: "lockin",                  # stable totalitarian lock-in (AI-enforced)
    4: "disempowerment",          # humans alive, comfortable or not, but no meaningful control
    5: "unknown_catastrophe",     # v2 XHAZ: unknown-unknowns absorbing hazard
}

# event counters (diagnostics)
ev = {k: np.zeros(N, dtype=int) for k in
      ["nuclear_war", "eng_pandemic", "nat_pandemic", "warning_shot", "regional_war"]}

alive = np.ones(N, dtype=bool)          # world still "ongoing"

# ----------------------------------------------------------------------------
# 3. YEARLY STEP
# ----------------------------------------------------------------------------
clip = lambda x, lo=0.0, hi=1.0: np.clip(x, lo, hi)


def soft(x, dx):
    # v2 soft-saturating (logistic-style) bounded update: a positive increment fades
    # as x -> 1 and a negative increment fades as x -> 0, so the variable asymptotes
    # toward the [0, 1] bounds instead of railing against a hard clip and sitting
    # pinned at a bound for decades. dx keeps its mid-range magnitude; only motion
    # *into* the near bound is damped by the (1 - x) / x logistic factors.
    pos = np.maximum(dx, 0.0)
    neg = np.maximum(-dx, 0.0)
    return clip(x + pos * (1.0 - x) - neg * x)


def hazard_mask(u, row, p, live_idx, alive_now, hazmask):
    # Which loop-start-live worlds (positions aligned to live_idx) fire this hazard.
    # Baseline: positional uniform vs probability, drawn at (6, n_live). v2 HAZMASK:
    # the fixed-shape (6, N) uniform is sliced to live_idx and gated by *current*
    # alive, so a world absorbed by an earlier same-year hazard neither rolls for
    # nor is counted by any later hazard this year. Both branches return a mask of
    # length n_live aligned to live_idx.
    if hazmask:
        return (u[row, live_idx] < p) & alive_now[live_idx]
    return u[row] < p


post_agi_years = np.zeros(N, dtype=int)
DEC_YEARS = set(range(2030, 2121, 10))
dec_snap = {}                           # year -> {var: float32 array}, state frozen at absorption for dead worlds
reg_drag = np.zeros(N)                  # accumulated regulation drag on k
safety_bonus = np.zeros(N)              # accumulated post-warning-shot safety effort
shot_hist = np.zeros(N)                 # decayed warning-shot memory per world (plan-28: hoisted out
                                        # of the V2_POLICY block, which used to own it, because V2_ERODE
                                        # also reads it; maintained unconditionally, consumed only by
                                        # whichever of the two switches is on)
audit_pandemic_post_absorption = 0      # HAZMASK diagnostic: pandemic events on worlds absorbed earlier the same year
audit_pinned = {nm: 0 for nm in ["W", "Rd", "G", "Tr", "H"]}  # saturation diagnostic: survivor-years within 0.01 of a bound
audit_alive_years = 0                   # denominator for audit_pinned (total survivor-years)
# v2 ERODE audit accumulators (plan-28 Phase B, consumed by check_century.py --erosion-audit).
# These are taken at the readiness update, so the denominator is the set of worlds the erode
# term was applied to. audit_alive_years above is counted later in the year, after the hazards
# have absorbed some of those worlds, so the two denominators are close but not the same and
# should not be substituted for one another.
ero_years = ero_pre_years = 0           # survivor-years at the readiness update; pre-crossing subset
ero_erode_sum = ero_assist_sum = 0.0    # summed erode and ai_assist over ero_years
ero_learn_sum = ero_pre_learn_sum = 0.0 # summed realised damping factor, all years and pre-crossing
ero_learn_zero = ero_pre_learn_zero = 0 # survivor-years with no warning shot yet on record
ero_net_losing = 0                      # survivor-years where erode exceeded ai_assist
ero_dR_neg = 0                          # survivor-years where readiness fell outright
ero_R_min = float("inf")                # lowest realised R across survivor-years
ero_R_floor = 0                         # survivor-years with R within 0.01 of the clip floor. R could
                                        # only rise from AI-side causes before this correction, so the
                                        # existing audit_pinned set never watched it at the bottom.
rebuild_timer = np.zeros(N)             # v2 REBUILD: years left before a collapsed world re-enters (0 = none)
ever_collapsed = np.zeros(N, dtype=bool)  # v2 REBUILD: world has collapsed at least once
recovered = np.zeros(N, dtype=bool)     # v2 REBUILD: world collapsed and re-entered
reb_preG = reb_postG = reb_preC = reb_postC = 0.0   # re-entry penalty audit (pre/post G and C)

# Phase 10 endogenous policy: safety_eff, race and respond become state-responsive rather
# than fixed per-world constants. Each is recomputed every year from the sampled base plus
# a bounded, damped feedback (scaled by POLICY_SCALE, which is 0 to reproduce the non-policy
# ensemble). Feedbacks are LEVEL functions of current state (not accumulating differentials),
# so they cannot oscillate. Constants documented here; bounds enforced by clip.
POLICY_SE_GAP = 0.010     # safety-effort gain per unit visible capability-readiness gap (C-R-0.15)/yr
POLICY_SE_SHOT = 0.003    # safety-effort gain per unit decayed warning-shot memory
POLICY_SE_MAX = 0.05      # cap on realised safety effort
POLICY_RACE_UP = 0.15     # race intensification at full capability proximity to threshold
POLICY_RACE_DROP = 0.20   # race de-escalation once AGI is crossed
POLICY_RESP_LEARN = 0.05  # responsiveness gain per unit warning-shot memory (institutions learn)
POLICY_SHOT_DECAY = 0.92  # yearly decay of warning-shot memory
if V2_POLICY:
    se_t = P["safety_eff"].copy()       # time-varying safety effort
    race_t = P["race"].copy()           # time-varying race intensity
    resp_t = P["respond"].copy()        # time-varying responsiveness
    pol_se_sum = np.zeros(N)            # accumulators for the realised-safety-effort audit
    pol_se_cnt = np.zeros(N)
    pol_bounds = {"se_t": [np.inf, -np.inf], "race_t": [np.inf, -np.inf], "resp_t": [np.inf, -np.inf]}

# Phase 8 common-random-numbers: when CENTURY_CRN is set (sobol_century.py only), every
# stochastic term that reaches the outcome classification is pre-drawn as a fixed (T, N)
# tensor and indexed in the loop, so the shock realisation for each world position is
# identical across evaluations that differ only in the injected parameters. This makes
# P(good)/P(disempowerment) a deterministic function of the parameters — the condition
# the Saltelli/Sobol total-order estimator needs. POP-only draws (which do not enter the
# classification) stay in-loop. CRN changes the v2 stream; baseline (CRN off) is untouched.
if CRN:
    _crnC = rng.normal(0, 0.008, (T, N))       # 3.1 capability noise
    _crnR = rng.normal(0, 0.004, (T, N))        # 3.2 readiness noise
    _crnG = rng.normal(0, 0.01, (T, N))         # 3.4 governance noise
    _crnShot = rng.random((T, N))               # 3.7 warning-shot rolls
    _crnU = rng.random((T, 6, N))               # 3.8 hazard uniforms
    _crnNukeSev = rng.random((T, N))            # nuclear severity split
    _crnBioSev = rng.random((T, N))             # engineered-pandemic severity split
    _crnBioSev2 = rng.random((T, N))            # extreme-pandemic extinction-vs-collapse split
    _crnTakeSev = rng.random((T, N))            # takeover extinction-vs-disempowerment split
    _crnDrift = rng.random((T, N))              # gradual-disempowerment roll
    _crnXhaz = rng.random((T, N))               # unknown-unknowns roll

for ti, year in enumerate(YEARS):
    if V2_REBUILD:
        # v2 REBUILD: collapsed worlds count down and re-enter with degraded institutions,
        # then resume stepping this year. Extinction stays absorbing (fate 1 is untouched).
        _reb = rebuild_timer > 0
        rebuild_timer[_reb] -= 1.0
        _done = _reb & (rebuild_timer <= 0)
        if _done.any():
            if AUDIT:
                reb_preG += float(G[_done].sum()); reb_preC += float(C[_done].sum())
            G[_done] = clip(G[_done] * 0.6); Tr[_done] = clip(Tr[_done] * 0.6); C[_done] = C[_done] * 0.75
            if AUDIT:
                reb_postG += float(G[_done].sum()); reb_postC += float(C[_done].sum())
            alive[_done] = True
            recovered[_done] = True
    a = alive.copy()          # snapshot: hazard blocks below mutate `alive`
    if not a.any():
        break

    # ---------- 3.0 endogenous policy (v2): recompute the state-responsive levers -------
    if V2_POLICY:
        # race intensifies as capability nears the threshold and de-escalates after crossing;
        # safety effort rises with the visible gap and warning-shot memory; responsiveness
        # grows with warning-shot memory. All bounded; POLICY_SCALE=0 leaves them at base.
        _prox = clip((C - (P["threshold"] - 0.20)) / 0.20, 0.0, 1.0)
        race_t = clip(P["race"] + POLICY_SCALE * (POLICY_RACE_UP * _prox - POLICY_RACE_DROP * (agi_year > 0)), 0.0, 1.0)
        _gapvis = np.maximum((C - R) - 0.15, 0.0)
        se_t = clip(P["safety_eff"] + POLICY_SCALE * (POLICY_SE_GAP * _gapvis + POLICY_SE_SHOT * shot_hist),
                    P["safety_eff"], POLICY_SE_MAX)
        resp_t = clip(P["respond"] + POLICY_SCALE * POLICY_RESP_LEARN * shot_hist, P["respond"], 1.0)
        pol_se_sum[a] += se_t[a]; pol_se_cnt[a] += 1
        for _nm, _arr in (("se_t", se_t), ("race_t", race_t), ("resp_t", resp_t)):
            pol_bounds[_nm][0] = min(pol_bounds[_nm][0], float(_arr[a].min()))
            pol_bounds[_nm][1] = max(pol_bounds[_nm][1], float(_arr[a].max()))
    race_a = race_t[a] if V2_POLICY else P["race"][a]
    safety_eff_a = se_t[a] if V2_POLICY else P["safety_eff"][a]
    respond_a = resp_t[a] if V2_POLICY else P["respond"][a]

    # ---------- 3.1 capability growth (curvature law + bottleneck + drag) ----
    k_base = P["k"][a] * (1 + 0.25 * race_a) * (1 - 0.5 * reg_drag[a])
    # V2_CAPASSIST: deployed capability accelerates capability research. Zero when the
    # switch is off, so k_eff is exactly the previous expression.
    k_eff = k_base * (1 + P["cap_assist"][a] * C[a])
    growth = k_eff * np.maximum(C[a], 0.05) ** P["alpha"][a]
    bottleneck = (np.maximum(0.0, (C[a] / P["ceiling"][a])) ** P["bneck_exp"][a]) * P["bneck_coef"][a]
    dC = growth - bottleneck * growth + (_crnC[ti][a] if CRN else rng.normal(0, 0.008, a.sum()))
    dC = np.maximum(dC, -0.01)
    if V2_SUBSTEP:
        # v2: re-integrate fast-growth worlds (annual dC > 0.06) in four quarters,
        # re-evaluating curvature and bottleneck each quarter so capability tracks
        # the AGI threshold instead of leaping past it and overstating gap_at_agi.
        # The year's stochastic term is recovered arithmetically and re-applied once,
        # so this correction draws no extra RNG and does not shift the stream.
        big = dC > 0.06
        if big.any():
            Cq = C[a][big]
            kb = k_base[big]; al = P["alpha"][a][big]; ce = P["ceiling"][a][big]
            bex = P["bneck_exp"][a][big]; bco = P["bneck_coef"][a][big]
            ca = P["cap_assist"][a][big]
            noise_big = dC[big] - (growth[big] - bottleneck[big] * growth[big])
            for _q in range(4):
                gq = kb * (1 + ca * Cq) * np.maximum(Cq, 0.05) ** al
                bq = (np.maximum(0.0, (Cq / ce)) ** bex) * bco
                Cq = Cq + (gq - bq * gq) / 4.0
            dC[big] = np.maximum((Cq - C[a][big]) + noise_big, -0.01)
    C[a] = np.maximum(C[a] + dC, 0.0)

    # ---------- 3.2 readiness growth ----------------------------------------
    # human-paced effort + AI-assisted alignment. The assist term has two parts:
    # a share of this year's capability growth, plus an ongoing dividend from
    # already-deployed capability (aligned-ish systems doing safety research).
    # Race intensity degrades both (corners cut, results hoarded).
    # dividend coefficient: v2 STRUCT samples it per world; baseline is the on/off constant
    div_mag = P["dividend_mag"][a] if V2_STRUCT else (0.012 if REC_DIVIDEND else 0.0)
    ai_assist = P["assist"][a] * (1 - 0.45 * race_a) * \
                (0.6 * np.maximum(dC, 0) + div_mag * C[a] * (0.4 + 0.6 * R[a]))
    # v2 ERODE: each year's new capability invalidates part of the evaluation and containment
    # harness built for last year's, so capability growth now has a SIGNED net effect on
    # readiness instead of a guaranteed positive one. Scales with the same np.maximum(dC, 0)
    # as ai_assist, so the two offset directly, and vanishes under plateau without any
    # special-casing (a stalled paradigm leaves the harness valid). Damping is gated on
    # decayed warning-shot memory: respond_a sets how hard a world reacts, shot_hist sets how
    # much there has been to react to, so a world with no incidents on record gets no damping
    # however responsive it is on paper. No RNG is drawn, so the stream is unchanged.
    if V2_ERODE:
        learn = respond_a * np.minimum(shot_hist[a] / SHOT_REF, 1.0)
        erode = P["erode_mag"][a] * np.maximum(dC, 0) * (1.0 - ERODE_DAMP * learn)
    else:
        erode = 0.0
    dR = safety_eff_a * (0.5 + G[a]) + ai_assist + safety_bonus[a] - erode
    R[a] = clip(R[a] + dR + (_crnR[ti][a] if CRN else rng.normal(0, 0.004, a.sum())))
    if AUDIT and V2_ERODE:
        # Counted here rather than at the end of the year so the denominator is exactly the
        # set of worlds erode was applied to. `agi_year[a] < 0` still reads as pre-crossing
        # because this year's crossing is recorded in 3.3 below, not above.
        _epre = agi_year[a] < 0
        ero_years += int(a.sum()); ero_pre_years += int(_epre.sum())
        ero_erode_sum += float(erode.sum()); ero_assist_sum += float(ai_assist.sum())
        ero_learn_sum += float(learn.sum()); ero_pre_learn_sum += float(learn[_epre].sum())
        ero_learn_zero += int((learn <= 0.0).sum())
        ero_pre_learn_zero += int((learn[_epre] <= 0.0).sum())
        ero_net_losing += int((erode > ai_assist).sum())
        ero_dR_neg += int((dR < 0).sum())
        ero_R_min = min(ero_R_min, float(R[a].min()))
        ero_R_floor += int((R[a] <= 0.01).sum())

    # ---------- 3.3 AGI crossing ---------------------------------------------
    crossed = a & (agi_year < 0) & (C >= P["threshold"])
    agi_year[crossed] = year
    gap_at_agi[crossed] = C[crossed] - R[crossed]
    is_post = a & (agi_year > 0)
    post_agi_years[is_post] += 1

    # ---------- 3.4 economy, distribution, governance ------------------------
    autom = clip((C - 0.35) / 0.55)                       # automation share proxy
    boom = 0.02 + 0.10 * autom[a] * np.minimum(C[a], 1.0) # growth accelerates with capability
    GDPg[a] = boom
    shock = np.maximum(dC, 0) * autom[a]                  # automation shock (speed x depth)
    # concentration: automation concentrates by default; redistribution, governance
    # and post-scarcity politics push back towards a contested equilibrium
    dW = 0.018 * autom[a] * (1 - Rd[a]) - 0.016 * Rd[a] * P["redist_will"][a] \
         - 0.008 * G[a] * (W[a] - 0.45)
    W[a] = soft(W[a], dW) if V2_SOFT else clip(W[a] + dW)
    # redistribution: political will + trust/governance enable it; abundance funds it;
    # concentrated wealth blocks it where governance is weak (political capture)
    dRd = 0.025 * P["redist_will"][a] * (0.4 * Tr[a] + 0.6 * G[a]) \
          + 0.015 * autom[a] * P["redist_will"][a] - 0.020 * W[a] * (1 - G[a])
    Rd[a] = soft(Rd[a], dRd) if V2_SOFT else clip(Rd[a] + dRd)
    dG = 0.020 * Tr[a] - 0.015 * (W[a] - 0.5) - 0.5 * shock * (1 - Rd[a]) \
         + 0.012 * respond_a + 0.010 * (H[a] - 0.5)
    _gnoise = _crnG[ti][a] if CRN else rng.normal(0, 0.01, a.sum())
    G[a] = soft(G[a], dG + _gnoise) if V2_SOFT else clip(G[a] + dG + _gnoise)
    dTr = 0.025 * (H[a] - 0.5) + 0.015 * Rd[a] - 0.020 * (W[a] - 0.5) \
          - 0.35 * shock * (1 - Rd[a])
    Tr[a] = soft(Tr[a], dTr) if V2_SOFT else clip(Tr[a] + dTr)

    # ---------- 3.5 climate ---------------------------------------------------
    # warming decelerates with decarbonisation effort; high capability + decent
    # governance unlocks cheap abatement/repair
    abate = np.minimum(P["climate_eff"][a] * (0.4 + 0.6 * G[a]) * (1 + 1.0 * autom[a] * G[a]), 1.5)
    if V2_CLIMATE:
        # v2: per-world sensitivity multiplier on the warming increment + a sampled tipping
        # feedback once warming passes the world's threshold (widens the 2126 spread).
        dT = 0.024 * P["clim_sens"][a] * (1 - 0.45 * abate) - 0.008 * autom[a] * G[a]
        dT = dT + np.where(TEMP[a] > P["tip_threshold"][a], P["tip_rate"][a], 0.0)
    else:
        dT = 0.024 * (1 - 0.45 * abate) - 0.008 * autom[a] * G[a]
    TEMP[a] = np.maximum(TEMP[a] + dT, 1.0)
    climate_stress = clip((TEMP - 1.5) / 2.0)

    # ---------- 3.6 wellbeing & population ------------------------------------
    dH = 0.045 * autom[a] * (0.25 + 0.75 * Rd[a]) + 0.02 * (G[a] - 0.4) \
         - 0.02 * (W[a] - 0.5) - 0.035 * climate_stress[a] - 0.30 * shock * (1 - Rd[a])
    H[a] = soft(H[a], dH) if V2_SOFT else clip(H[a] + dH)
    # demographic transition: growth fades to ~0 mid-century, abundance+health lift longevity
    if V2_DEMO:
        # v2: fertility is positive before the world's sampled peak year and structurally
        # negative after it, so population can peak-and-decline rather than only rise.
        demo = P["fert_scale"][a] * np.tanh((P["pop_peak_year"][a] - year) / 40.0)
        base_pop_g = demo - 0.002 * climate_stress[a] + 0.0018 * autom[a] * H[a]
    else:
        base_pop_g = 0.007 * np.exp(-(year - 2026) / 40.0) - 0.002 * climate_stress[a] \
                     + 0.0018 * autom[a] * H[a]
    POP[a] = POP[a] * (1 + base_pop_g)

    # ---------- 3.7 warning shots (AI near-misses) ----------------------------
    p_shot = clip(0.02 + 0.10 * (C[a] - 0.5), 0, 0.15)
    shot = (_crnShot[ti][a] if CRN else rng.random(a.sum())) < p_shot
    idx = np.where(a)[0][shot]
    ev["warning_shot"][idx] += 1
    # accumulate decayed warning-shot memory. Drives next year's endogenous levers under
    # V2_POLICY and the erosion damping under V2_ERODE; maintained unconditionally so the
    # two switches stay separable (plan-28 Phase A step 3). Draws no RNG, and with both
    # switches off nothing reads it, so an unswitched run is unchanged.
    shot_hist *= POLICY_SHOT_DECAY
    shot_hist[idx] += 1.0
    # reactive: regulation drag + safety investment, scaled by responsiveness.
    # v2 STRUCT applies it always but with a per-world sampled magnitude react_scale
    # (0 reproduces the baseline off corner, 1 the on corner); baseline keeps the binary.
    if V2_STRUCT:
        _rs = P["react_scale"][idx]
        reg_drag[idx] = np.minimum(reg_drag[idx] + 0.15 * _rs * P["respond"][idx], 0.7)
        safety_bonus[idx] = np.minimum(safety_bonus[idx] + 0.004 * _rs * P["respond"][idx], 0.02)
    elif REC_REACT:
        reg_drag[idx] = np.minimum(reg_drag[idx] + 0.15 * P["respond"][idx], 0.7)
        safety_bonus[idx] = np.minimum(safety_bonus[idx] + 0.004 * P["respond"][idx], 0.02)

    # ---------- 3.8 hazard processes ------------------------------------------
    live_idx = np.where(a)[0]
    n_live = live_idx.size
    # baseline draws the six hazard uniforms sized to the live count; v2 HAZMASK draws
    # them at fixed shape (6, N) so the RNG stream is independent of how many worlds
    # remain alive (stream discipline — see hazard_mask above).
    u = _crnU[ti] if CRN else (rng.random((6, N)) if V2_HAZMASK else rng.random((6, n_live)))

    turb = (0.5 * shock * 10 + 0.3 * climate_stress[a] + 0.4 * W[a] * (1 - Tr[a])) * P["fragility"][a]
    race_heat = race_a * clip((C[a] - 0.55) / 0.35)          # racing near the threshold

    # regional war (frequent, non-absorbing): degrades trust/governance
    p_regional = clip(0.04 + 0.05 * turb, 0, 0.25)
    m = hazard_mask(u, 0, p_regional, live_idx, alive, V2_HAZMASK)
    ridx = live_idx[m]
    ev["regional_war"][ridx] += 1
    Tr[ridx] = clip(Tr[ridx] - 0.05); G[ridx] = clip(G[ridx] - 0.03)
    POP[ridx] *= (1 - 0.0015)

    # great-power nuclear war: base ~0.3%/yr, amplified by turbulence + AI race
    p_nuc = clip(0.003 * (1 + 1.5 * turb + 2.5 * race_heat), 0, 0.06)
    m = hazard_mask(u, 1, p_nuc, live_idx, alive, V2_HAZMASK)
    nidx = live_idx[m]
    if nidx.size:
        ev["nuclear_war"][nidx] += 1
        sev = _crnNukeSev[ti][nidx] if CRN else rng.random(nidx.size)
        # 70% "limited" exchange: 2-8% dead, big setbacks; 25% major: 15-35% dead;
        # 5% escalation to civilisational collapse
        limited = sev < 0.70
        major = (sev >= 0.70) & (sev < 0.95)
        coll = sev >= 0.95
        POP[nidx[limited]] *= rng.uniform(0.92, 0.98, limited.sum())
        POP[nidx[major]]   *= rng.uniform(0.65, 0.85, major.sum())
        C[nidx[limited]] *= 0.93; C[nidx[major]] *= 0.75
        G[nidx] = clip(G[nidx] - 0.10); Tr[nidx] = clip(Tr[nidx] - 0.10); H[nidx] = clip(H[nidx] - 0.15)
        if V2_NUKE_R:
            # v2: a nuclear exchange also sets back alignment/control readiness
            # (labs, compute, expert institutions destroyed): limited -0.03, major -0.10.
            R[nidx[limited]] = clip(R[nidx[limited]] - 0.03)
            R[nidx[major]]   = clip(R[nidx[major]] - 0.10)
        cidx = nidx[coll]
        if V2_REBUILD:
            rebuild_timer[cidx] = P["rebuild_period"][cidx]; ever_collapsed[cidx] = True
            alive[cidx] = False   # out during rebuild; re-enters via the top-of-loop block
        else:
            fate[cidx] = 2; fate_year[cidx] = year; alive[cidx] = False
        snapshot(cidx, "nuclear")
        POP[cidx] *= rng.uniform(0.3, 0.5, coll.sum())

    # engineered pandemic: biotech democratisation scales with capability;
    # defence scales with capability*readiness*biodefence investment
    offence = clip(0.001 + 0.012 * clip((C[a] - 0.45) / 0.5), 0, 0.02)
    defence = clip(0.3 + 0.7 * C[a] * R[a]) * P["bio_defense"][a]
    if V2_BIOUP:
        # v2: past the world's own AGI threshold, human misuse of AGI-grade biotools
        # keeps raising offence (the pre-threshold term saturates at C=0.95, which left
        # a far-post-AGI world facing the same bio ceiling as a near-threshold one).
        # The uplift ramps over 0.6 capability past the threshold; the cap doubles for
        # the uplifted regime, and the existing capability x readiness x biodefence
        # defence term still gates it, so well-governed worlds stay protected. This is
        # the MISUSE channel — agentic AI risk stays in the takeover hazard. No RNG is
        # drawn, so the stream is unchanged; baseline keeps the saturating offence + 2% cap.
        offence = offence + 0.012 * clip((C[a] - P["threshold"][a]) / 0.60)
        p_bio = clip(offence * (1 - 0.8 * defence), 0, 0.04)
    else:
        p_bio = clip(offence * (1 - 0.8 * defence), 0, 0.02)
    m = hazard_mask(u, 2, p_bio, live_idx, alive, V2_HAZMASK)
    bidx = live_idx[m]
    if AUDIT:
        # HAZMASK invariant: a world absorbed earlier this year must receive no
        # engineered-pandemic event. Baseline counts them (bug); HAZMASK yields 0.
        audit_pandemic_post_absorption += int((~alive[bidx]).sum())
    if bidx.size:
        ev["eng_pandemic"][bidx] += 1
        sev = _crnBioSev[ti][bidx] if CRN else rng.random(bidx.size)
        mild = sev < 0.75; severe = (sev >= 0.75) & (sev < 0.97); extreme = sev >= 0.97
        POP[bidx[mild]]   *= rng.uniform(0.97, 0.995, mild.sum())
        POP[bidx[severe]] *= rng.uniform(0.75, 0.92, severe.sum())
        Tr[bidx] = clip(Tr[bidx] - 0.08); H[bidx] = clip(H[bidx] - 0.10)
        xidx = bidx[extreme]
        xidx = xidx[fate[xidx] == 0]
        # extreme engineered agent: collapse, small chance of extinction
        sev2 = _crnBioSev2[ti][xidx] if CRN else rng.random(xidx.size)
        ext = sev2 < 0.25
        _extx = xidx[ext]; _collx = xidx[~ext]
        fate[_extx] = 1; fate_year[_extx] = year
        if V2_REBUILD:
            rebuild_timer[_collx] = P["rebuild_period"][_collx]; ever_collapsed[_collx] = True
        else:
            fate[_collx] = 2; fate_year[_collx] = year
        alive[xidx] = False
        snapshot(xidx, "pandemic")
        POP[xidx] *= rng.uniform(0.02, 0.3, xidx.size)

    # natural pandemic (COVID-class): non-absorbing
    if V2_NATPAND:
        # v2: COVID-class detection and response scale with capability and biodefence,
        # so the flat 0.025/yr becomes a modulated rate (better-prepared worlds see
        # fewer such events); the floor keeps a residual background rate.
        p_nat = clip(0.025 * (1 - 0.6 * C[a] * P["bio_defense"][a]), 0.005, 0.025)
    else:
        p_nat = 0.025
    m = hazard_mask(u, 3, p_nat, live_idx, alive, V2_HAZMASK)
    pidx = live_idx[m]
    if AUDIT:
        audit_pandemic_post_absorption += int((~alive[pidx]).sum())
    ev["nat_pandemic"][pidx] += 1
    POP[pidx] *= 0.998; H[pidx] = clip(H[pidx] - 0.03); Tr[pidx] = clip(Tr[pidx] - 0.02)

    # misaligned-AI takeover: hazard only in the post-AGI transition window,
    # driven by the capability-readiness gap; decays as the window closes
    if V2_GAPNORM:
        # v2: normalise the capability-readiness gap by the world's own AGI threshold
        # so a high-threshold world is not mechanically punished for a large absolute gap.
        gap_now = np.maximum((C[a] - R[a]) * (GAPNORM_REF / P["threshold"][a]), 0)
    else:
        gap_now = np.maximum(C[a] - R[a], 0)
    if V2_STRUCT:
        # v2: per-world sampled takeover window — flat (no deadline) for the sampled
        # prior mass on persistent risk, else exponential decay with the world's own
        # timescale tau. Supersedes the binary REC_WINDOW.
        _flat = P["struct_flat"][a] > 0.5
        window = np.where(_flat, 1.0, np.exp(-post_agi_years[a] / P["tau_window"][a]))
    elif REC_WINDOW:
        window = np.exp(-post_agi_years[a] / 10.0)
    else:
        window = np.ones(a.sum())
    p_take = np.where(agi_year[a] > 0,
                      clip(0.030 * clip((gap_now - 0.15) / 0.50) ** 2 * window * (1 + race_a), 0, 0.07),
                      0.0)
    m = hazard_mask(u, 4, p_take, live_idx, alive, V2_HAZMASK)
    tidx = live_idx[m]
    tidx = tidx[fate[tidx] == 0]
    if tidx.size:
        sev = _crnTakeSev[ti][tidx] if CRN else rng.random(tidx.size)
        # extinction-grade vs permanent disempowerment. Baseline is the fixed 30% the
        # documents flag as the one parameter nothing softens; v2 STRUCT samples it
        # per world (Beta mean 0.30).
        lethal = P["lethal_share"][tidx] if V2_STRUCT else 0.30
        e = sev < lethal
        fate[tidx[e]] = 1; fate[tidx[~e]] = 4
        fate_year[tidx] = year; alive[tidx] = False
        snapshot(tidx, "takeover")

    # totalitarian lock-in: post-AGI, requires high concentration + weak democracy
    # + enough control to actually enforce it (readiness used for domination)
    p_lock = np.where(agi_year[a] > 0,
                      clip(0.012 * clip((W[a] - 0.6) / 0.4) * clip((0.5 - G[a]) / 0.5) * clip(R[a] / 0.6), 0, 0.02),
                      0.0)
    m = hazard_mask(u, 5, p_lock, live_idx, alive, V2_HAZMASK)
    lidx = live_idx[m]
    lidx = lidx[fate[lidx] == 0]
    fate[lidx] = 3; fate_year[lidx] = year; alive[lidx] = False
    snapshot(lidx, "lockin")

    # v2 unknown-unknowns: a small absorbing hazard for risks outside the named channels
    if V2_XHAZ:
        _xroll = _crnXhaz[ti] if CRN else rng.random(N)
        xidx2 = np.where(alive & (_xroll < P["xhaz_rate"]) & (fate == 0))[0]
        fate[xidx2] = 5; fate_year[xidx2] = year; alive[xidx2] = False
        snapshot(xidx2, "unknown")

    if year in DEC_YEARS:
        dec_snap[year] = {nm: arr.astype(np.float32).copy() for nm, arr in
                          (("C", C), ("R", R), ("W", W), ("Rd", Rd), ("H", H),
                           ("G", G), ("TEMP", TEMP), ("POP", POP))}

    # ---------- decadal snapshot (medians across still-ongoing worlds) --------
    if DECADAL and year % 10 == 0:
        m = alive
        if m.any():
            dec_rows.append({
                "year": int(year),
                "ongoing_%": round(100.0 * m.mean(), 1),
                "C": round(float(np.median(C[m])), 2),
                "R": round(float(np.median(R[m])), 2),
                "gap": round(float(np.median(C[m] - R[m])), 2),
                "W": round(float(np.median(W[m])), 2),
                "H": round(float(np.median(H[m])), 2),
                "G": round(float(np.median(G[m])), 2),
                "temp": round(float(np.median(TEMP[m])), 2),
                "pop": round(float(np.median(POP[m])), 1),
                "agi_crossed_%": round(100.0 * float((agi_year[m] > 0).mean()), 1),
            })

    # gradual disempowerment (non-event): sustained huge gap + high concentration
    # erodes human agency until control is unrecoverable
    drift = a & (agi_year > 0) & ((C - R) > 0.40) & (W > 0.70) & (post_agi_years > 10)
    m2 = (_crnDrift[ti] if CRN else rng.random(N)) < 0.025
    didx = np.where(drift & m2 & (fate == 0))[0]
    fate[didx] = 4; fate_year[didx] = year; alive[didx] = False
    snapshot(didx, "drift")

    if AUDIT:
        # saturation diagnostic (consumed by check_century.py --pinned-audit): for each
        # bounded variable, count the still-alive worlds sitting within 0.01 of a [0, 1]
        # bound this year. The baseline clip rails H/Rd/G/Tr near 1.0 post-2070; V2_SOFT
        # keeps them off the bounds.
        _ay = alive
        audit_alive_years += int(_ay.sum())
        for _nm, _ar in (("W", W), ("Rd", Rd), ("G", G), ("Tr", Tr), ("H", H)):
            audit_pinned[_nm] += int((((_ar <= 0.01) | (_ar >= 0.99)) & _ay).sum())

# ----------------------------------------------------------------------------
# 4. CLASSIFY SURVIVING WORLDS AT 2126
# ----------------------------------------------------------------------------
final = np.full(N, "", dtype=object)
final[fate == 1] = "extinction"
final[fate == 2] = "collapse"
final[fate == 3] = "lockin"
final[fate == 4] = "disempowerment"
final[fate == 5] = "unknown_catastrophe"

surv = fate == 0
agi_ok = surv & (agi_year > 0)
no_agi = surv & (agi_year < 0)

# among post-AGI survivors: abundance vs oligarchic vs fragile
#
# CUTOFF VALIDATION against the soft dynamics (plan-27 FU-008). These cutoffs were
# originally tuned to the baseline clip dynamics, where survivor H/Rd/G rail near ~1.0
# and W deconcentrates to ~0.2 by 2126. Under the soft (logistic) dynamics the
# stationary distributions differ: survivor H settles near ~0.78 (not 1.0), and W
# does not deconcentrate (the late-century fall to ~0.2 is a clip artefact). The
# concern was that at the unchanged cutoffs the W < 0.62 boundary would coincide with
# a soft-W mode and collapse the abundance share into oligarchic. Measured against
# the corrected (level-neutral GAPNORM, plan-27 Phase 1) survivor distribution via
# `check_century.py --cutoff-audit`, that pathology is NOT present: survivor W over
# post-AGI survivors is broad (p10-p90 ~0.42-0.85) with a shallow ANTIMODE at
# ~0.55-0.65 and a concentrated peak at ~0.75-0.85, so the W < 0.62 separatrix sits
# in the low-density antimode (robust, not on a mode), and the split is a healthy
# abundance ~38.7% / oligarchic ~44.5% / fragile ~16.7% of post-AGI survivors. The
# H > 0.62 / H > 0.40 / Rd > 0.35 gates admit the bulk of survivors (soft H ~0.78,
# Rd median ~0.71). Cutoffs are therefore KEPT (validated, not merely unchanged); the
# baseline path stays bit-identical because classification runs only on v2 survivors.
abundant = agi_ok & (H > 0.62) & (Rd > 0.35) & (W < 0.62)
oligarch = agi_ok & ~abundant & (W >= 0.62) & (H > 0.40)
fragile  = agi_ok & ~abundant & ~oligarch
final[abundant] = "aligned_abundance"
final[oligarch] = "oligarchic_prosperity"
final[fragile]  = "turbulent_transition"

# no-AGI worlds: constrained flourishing vs stagnation/degraded
flourish = no_agi & (H > 0.55) & (G > 0.40)
final[flourish] = "constrained_flourishing"
final[no_agi & ~flourish] = "muddling_degraded"

if V2_REBUILD:
    # v2 REBUILD: collapse is non-absorbing. A world that collapsed and re-entered is
    # marked "recovered" (overriding whichever survivor class it reached); a world still
    # mid-rebuild at 2126 (never re-entered) counts as "collapse" (still down). Extinction
    # and the post-AGI terminal fates are untouched.
    final[(fate == 0) & recovered] = "recovered"
    final[(fate == 0) & ever_collapsed & ~recovered] = "collapse"

# ----------------------------------------------------------------------------
# 5. REPORT
# ----------------------------------------------------------------------------
def pct(x):
    # Guard degenerate quantile/override subsets: a statistic over an empty mask
    # has no defined share, so report it as null rather than let np.mean warn and
    # emit NaN. Non-empty masks keep the exact numpy computation (byte-identical
    # baseline output). Emitted with allow_nan=False below so any NaN is a hard error.
    x = np.asarray(x)
    return None if x.size == 0 else 100.0 * np.mean(x)


def rnd(v, nd):
    return None if v is None else round(v, nd)


def swing(hi, lo):
    # top-minus-bottom difference of two subset shares; null if either subset is
    # empty (e.g. the plateau override leaves no non-plateau worlds), so the
    # subtraction never touches a NaN/None operand.
    a, b = pct(hi), pct(lo)
    return None if a is None or b is None else round(a - b, 1)

order = ["aligned_abundance", "oligarchic_prosperity", "turbulent_transition",
         "constrained_flourishing", "muddling_degraded",
         "disempowerment", "lockin", "collapse", "extinction"]
# New v2 outcome classes are appended only when their switch is on, so the baseline
# outcomes block keeps its exact nine keys (the golden regression gate depends on it).
if V2_XHAZ:
    order.append("unknown_catastrophe")
if V2_REBUILD:
    order.append("recovered")

out = {"N": N, "outcomes": {}}
for o in order:
    out["outcomes"][o] = rnd(pct(final == o), 2)

has_agi = agi_year > 0
# Guard the all-no-AGI ensemble (reachable via CENTURY_OVERRIDES pinning plateau plus a
# low ceiling/threshold combination): quantiles over an empty crossing set have no value,
# so emit null rather than crash — the same contract pct() applies to empty subsets.
# Non-empty ensembles keep the exact computation (byte-identical output).
_n_agi = int(has_agi.sum())
out["agi"] = {
    "p_agi_by_2126": rnd(pct(has_agi), 1),
    "median_year": int(np.median(agi_year[has_agi])) if _n_agi else None,
    "p10_year": int(np.percentile(agi_year[has_agi], 10)) if _n_agi else None,
    "p90_year": int(np.percentile(agi_year[has_agi], 90)) if _n_agi else None,
    "p_by_2035": rnd(pct(has_agi & (agi_year <= 2035)), 1),
    "p_by_2040": rnd(pct(has_agi & (agi_year <= 2040)), 1),
    "p_by_2050": rnd(pct(has_agi & (agi_year <= 2050)), 1),
    "p_by_2075": rnd(pct(has_agi & (agi_year <= 2075)), 1),
    # Two complements the documents quote directly. Emitted rather than left to be derived in
    # prose so --doc-figures can pin them like every other cell.
    "p_no_agi_by_2126": rnd(pct(~has_agi), 1),
    "p_after_2050": rnd(pct(has_agi & (agi_year >= 2050)), 1),
}
g = gap_at_agi[has_agi]
out["gap_at_agi"] = {
    "median": round(float(np.median(g)), 3) if _n_agi else None,
    "p_controlled(gap<0.15)": round(100 * np.mean(g < 0.15), 1) if _n_agi else None,
    "p_contested(0.15-0.35)": round(100 * np.mean((g >= 0.15) & (g < 0.35)), 1) if _n_agi else None,
    "p_uncontrolled(>0.35)": round(100 * np.mean(g >= 0.35), 1) if _n_agi else None,
}
out["events_per_world"] = {k: round(float(v.mean()), 3) for k, v in ev.items()}
out["p_at_least_one_nuclear_war"] = rnd(pct(ev["nuclear_war"] > 0), 1)
out["p_at_least_one_eng_pandemic"] = rnd(pct(ev["eng_pandemic"] > 0), 1)

okset = {"aligned_abundance", "constrained_flourishing", "oligarchic_prosperity"}
good = np.isin(final, list(okset))
verygood = final == "aligned_abundance"
_bad_classes = ["extinction", "collapse", "lockin", "disempowerment"]
if V2_XHAZ:
    _bad_classes.append("unknown_catastrophe")   # an absorbing catastrophe is irreversibly bad
bad = np.isin(final, _bad_classes)
out["aggregates"] = {
    "good(broadly acceptable)": rnd(pct(good), 1),
    "aligned_abundance_only": rnd(pct(verygood), 1),
    "irreversible_bad": rnd(pct(bad), 1),
    "extinction_or_collapse": rnd(pct(np.isin(final, ["extinction", "collapse"])), 1),
}

if WEIGHTS is not None:
    # Phase 7: anchor-weighted outcome and aggregate tables (importance reweighting
    # toward the outside-view anchors). Reported next to the unweighted tables so the
    # extinction 15.6%-vs-1-6% tension becomes a quantified before/after statement.
    _wsum = float(WEIGHTS.sum())

    def wshare(_mask):
        return round(100.0 * float(WEIGHTS[_mask].sum()) / _wsum, 2) if _wsum > 0 else None

    out["outcomes_weighted"] = {o: wshare(final == o) for o in order}
    out["aggregates_weighted"] = {
        "good(broadly acceptable)": wshare(good),
        "aligned_abundance_only": wshare(verygood),
        "irreversible_bad": wshare(bad),
        "extinction_or_collapse": wshare(np.isin(final, ["extinction", "collapse"])),
    }
    out["weights_ess_fraction"] = round(float(_wsum ** 2 / float((WEIGHTS ** 2).sum())) / N, 4)

if LEVER_WEIGHTS is not None:
    # Third view: lever-feasibility-weighted outcome and aggregate tables ("the
    # realistic bet"). The unweighted tables average over flat lever priors — an
    # implicit forecast that strong redistribution is as likely as weak; these
    # tables replace that with the documented feasibility judgements of
    # lever-anchors.json, so the gap between the two quantifies how much of the
    # century's fate rests on levers the world is unlikely to pull unprompted.
    _lwsum = float(LEVER_WEIGHTS.sum())

    def lwshare(_mask):
        return round(100.0 * float(LEVER_WEIGHTS[_mask].sum()) / _lwsum, 2) if _lwsum > 0 else None

    out["outcomes_lever_weighted"] = {o: lwshare(final == o) for o in order}
    out["aggregates_lever_weighted"] = {
        "good(broadly acceptable)": lwshare(good),
        "aligned_abundance_only": lwshare(verygood),
        "irreversible_bad": lwshare(bad),
        "extinction_or_collapse": lwshare(np.isin(final, ["extinction", "collapse"])),
    }
    out["lever_weights_ess_fraction"] = round(
        float(_lwsum ** 2 / float((LEVER_WEIGHTS ** 2).sum())) / N, 4)

if V2_STRUCT:
    # structure-conditional outcomes (Phase 5): outcomes sliced by the sampled
    # takeover-window structure, so the §6.1 21-point swing between the flat-window
    # (persistent-risk) prior and the short-tau (recovery) prior becomes a gradient
    # inside one ensemble rather than two rival documents. Shorter tau (faster window
    # closure) should be monotonically safer.
    _flat = P["struct_flat"] > 0.5
    _tau = P["tau_window"]
    _nf = ~_flat
    out["structure_conditional"] = {
        "prior_p_flat": STRUCT_P_FLAT,
        "P(good)|flat_window": rnd(pct(good[_flat]), 1),
        "P(good)|tau<8yr": rnd(pct(good[_nf & (_tau < 8)]), 1),
        "P(irreversible_bad)|flat_window": rnd(pct(bad[_flat]), 1),
        "P(irreversible_bad)|tau>=15yr": rnd(pct(bad[_nf & (_tau >= 15)]), 1),
        "P(irreversible_bad)|8<=tau<15yr": rnd(pct(bad[_nf & (_tau >= 8) & (_tau < 15)]), 1),
        "P(irreversible_bad)|tau<8yr": rnd(pct(bad[_nf & (_tau < 8)]), 1),
    }

surv_mask = fate == 0
out["endstate_2126_survivors"] = {
    "median_pop_bn": round(float(np.median(POP[surv_mask])), 2),
    "median_warming_C": round(float(np.median(TEMP[surv_mask])), 2),
    "median_wellbeing": round(float(np.median(H[surv_mask])), 2),
    "median_concentration": round(float(np.median(W[surv_mask])), 2),
    "pop_bn_p10_p90": [round(float(np.percentile(POP[surv_mask], 10)), 2),
                       round(float(np.percentile(POP[surv_mask], 90)), 2)],
    "warming_C_p10_p90": [round(float(np.percentile(TEMP[surv_mask], 10)), 2),
                          round(float(np.percentile(TEMP[surv_mask], 90)), 2)],
}

# FU-008 cutoff audit (env-gated, off by default so the headline JSON is unchanged):
# the survivor W/H/Rd/G distributions over post-AGI survivors, from which the
# abundance/oligarchic/fragile cutoffs are derived against the soft dynamics.
if os.environ.get("CENTURY_CUTOFF_AUDIT"):
    def _q5(v):
        return [round(float(x), 3) for x in np.quantile(v, [0.10, 0.25, 0.50, 0.75, 0.90])]
    def _hist20(v):
        counts, _ = np.histogram(v, bins=20, range=(0.0, 1.0))
        return [int(c) for c in counts]
    _nao = int(agi_ok.sum()) or 1
    out["survivor_cutoff_audit"] = {
        "n_agi_survivors": int(agi_ok.sum()),
        "quantiles_p10_p25_p50_p75_p90": {
            "W_concentration": _q5(W[agi_ok]),
            "H_wellbeing": _q5(H[agi_ok]),
            "Rd_redistribution": _q5(Rd[agi_ok]),
            "G_governance": _q5(G[agi_ok]),
        },
        "hist20_0to1": {
            "W_concentration": _hist20(W[agi_ok]),
            "H_wellbeing": _hist20(H[agi_ok]),
        },
        "current_shares_pct_of_agi_survivors": {
            "aligned_abundance": round(100.0 * int(abundant.sum()) / _nao, 1),
            "oligarchic_prosperity": round(100.0 * int(oligarch.sum()) / _nao, 1),
            "turbulent_transition_fragile": round(100.0 * int(fragile.sum()) / _nao, 1),
        },
    }

# ---- sensitivity: P(good) by parameter quartile -----------------------------
SENS_NAMES = ["assist", "race", "respond", "alpha", "k", "safety_eff", "R0",
              "redist_will", "bio_defense", "fragility", "threshold", "climate_eff",
              "concentration0"]
# erode_mag is only drawn when its switch is on, so registering it unconditionally would
# KeyError on the baseline path. Appended the same way V2_XHAZ appends its outcome class, which
# also keeps the baseline sensitivity block at its exact original key set.
if V2_ERODE:
    SENS_NAMES.append("erode_mag")

sens = {}
for name in SENS_NAMES:
    v = P[name].astype(float)
    qs = np.quantile(v, [0.25, 0.5, 0.75])
    lo = v <= qs[0]; hi = v >= qs[2]
    sens[name] = {
        "P(good)|bottom_quartile": rnd(pct(good[lo]), 1),
        "P(good)|top_quartile": rnd(pct(good[hi]), 1),
        "swing": swing(good[hi], good[lo]),
    }
sens["plateau"] = {
    "P(good)|no_plateau": rnd(pct(good[~P["plateau"]]), 1),
    "P(good)|plateau": rnd(pct(good[P["plateau"]]), 1),
    "swing": swing(good[P["plateau"]], good[~P["plateau"]]),
}
out["sensitivity_P_good"] = dict(sorted(sens.items(), key=lambda kv: float("inf") if kv[1]["swing"] is None else -abs(kv[1]["swing"])))
# These quartile swings are MARGINAL-ONLY (one parameter at a time); they cannot see
# interactions such as safety-effort-given-race. Under V2_CORR they are additionally
# CONFOUNDED by the copula prior correlations: e.g. with race,respond = -0.4 the top-race
# quartile is systematically low-respond, so the "race swing" bundles both effects and
# can mis-rank levers. Variance-based first-order and total Sobol indices, which handle
# both problems, are produced by sobol_century.py (Phase 8) — use those for lever ranking.
out["sensitivity_note"] = ("quartile swings are marginal-only and, under V2_CORR, confounded by the "
                           "copula prior correlations (a top-race quartile is systematically "
                           "low-respond); use the Sobol indices from sobol_century.py for lever ranking")

disw = final == "disempowerment"
sens_d = {}
for name in SENS_NAMES:
    v = P[name].astype(float)
    qs = np.quantile(v, [0.25, 0.75])
    lo = v <= qs[0]; hi = v >= qs[1]
    sens_d[name] = {
        "P(disemp)|bottom_quartile": rnd(pct(disw[lo]), 1),
        "P(disemp)|top_quartile": rnd(pct(disw[hi]), 1),
        "swing": swing(disw[hi], disw[lo]),
    }
sens_d["plateau"] = {
    "P(disemp)|no_plateau": rnd(pct(disw[~P["plateau"]]), 1),
    "P(disemp)|plateau": rnd(pct(disw[P["plateau"]]), 1),
    "swing": swing(disw[P["plateau"]], disw[~P["plateau"]]),
}
out["sensitivity_P_disempowerment"] = dict(sorted(sens_d.items(), key=lambda kv: float("inf") if kv[1]["swing"] is None else -abs(kv[1]["swing"])))

# conditional structure
# The headline split three ways by the base growth rate. k is the input with the largest
# total-order index and the widest reach in the model, and nothing constrains it except the
# arrival bands of the calibration, which currently sit loose enough to be inactive (section
# 8). Averaging over its prior therefore reports a single number that hides the model's
# dominant uncertainty, so the tertile split is emitted alongside it and quoted in section 3.
# Conditioning on the existing ensemble rather than pinning k keeps the within-tertile spread.
_kt1, _kt2 = np.quantile(P["k"], [1.0 / 3.0, 2.0 / 3.0])
_mixed = (final == "turbulent_transition") | (final == "muddling_degraded") | (final == "recovered")
def _k_slice(_m):
    _h = agi_year[_m]
    _c = _h > 0
    return {
        "good": rnd(pct(good[_m]), 1),
        "mixed": rnd(pct(_mixed[_m]), 1),
        "irreversible_bad": rnd(pct(bad[_m]), 1),
        "extinction": rnd(pct((final == "extinction")[_m]), 1),
        "median_agi_year": int(np.median(_h[_c])) if _c.any() else None,
    }
out["headline_by_k_tertile"] = {
    "k_cuts": [round(float(_kt1), 4), round(float(_kt2), 4)],
    "slowest_third": _k_slice(P["k"] < _kt1),
    "middle_third": _k_slice((P["k"] >= _kt1) & (P["k"] < _kt2)),
    "fastest_third": _k_slice(P["k"] >= _kt2),
}

out["conditionals"] = {
    "P(bad)|gap>0.35_at_agi": rnd(pct(bad[has_agi & (gap_at_agi > 0.35)]), 1),
    "P(bad)|gap<0.15_at_agi": rnd(pct(bad[has_agi & (gap_at_agi < 0.15)]), 1),
    "P(abundance)|gap<0.15": rnd(pct(verygood[has_agi & (gap_at_agi < 0.15)]), 1),
    "P(bad)|agi<=2035": rnd(pct(bad[has_agi & (agi_year <= 2035)]), 1),
    "P(bad)|agi>2050": rnd(pct(bad[has_agi & (agi_year > 2050)]), 1),
    "P(bad)|no_agi": rnd(pct(bad[~has_agi]), 1),
    "P(good)|top_assist_and_respond": rnd(pct(good[(P["assist"] > np.quantile(P["assist"], 0.75)) & (P["respond"] > np.quantile(P["respond"], 0.75))]), 1),
    "P(good)|bottom_assist_and_respond": rnd(pct(good[(P["assist"] < np.quantile(P["assist"], 0.25)) & (P["respond"] < np.quantile(P["respond"], 0.25))]), 1),
    "P(disemp)|gap<0.15_at_agi": rnd(pct((final == "disempowerment")[has_agi & (gap_at_agi < 0.15)]), 1),
    "P(disemp)|gap>0.35_at_agi": rnd(pct((final == "disempowerment")[has_agi & (gap_at_agi > 0.35)]), 1),
    "P(disemp)|agi<=2035": rnd(pct((final == "disempowerment")[has_agi & (agi_year <= 2035)]), 1),
    "P(disemp)|agi>2050": rnd(pct((final == "disempowerment")[has_agi & (agi_year > 2050)]), 1),
    "P(disemp)|no_agi": rnd(pct((final == "disempowerment")[~has_agi]), 1),
}

# fate-year distribution for absorbing bads
if (fate > 0).any():
    fy = fate_year[fate > 0]
    out["bad_event_timing"] = {
        "median_year": int(np.median(fy)),
        "p10": int(np.percentile(fy, 10)),
        "p90": int(np.percentile(fy, 90)),
    }

ab = final == "aligned_abundance"
if ab.any():
    prof_a = {"n": int(ab.sum())}
    ay = agi_year[ab]
    prof_a["agi_year_q25_50_75"] = [int(np.percentile(ay, q_)) for q_ in (25, 50, 75)]
    ga = gap_at_agi[ab]
    prof_a["gap_at_agi_q25_50_75"] = [round(float(np.percentile(ga, q_)), 2) for q_ in (25, 50, 75)]
    prof_a["crossing_condition_%"] = {
        "controlled(gap<0.15)": round(100 * float(np.mean(ga < 0.15)), 1),
        "contested(0.15-0.35)": round(100 * float(np.mean((ga >= 0.15) & (ga < 0.35))), 1),
        "uncontrolled(>0.35)": round(100 * float(np.mean(ga >= 0.35)), 1)}
    prof_a["param_median_abundance_vs_all"] = {
        nm: [round(float(np.median(P[nm][ab].astype(float))), 3),
             round(float(np.median(P[nm].astype(float))), 3)]
        for nm in ["k", "alpha", "safety_eff", "assist", "race", "respond",
                   "redist_will", "R0", "threshold"]}
    prof_a["plateau_share_%_vs_all"] = [round(100 * float(P["plateau"][ab].mean()), 1),
                                        round(100 * float(P["plateau"].mean()), 1)]
    prof_a["events_mean"] = {k_: round(float(v_[ab].mean()), 2) for k_, v_ in ev.items()}
    prof_a["p_at_least_one_nuclear_war_%"] = round(100 * float((ev["nuclear_war"][ab] > 0).mean()), 1)
    prof_a["decadal_medians"] = [
        {"year": int(y_), **{nm: round(float(np.median(dec_snap[y_][nm][ab])), 2)
                        for nm in ["C", "R", "W", "Rd", "H", "G", "TEMP", "POP"]},
         "gap": round(float(np.median(dec_snap[y_]["C"][ab] - dec_snap[y_]["R"][ab])), 2)}
        for y_ in sorted(dec_snap)]
    out["abundance_profile"] = prof_a

ex = final == "extinction"
if ex.any():
    prof_e = {"n": int(ex.sum())}
    che = fate_channel[ex]
    prof_e["channel_shares_%"] = {c: round(100 * float((che == c).mean()), 1)
                                  for c in ["takeover", "pandemic"]}
    prof_e["fate_year_q25_50_75"] = [int(np.percentile(fate_year[ex], q_)) for q_ in (25, 50, 75)]
    # years between AGI crossing and the end (takeover channel requires AGI). Guard the
    # zero-crossing subset — all extinctions can arrive via the pandemic channel with no
    # AGI (e.g. a pinned-plateau override run), so these quantiles can have no value.
    exa = ex & (agi_year > 0)
    _n_exa = int(exa.sum())
    yrs_post = (fate_year[exa] - agi_year[exa]).astype(float)
    prof_e["years_from_agi_to_end_q25_50_75"] = ([round(float(np.percentile(yrs_post, q_)), 1) for q_ in (25, 50, 75)]
                                                 if _n_exa else None)
    prof_e["p_agi_crossed_%"] = round(100 * float(exa.sum() / ex.sum()), 1)
    ge = gap_at_agi[exa]
    prof_e["gap_at_agi_q25_50_75"] = ([round(float(np.percentile(ge, q_)), 2) for q_ in (25, 50, 75)]
                                      if _n_exa else None)
    for nme in ["W", "Rd", "H", "G", "C", "R"]:
        v_ = snap[nme][ex]; v_ = v_[~np.isnan(v_)]
        prof_e[nme + "_at_fate_q25_50_75"] = [round(float(np.percentile(v_, q_)), 2) for q_ in (25, 50, 75)]
    prof_e["param_median_extinction_vs_all"] = {
        nm: [round(float(np.median(P[nm][ex].astype(float))), 3),
             round(float(np.median(P[nm].astype(float))), 3)]
        for nm in ["k", "alpha", "safety_eff", "assist", "race", "respond",
                   "redist_will", "bio_defense", "fragility"]}
    prof_e["events_mean_before_end"] = {k_: round(float(v_[ex].mean()), 2) for k_, v_ in ev.items()}
    # channel-split medians
    for c in ["takeover", "pandemic"]:
        mm = ex & (fate_channel == c)
        if mm.any():
            prof_e["median_by_channel_" + c] = {
                "fate_year": int(np.median(fate_year[mm])),
                **{nme: round(float(np.nanmedian(snap[nme][mm])), 2)
                   for nme in ["W", "H", "G", "C", "R"]}}
    out["extinction_profile"] = prof_e

fl = final == "constrained_flourishing"
if fl.any():
    prof_f = {"n": int(fl.sum())}
    prof_f["plateau_share_%_vs_all"] = [round(100 * float(P["plateau"][fl].mean()), 1),
                                        round(100 * float(P["plateau"].mean()), 1)]
    hard = P["ceiling"][fl] < P["threshold"][fl]          # capability ceiling below AGI threshold
    prof_f["hard_ceiling_share_%"] = round(100 * float(hard.mean()), 1)
    prof_f["param_median_flourishing_vs_all"] = {
        nm: [round(float(np.median(P[nm][fl].astype(float))), 3),
             round(float(np.median(P[nm].astype(float))), 3)]
        for nm in ["k", "alpha", "threshold", "safety_eff", "race", "redist_will", "climate_eff"]}
    prof_f["C_2126_q25_50_75"] = [round(float(np.percentile(C[fl], q_)), 2) for q_ in (25, 50, 75)]
    prof_f["R_2126_q25_50_75"] = [round(float(np.percentile(R[fl], q_)), 2) for q_ in (25, 50, 75)]
    dist = P["threshold"][fl] - C[fl]
    prof_f["threshold_minus_C_2126_q25_50_75"] = [round(float(np.percentile(dist, q_)), 2) for q_ in (25, 50, 75)]
    prof_f["gap_if_crossed_now_q50"] = round(float(np.median(C[fl] - R[fl])), 2)
    prof_f["events_mean"] = {k_: round(float(v_[fl].mean()), 2) for k_, v_ in ev.items()}
    prof_f["p_at_least_one_nuclear_war_%"] = round(100 * float((ev["nuclear_war"][fl] > 0).mean()), 1)
    prof_f["endstate_2126_medians"] = {
        nm: round(float(np.median(arr[fl])), 2)
        for nm, arr in (("H", H), ("W", W), ("Rd", Rd), ("G", G), ("Tr", Tr), ("TEMP", TEMP), ("POP", POP))}
    prof_f["decadal_medians"] = [
        {"year": int(y_), **{nm: round(float(np.median(dec_snap[y_][nm][fl])), 2)
                             for nm in ["C", "R", "W", "Rd", "H", "G", "TEMP", "POP"]}}
        for y_ in sorted(dec_snap)]
    # sibling: what separates flourishing from the degraded no-AGI worlds
    mud = final == "muddling_degraded"
    if mud.any():
        prof_f["vs_muddling_param_medians"] = {
            nm: [round(float(np.median(P[nm][fl].astype(float))), 3),
                 round(float(np.median(P[nm][mud].astype(float))), 3)]
            for nm in ["redist_will", "climate_eff", "race", "fragility", "respond"]}
        prof_f["muddling_n"] = int(mud.sum())
    out["flourishing_profile"] = prof_f

dis = final == "disempowerment"
if dis.any():
    def q(x, m):
        v = x[m][~np.isnan(x[m])]
        return [round(float(np.percentile(v, p_)), 2) for p_ in (25, 50, 75)]
    ch = fate_channel[dis]
    prof = {"n": int(dis.sum()),
            "channel_shares_%": {c: round(100 * float((ch == c).mean()), 1)
                                 for c in ["takeover", "drift"]},
            "fate_year_q25_50_75": [int(np.percentile(fate_year[dis], p_)) for p_ in (25, 50, 75)]}
    for nme in ["W", "Rd", "H", "G", "C", "R", "POP"]:
        prof[nme + "_at_fate_q25_50_75"] = q(snap[nme], dis)
    g_ = snap["C"][dis] - snap["R"][dis]
    g_ = g_[~np.isnan(g_)]
    prof["gap_at_fate_q25_50_75"] = [round(float(np.percentile(g_, p_)), 2) for p_ in (25, 50, 75)]
    # channel-split medians for the headline variables
    for c in ["takeover", "drift"]:
        mm = dis & (fate_channel == c)
        if mm.any():
            prof["median_by_channel_" + c] = {
                nme: round(float(np.nanmedian(snap[nme][mm])), 2)
                for nme in ["W", "Rd", "H", "G", "C", "R"]}
    out["disempowerment_profile"] = prof

if DECADAL:
    out["decadal"] = dec_rows
if AUDIT:
    # HAZMASK diagnostic (consumed by check_century.py --hazmask-audit): worlds that
    # received a pandemic event while already absorbed earlier the same year. The
    # HAZMASK correction drives this to 0; the baseline path leaves it positive.
    out["audit_pandemic_post_absorption"] = int(audit_pandemic_post_absorption)
    out["audit_pinned_fraction"] = {
        nm: (round(audit_pinned[nm] / audit_alive_years, 4) if audit_alive_years else None)
        for nm in ["W", "Rd", "G", "Tr", "H"]}
    if V2_CORR:
        # copula diagnostic (consumed by check_century.py --corr-audit): the matrix was
        # positive definite (Cholesky above succeeded); the realised pairwise RANK
        # (Spearman) correlations of the reordered marginals — a Gaussian copula's
        # invariant, unaffected by the marginals' shapes (e.g. k's lognormal skew, which
        # would attenuate Pearson); and p10/p50/p90 of each correlated marginal, which,
        # being a permutation of the independent sample, are preserved exactly.
        def _spearman(_x, _y):
            _rx = np.argsort(np.argsort(_x)); _ry = np.argsort(np.argsort(_y))
            return round(float(np.corrcoef(_rx, _ry)[0, 1]), 3)
        out["audit_corr"] = {
            "psd": True,
            "pairs": {pr: {"target": corr_pairs[pr],
                           "realised_rank": _spearman(P[pr.split(",")[0].strip()].astype(float),
                                                      P[pr.split(",")[1].strip()].astype(float))}
                      for pr in corr_pairs},
            "marginal_q": {nm: [round(float(np.percentile(P[nm].astype(float), _q)), 4)
                                for _q in (10, 50, 90)] for nm in CORR_VARS},
        }
    # curvature diagnostic (consumed by check_century.py --alphasub-audit). The realised
    # marginal is reported rather than the configured ceiling so the audit can see whether
    # the rescale actually reached the prior, and the mean-vs-midpoint check confirms the
    # map stayed uniform rather than piling draws at one end. p10/p50/p90 come from the same
    # array the copula reorders, so a reordering that damaged the marginal would show here.
    _al = P["alpha"].astype(float)
    _lo_al, _hi_al = (1.0, ALPHA_MAX if V2_ALPHASUB else 1.9)
    # timing diagnostic (consumed by check_century.py --doc-figures for section 6.8). The two
    # rank correlations are the evidence that the growth rate and the curvature exponent push
    # the crossing in opposite directions, which is why their copula coupling is negative.
    # Emitted so that argument is pinned to the engine rather than to a number typed once into
    # the document. Run with CENTURY_CORR_JSON=identity to read them uncoupled.
    _mx = agi_year > 0
    def _spear(_x, _y):
        _rx = np.argsort(np.argsort(_x)); _ry = np.argsort(np.argsort(_y))
        return round(float(np.corrcoef(_rx, _ry)[0, 1]), 3)
    out["audit_timing"] = {
        "spearman_k_vs_crossing_year": _spear(P["k"][_mx].astype(float), agi_year[_mx].astype(float)) if _mx.any() else None,
        "spearman_alpha_vs_crossing_year": _spear(P["alpha"][_mx].astype(float), agi_year[_mx].astype(float)) if _mx.any() else None,
        "spearman_alpha_vs_final_capability": _spear(P["alpha"][_mx].astype(float), C[_mx]) if _mx.any() else None,
        "agi_p10": int(np.percentile(agi_year[_mx], 10)) if _mx.any() else None,
        "agi_p50": int(np.percentile(agi_year[_mx], 50)) if _mx.any() else None,
        "agi_p90": int(np.percentile(agi_year[_mx], 90)) if _mx.any() else None,
        # p90 - p10, the width the coupling sign controls. Emitted rather than derived in the
        # document so the spread column of section 6.8 is pinned like every other cell.
        "agi_spread_yr": int(np.percentile(agi_year[_mx], 90) - np.percentile(agi_year[_mx], 10)) if _mx.any() else None,
    }
    out["audit_alpha"] = {
        "alphasub": bool(V2_ALPHASUB),
        "alpha_max_configured": round(float(ALPHA_MAX), 4),
        "observed_min": round(float(_al.min()), 4),
        "observed_max": round(float(_al.max()), 4),
        "mean": round(float(_al.mean()), 4),
        "expected_uniform_mean": round((_lo_al + _hi_al) / 2.0, 4),
        "q10_50_90": [round(float(np.percentile(_al, _q)), 4) for _q in (10, 50, 90)],
    }
    # plateau diagnostic (consumed by check_century.py --platdrag-audit). The overshoot is
    # the quantity the correction exists to control: how far past its own ceiling a stalled
    # world's capability gets before growth stops. Reported for stalled and unstalled worlds
    # separately so the audit can confirm the correction touched only the first group, and
    # the crossing years confirm a stall now costs decades rather than a year.
    # capability-assist diagnostic (consumed by check_century.py --capassist-audit). The
    # realised multiplier is the quantity the correction adds: how much faster capability
    # research runs because capability is already deployed. Reported next to the readiness
    # assist it mirrors, so the audit can show the two sides are no longer one-directional.
    _ca = P["cap_assist"].astype(float)
    out["audit_capassist"] = {
        "capassist": bool(V2_CAPASSIST),
        "capassist_max": round(float(CAPASSIST_MAX), 4),
        "coef_mean": round(float(_ca.mean()), 4),
        "coef_max": round(float(_ca.max()), 4),
        "readiness_assist_ceiling": 0.65,
        "growth_multiplier_at_threshold_mean": round(float((1.0 + _ca * P["threshold"]).mean()), 4),
    }
    _pl = P["plateau"].astype(bool)
    def _ovr(_m):
        return round(float(np.percentile(C[_m] / P["ceiling"][_m], 90)), 4) if _m.any() else None
    def _med_cross(_m):
        _c = _m & (agi_year > 0)
        return int(np.median(agi_year[_c])) if _c.any() else None
    out["audit_plateau"] = {
        "platdrag": bool(V2_PLATDRAG),
        "plateau_exp": round(float(PLATEAU_EXP), 4),
        "plateau_coef": round(float(PLATEAU_COEF), 4),
        "theoretical_cap_x_ceiling": round(float((1.0 / PLATEAU_COEF) ** (1.0 / PLATEAU_EXP)), 4),
        "overshoot_p90_stalled": _ovr(_pl),
        "overshoot_p90_unstalled": _ovr(~_pl),
        "median_crossing_stalled": _med_cross(_pl),
        "median_crossing_unstalled": _med_cross(~_pl),
        "share_stalled_crossing_pct": round(100.0 * float((agi_year[_pl] > 0).mean()), 2) if _pl.any() else None,
        # How far behind the rest of the ensemble a stalled world that still crosses now lands.
        # This is the number that distinguishes a stall from a mild delay, so it is emitted
        # rather than subtracted in the document.
        "stall_lag_years": (_med_cross(_pl) - _med_cross(~_pl))
                           if (_med_cross(_pl) is not None and _med_cross(~_pl) is not None) else None,
    }
    if V2_POLICY:
        # policy diagnostic (consumed by check_century.py --policy-audit): observed bounds of
        # each state-responsive lever (must stay within the declared clip bounds) and the mean
        # realised safety effort in the top vs bottom warning-shot quartile (top must be higher).
        _semean = pol_se_sum / np.maximum(pol_se_cnt, 1)
        _ws = ev["warning_shot"]
        _q1, _q3 = np.percentile(_ws, [25, 75])
        _bot = _ws <= _q1
        _top = _ws >= _q3
        out["audit_policy"] = {
            "se_t_bounds": [round(pol_bounds["se_t"][0], 5), round(pol_bounds["se_t"][1], 5)],
            "race_t_bounds": [round(pol_bounds["race_t"][0], 4), round(pol_bounds["race_t"][1], 4)],
            "resp_t_bounds": [round(pol_bounds["resp_t"][0], 4), round(pol_bounds["resp_t"][1], 4)],
            "safety_effort_top_ws_quartile": round(float(_semean[_top].mean()), 5),
            "safety_effort_bottom_ws_quartile": round(float(_semean[_bot].mean()), 5),
        }
    if V2_ERODE:
        # readiness-erosion diagnostic (consumed by check_century.py --erosion-audit). The mean
        # erode against the mean ai_assist on the same denominator says whether capability
        # growth is net positive or net negative for readiness, which is the whole claim the
        # correction makes. The learn figures say how much damping the warning-shot gate
        # withholds, split at the AGI crossing because that is where the gate binds hardest:
        # a world that has seen no incident by the time it crosses gets no damping at all.
        _ed = max(ero_years, 1)
        _edp = max(ero_pre_years, 1)
        out["audit_erosion"] = {
            "survivor_years": ero_years,
            "survivor_years_pre_agi": ero_pre_years,
            "mean_erode_per_yr": round(ero_erode_sum / _ed, 6),
            "mean_ai_assist_per_yr": round(ero_assist_sum / _ed, 6),
            "share_erode_exceeds_assist": round(ero_net_losing / _ed, 4),
            "n_years_readiness_fell": ero_dR_neg,
            "share_years_readiness_fell": round(ero_dR_neg / _ed, 4),
            "min_realised_R": (round(ero_R_min, 5) if ero_years else None),
            "share_R_at_floor": round(ero_R_floor / _ed, 6),
            "mean_learn": round(ero_learn_sum / _ed, 5),
            "share_learn_zero": round(ero_learn_zero / _ed, 4),
            "mean_learn_pre_agi": round(ero_pre_learn_sum / _edp, 5),
            "share_learn_zero_pre_agi": round(ero_pre_learn_zero / _edp, 4),
        }
    if V2_XHAZ or V2_REBUILD:
        # hazard-completeness diagnostic (consumed by check_century.py --hazard-audit): the
        # outcome shares (including the new channels) sum to 100%; the unknown-unknowns share
        # tracks its sampled rate; and recovered worlds carry the documented state penalty
        # (lower mean capability than the never-collapsed survivors).
        out["audit_hazard"] = {
            "outcome_sum_pct": round(float(sum(v for v in out["outcomes"].values() if v is not None)), 2),
            "unknown_catastrophe_pct": out["outcomes"].get("unknown_catastrophe"),
            "xhaz_rate_mean_per_yr": round(float(P["xhaz_rate"].mean()), 5) if V2_XHAZ else None,
            "recovered_pct": out["outcomes"].get("recovered"),
            "n_recovered": int(recovered.sum()) if V2_REBUILD else None,
            # penalty applied at re-entry, measured directly (post/pre): G should be ~0.6, C ~0.75
            "reentry_G_penalty_ratio": (round(reb_postG / reb_preG, 3) if V2_REBUILD and reb_preG > 0 else None),
            "reentry_C_penalty_ratio": (round(reb_postC / reb_preC, 3) if V2_REBUILD and reb_preC > 0 else None),
        }
print(json.dumps(out, indent=2, allow_nan=False))
