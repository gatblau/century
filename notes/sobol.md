# Sobol sensitivity (Phase 8)

Variance-based first-order (S_i) and total-order (S_Ti) Sobol indices for P(good) and P(disempowerment), hand-rolled Saltelli (NumPy only), engine under CENTURY_V2, Saltelli base N=8192. Unlike the marginal quartile swings in century_sim.py, these capture interactions (S_Ti > S_i). The estimator is validated against the analytic Ishigami indices (`--self-test`).

## P(good)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.113 | 0.290 | +0.177 |
| redist_will | 0.056 | 0.181 | +0.125 |
| concentration0 | 0.028 | 0.157 | +0.128 |
| safety_eff | 0.026 | 0.135 | +0.109 |
| respond | 0.023 | 0.107 | +0.084 |
| race | 0.032 | 0.107 | +0.075 |
| alpha | 0.008 | 0.107 | +0.099 |
| threshold | 0.013 | 0.080 | +0.067 |
| climate_eff | 0.020 | 0.073 | +0.053 |
| erode_mag | 0.015 | 0.070 | +0.055 |
| assist | 0.012 | 0.060 | +0.048 |
| R0 | 0.006 | 0.043 | +0.037 |
| bio_defense | -0.003 | 0.031 | +0.034 |
| fragility | 0.006 | 0.021 | +0.016 |

## P(disempowerment)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.130 | 0.371 | +0.241 |
| safety_eff | 0.036 | 0.181 | +0.146 |
| alpha | -0.001 | 0.139 | +0.140 |
| concentration0 | 0.040 | 0.139 | +0.099 |
| race | 0.008 | 0.118 | +0.110 |
| erode_mag | 0.009 | 0.102 | +0.094 |
| threshold | 0.002 | 0.094 | +0.093 |
| assist | 0.012 | 0.087 | +0.075 |
| R0 | -0.006 | 0.060 | +0.066 |
| redist_will | 0.007 | 0.058 | +0.051 |
| respond | -0.007 | 0.039 | +0.046 |
| fragility | 0.001 | 0.005 | +0.005 |
| bio_defense | 0.000 | 0.003 | +0.003 |
| climate_eff | 0.000 | 0.000 | +0.000 |

**Interaction finding.** For `safety_eff` on P(good), S_i=0.026 and S_Ti=0.135. The total-order index exceeds the first-order index, confirming that safety effort acts partly through interactions (e.g. safety-effort-given-race) that the marginal quartile swings cannot see.
