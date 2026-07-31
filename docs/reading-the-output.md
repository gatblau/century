# Reading a run

Every run of `century_sim.py` prints one JSON object. Most of it is there for deep dives. Five blocks carry the headline story, and this page walks through them.

Here is a trimmed run, so you can find your way around a real one.

```json
{
  "N": 800000,
  "outcomes": {
    "aligned_abundance": 17.35,
    "oligarchic_prosperity": 17.48,
    "turbulent_transition": 8.76,
    "constrained_flourishing": 4.22,
    "muddling_degraded": 4.94,
    "disempowerment": 30.06,
    "lockin": 1.30,
    "collapse": 0.45,
    "extinction": 10.43,
    "unknown_catastrophe": 2.39,
    "recovered": 2.59
  },
  "aggregates": {
    "good(broadly acceptable)": 39.1,
    "irreversible_bad": 44.6
  },
  "agi": { "median_year": 2038, "p10_year": 2030, "p90_year": 2060 },
  "events_per_world": { "nuclear_war": 0.507, "eng_pandemic": 0.619 },
  "sensitivity_P_good": {
    "respond": { "P(good)|bottom_quartile": 28.0, "P(good)|top_quartile": 49.1, "swing": 21.1 }
  }
}
```

## outcomes

The heart of it. Eleven ways a century can end, each with the share of worlds that reached it. They add up to 100.

The headline table in the README folds these eleven into three rows.

| Outcome key | In one line | Headline row |
|---|---|---|
| `aligned_abundance` | AGI stays under control and its gains reach most people | Broadly good |
| `oligarchic_prosperity` | AGI is controlled but the gains pool at the top | Broadly good |
| `constrained_flourishing` | No AGI, and the world governs itself well | Broadly good |
| `turbulent_transition` | AGI arrived but nothing settled by 2126 | Mixed |
| `muddling_degraded` | No AGI, and weak politics | Mixed |
| `recovered` | Collapsed, then rebuilt with scars | Mixed |
| `disempowerment` | Humans survive but permanently lose control | Irreversibly bad |
| `lockin` | A human elite freezes its own rule in place | Irreversibly bad |
| `collapse` | Industrial civilisation broke down and has not rebuilt | Irreversibly bad |
| `extinction` | No meaningful human future | Irreversibly bad |
| `unknown_catastrophe` | A terminal event the model cannot name | Irreversibly bad |

## aggregates

The same result summed up: the good share and the irreversibly bad share. These are the two figures the rest of the project keeps coming back to.

## agi

When the machine arrives. `median_year` is the middle world. `p10_year` and `p90_year` are the early and late edges, and half of all worlds cross the AGI threshold between them.

## events_per_world

How often each shock lands in an average world: nuclear war, engineered and natural pandemics, warning shots, and regional wars. The two `p_at_least_one_*` lines beside it turn the pandemic and nuclear counts into the plain "did it happen at all" odds.

## sensitivity_P_good

A ranking of the dials. For each one it shows the good share in the worlds where the dial sits low, the good share where it sits high, and the `swing` between them. A positive swing means turning the dial up helps, and a negative swing means it hurts.

Read this as a rough guide only. The note in the same block explains why the Sobol indices from `sobol_century.py` (a fuller method, which also measures how the dials interact with each other) are the honest ranking.

## The rest

The remaining blocks are for closer reading: `gap_at_agi`, `structure_conditional`, `conditionals`, and the four `*_profile` blocks. They record the state of the world at the moment each kind of ending was sealed. Section 3 of [`future.md`](future.md) walks through them.

## Comparing two runs

Run the model twice with different settings and compare the `outcomes` blocks. The difference between them is what that choice buys.
