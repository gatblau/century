# Sobol sensitivity (Phase 8)

Variance-based first-order (S_i) and total-order (S_Ti) Sobol indices for P(good) and P(disempowerment), hand-rolled Saltelli (NumPy only), engine under CENTURY_V2, Saltelli base N=8192. Unlike the marginal quartile swings in century_sim.py, these capture interactions (S_Ti > S_i). The estimator is validated against the analytic Ishigami indices (`--self-test`).

## P(good)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.107 | 0.292 | +0.185 |
| redist_will | 0.059 | 0.174 | +0.116 |
| concentration0 | 0.022 | 0.149 | +0.127 |
| safety_eff | 0.028 | 0.139 | +0.111 |
| race | 0.027 | 0.113 | +0.086 |
| alpha | 0.001 | 0.110 | +0.109 |
| respond | 0.030 | 0.107 | +0.076 |
| threshold | 0.007 | 0.083 | +0.077 |
| erode_mag | 0.017 | 0.073 | +0.056 |
| assist | 0.013 | 0.064 | +0.051 |
| climate_eff | 0.012 | 0.061 | +0.049 |
| R0 | 0.008 | 0.045 | +0.037 |
| bio_defense | -0.002 | 0.033 | +0.035 |
| fragility | 0.004 | 0.019 | +0.015 |

## P(disempowerment)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.134 | 0.378 | +0.244 |
| safety_eff | 0.036 | 0.185 | +0.149 |
| alpha | 0.001 | 0.144 | +0.143 |
| concentration0 | 0.038 | 0.141 | +0.102 |
| race | 0.009 | 0.120 | +0.111 |
| erode_mag | 0.006 | 0.106 | +0.100 |
| threshold | 0.002 | 0.098 | +0.096 |
| assist | 0.010 | 0.090 | +0.080 |
| R0 | -0.006 | 0.061 | +0.067 |
| redist_will | 0.007 | 0.058 | +0.052 |
| respond | -0.007 | 0.040 | +0.047 |
| fragility | 0.001 | 0.005 | +0.005 |
| bio_defense | 0.000 | 0.003 | +0.003 |
| climate_eff | 0.000 | 0.000 | +0.000 |

**Interaction finding.** For `safety_eff` on P(good), S_i=0.028 and S_Ti=0.139. The total-order index exceeds the first-order index, confirming that safety effort acts partly through interactions (e.g. safety-effort-given-race) that the marginal quartile swings cannot see.
