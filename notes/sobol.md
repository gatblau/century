# Sobol sensitivity (Phase 8)

Variance-based first-order (S_i) and total-order (S_Ti) Sobol indices for P(good) and P(disempowerment), hand-rolled Saltelli (NumPy only), engine under CENTURY_V2, Saltelli base N=8192. Unlike the marginal quartile swings in century_sim.py, these capture interactions (S_Ti > S_i). The estimator is validated against the analytic Ishigami indices (`--self-test`).

## P(good)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.087 | 0.269 | +0.183 |
| redist_will | 0.060 | 0.184 | +0.124 |
| concentration0 | 0.042 | 0.168 | +0.126 |
| safety_eff | 0.022 | 0.120 | +0.098 |
| respond | 0.019 | 0.111 | +0.092 |
| race | 0.023 | 0.106 | +0.083 |
| alpha | 0.007 | 0.103 | +0.096 |
| climate_eff | 0.020 | 0.077 | +0.057 |
| threshold | 0.010 | 0.071 | +0.062 |
| erode_mag | 0.009 | 0.059 | +0.050 |
| assist | 0.010 | 0.058 | +0.048 |
| R0 | 0.001 | 0.039 | +0.039 |
| bio_defense | 0.001 | 0.033 | +0.033 |
| fragility | 0.001 | 0.027 | +0.026 |

## P(disempowerment)

| parameter | S_i | S_Ti | interaction (S_Ti - S_i) |
|---|---:|---:|---:|
| k | 0.120 | 0.344 | +0.224 |
| safety_eff | 0.041 | 0.154 | +0.113 |
| concentration0 | 0.037 | 0.139 | +0.102 |
| alpha | -0.002 | 0.134 | +0.135 |
| race | 0.009 | 0.111 | +0.102 |
| erode_mag | 0.005 | 0.088 | +0.082 |
| assist | 0.007 | 0.082 | +0.075 |
| threshold | 0.004 | 0.082 | +0.078 |
| redist_will | 0.004 | 0.057 | +0.053 |
| R0 | -0.001 | 0.053 | +0.054 |
| respond | -0.008 | 0.038 | +0.046 |
| fragility | 0.000 | 0.005 | +0.005 |
| bio_defense | -0.001 | 0.002 | +0.002 |
| climate_eff | 0.000 | 0.000 | +0.000 |

**Interaction finding.** For `safety_eff` on P(good), S_i=0.022 and S_Ti=0.120. The total-order index exceeds the first-order index, confirming that safety effort acts partly through interactions (e.g. safety-effort-given-race) that the marginal quartile swings cannot see.
