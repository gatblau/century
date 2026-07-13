# Sobol sensitivity (Phase 8)

Variance-based first-order (S_i) and total-order (S_Ti) Sobol indices for P(good) and P(disempowerment), hand-rolled Saltelli (NumPy only), engine under CENTURY_V2, Saltelli base N=8192. Unlike the marginal quartile swings in century_sim.py, these capture interactions (S_Ti > S_i). The estimator is validated against the analytic Ishigami indices (`--self-test`).

## P(good)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.101 | 0.261 | +0.161 |
| redist_will | 0.055 | 0.184 | +0.130 |
| concentration0 | 0.023 | 0.150 | +0.127 |
| safety_eff | 0.022 | 0.123 | +0.101 |
| race | 0.024 | 0.109 | +0.085 |
| respond | 0.016 | 0.108 | +0.093 |
| alpha | -0.000 | 0.096 | +0.096 |
| climate_eff | 0.021 | 0.079 | +0.058 |
| threshold | 0.012 | 0.079 | +0.066 |
| assist | 0.003 | 0.066 | +0.063 |
| R0 | 0.001 | 0.044 | +0.043 |
| bio_defense | 0.007 | 0.040 | +0.032 |
| fragility | -0.001 | 0.026 | +0.028 |

## P(disempowerment)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.147 | 0.367 | +0.220 |
| safety_eff | 0.050 | 0.199 | +0.149 |
| concentration0 | 0.021 | 0.136 | +0.115 |
| alpha | 0.017 | 0.129 | +0.112 |
| assist | 0.019 | 0.112 | +0.093 |
| race | 0.010 | 0.112 | +0.102 |
| threshold | 0.010 | 0.106 | +0.096 |
| R0 | 0.004 | 0.073 | +0.070 |
| redist_will | 0.008 | 0.048 | +0.040 |
| respond | -0.002 | 0.027 | +0.029 |
| fragility | 0.000 | 0.004 | +0.004 |
| bio_defense | 0.000 | 0.001 | +0.001 |
| climate_eff | 0.000 | 0.000 | +0.000 |

**Interaction finding.** For `safety_eff` on P(good), S_i=0.022 and S_Ti=0.123. The total-order index exceeds the first-order index, confirming that safety effort acts partly through interactions (e.g. safety-effort-given-race) that the marginal quartile swings cannot see.
