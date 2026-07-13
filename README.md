# Century Superforecaster

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A world model you can run on your laptop. It plays out the next hundred years, 2026 to 2126, across 800,000 simulated worlds, and reports how often the century ends well, how often it ends badly, and which decisions change those odds.

One full run takes about a minute. You need Python 3 and NumPy. That is all.

```bash
pip install numpy
python3 century_sim.py 800000
```

## Why this exists

Arguments about the future usually stay stuck at the level of opinion. One person says AI risk dominates everything, another says pandemics, another says none of it matters because institutions will adapt. There is rarely a way to check.

This project gives you a way to check. The model contains the major forces people argue about: AI progress, nuclear war, engineered and natural pandemics, climate, demographics, the economy, and how governments react when things go wrong. Every uncertain quantity is sampled from ranges anchored to published expert estimates, so each simulated world is a coherent "what if" drawn from what we actually know. Run enough worlds and you get the full spread of possible centuries.

The purpose is policy. If a choice changes the odds of a good century and we can make it today, that is worth knowing. If a choice feels important but barely moves the numbers, that is worth knowing too. Anyone can run the model, question its assumptions, change them, and see what happens.

## What the model currently says

Two numbers matter, side by side: what the century could be, and where it is heading. The first column treats every good policy choice as open. The second weighs each choice by an honest, written-down estimate of how likely it is to actually happen.

| How the century ends | If every choice stays open | On its expected course |
|---|---:|---:|
| Broadly good (abundance, shared prosperity, or steady flourishing) | 44.1 % | 39.5 % |
| Mixed (rocky transitions, recoveries, muddling through) | 14.0 % | 15.1 % |
| Irreversibly bad (disempowerment, lock-in, collapse, extinction) | 41.9 % | 45.4 % |

The three rows cover every world, so each column adds up to 100 %. Mixed worlds are the ones where the century ends without a verdict: still shaken by the arrival of AGI, rebuilding after a collapse, or muddling along under weak institutions with no AGI at all. Nothing irreversible has happened to them, but nothing is settled either. Overall: the century could go either way, and it is currently heading slightly the wrong way. Both columns come from the same 800,000 worlds. The estimates behind the second column are judgements, not survey data. They live in `lever-anchors.json` with their reasoning written next to them, anyone can edit them and rerun, and [`realistic-bet.md`](docs/realistic-bet.md) walks through them choice by choice.

The interesting part is what changes the outcome. Making only the social and political choices we can realistically reach (institutional readiness, safety investment, cooperation, redistribution), while leaving the pace of technology untouched, raises the good share from 44 % to 71 %:

| Configuration | P(good) | P(bad) |
|---|---:|---:|
| Do nothing | 44.1 % | 41.9 % |
| Make the feasible socio-political choices | 71.0 % | 20.7 % |
| Push those choices to their extremes | 78.1 % | 16.1 % |
| Feasible choices plus compute governance | 76.4 % | 14.9 % |

The last row is the second row plus limits on large computing runs. That combination trims the bad tail further, but in the model it also delays AGI by about six years.

Preparation is what flips the outcome. Technology can keep racing ahead and the good share still climbs to 71 % once those choices are made. The distance between the expected course (39.5 %) and the prepared world (71 %) is the point of the whole project: more than 30 points of century, blocked by nothing except how unlikely the choices currently are. The two main documents in this repo, [`future.md`](docs/future.md) (the full report) and [`strategy.md`](docs/strategy.md) (what to do about it), walk through this in detail.

## Try it yourself

The default run prints a JSON report: the outcome distribution, when AGI arrives across worlds, how often wars and pandemics happen, population and climate endpoints, and a ranking of which parameters matter most.

```bash
python3 century_sim.py 20000          # quick run, ~2 seconds, slightly noisier
python3 century_sim.py 800000         # full run, ~50 seconds
```

Every assumption is a parameter you can override. This is where it gets fun. Build a world and see how it ends.

## Five worlds

The model has no built-in scenarios. A scenario is something you build, by pinning parameters and running it. Here are five, each a single command, each at the full 800,000 worlds so the numbers line up with every other table in this file.

```bash
# 1. the prepared acceleration: fast technology, institutions that keep up
CENTURY_OVERRIDES='{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75}' python3 century_sim.py 800000

# 2. the race to fragility: hard racing, weak response, safety as a rounding error
CENTURY_OVERRIDES='{"race":0.95,"respond":0.25,"safety_eff":0.006}' python3 century_sim.py 800000

# 3. the concentrated world: nobody races, nobody cuts a corner, the gains just never move
CENTURY_OVERRIDES='{"concentration0":0.75,"redist_will":0.2}' python3 century_sim.py 800000

# 4. the undefended world: biodefence near its floor, everything else as normal
CENTURY_OVERRIDES='{"bio_defense":0.2}' python3 century_sim.py 800000

# 5. the plateau: the current AI paradigm stalls
CENTURY_OVERRIDES='{"plateau":true}' python3 century_sim.py 800000
```

| World | Good | Irreversibly bad | Extinction | Shared abundance |
|---|---:|---:|---:|---:|
| Baseline (no overrides) | 44.1 % | 41.9 % | 9.7 % | 19.4 % |
| 1. Prepared acceleration | 71.0 % | 20.7 % | 5.3 % | 65.4 % |
| 2. Race to fragility | 25.0 % | 61.7 % | 14.4 % | 10.4 % |
| 3. Concentrated | 20.4 % | 51.3 % | 9.2 % | 0.0 % |
| 4. Undefended | 41.1 % | 42.4 % | 10.0 % | 18.2 % |
| 5. Plateau | 62.7 % | 11.3 % | 2.1 % | 19.7 % |

World 1 is the same configuration as the "make the feasible socio-political choices" row in the table further up, and it lands on the same 71.0 % from a standing start, which is the cheapest reproducibility check in the repo.

Two things in that table are worth staring at.

The worst world is number 3, and it touches no technical parameter at all. Nobody races and nobody cuts a safety corner. Capability and wealth simply start out concentrated, and the political will to share them is pinned to its floor. That costs 24 points of good century, more than the racing world does. Read the extinction column and it looks harmless: 9.2 %, barely off the baseline. Read the last column and shared abundance is 0.0 %, which is a wall rather than bad luck. The model only classes a world as shared abundance once concentration falls below 0.62, and concentration only falls when there is political will to share. Take that away and the best ending has no path from here, in any of the 800,000 worlds.

World 4 hurts far less than expected. Letting biodefence collapse raises engineered pandemics by 44 % (0.70 to 1.01 events per world) and still costs only 3 points of good century. In this model pandemics are a real hazard and a weak determinant of the outcome. What decides the century is what happens to capability and to power.

Compare the `outcomes` blocks of any two runs. The difference is what that choice buys.

## The dials

| Dial | What it means | Sampled range |
|---|---|---|
| `race` | how hard nations and labs race each other | 0.25 to 1.0 |
| `respond` | how strongly institutions react to warning shots | 0.15 to 1.0 |
| `safety_eff` | yearly human-paced gain in safety readiness | 0.004 to 0.020 |
| `assist` | how much AI capability can be turned into safety | 0 to 0.65 |
| `redist_will` | political capacity to share the gains | 0.2 to 0.9 |
| `concentration0` | how concentrated wealth and power start out | 0.55 to 0.75 |
| `bio_defense` | biodefence investment against bio-offence diffusion | 0.2 to 0.9 |
| `k` | base speed of capability growth | lognormal around 0.095 |
| `alpha` | curvature of capability growth | 1.0 to 1.9 |
| `plateau` | whether the current AI paradigm stalls | true in 14 % of worlds |

Ranked by how much each one swings the odds of a good century (the gap between its top and bottom quartile), `plateau` tops the list at 21.5 points, but a plateau is weather rather than a choice. Among the things we can actually decide, `redist_will` comes first at 21.3, just ahead of `respond` at 21.1 and well ahead of `race` at 16.1. The strongest choice available to us is whether we are politically capable of sharing the proceeds, which is not where most AI policy is currently looking.

Section 9 of `future.md` and section 6 of `strategy.md` list every documented run, ready to copy and paste.

## How to read the report

Every run prints one JSON object. Most of it is there for deep dives, but five blocks carry the headline story. Here is a trimmed run so you can find your way around it:

```json
{
  "N": 800000,
  "outcomes": {
    "aligned_abundance": 19.4,
    "oligarchic_prosperity": 21.6,
    "turbulent_transition": 9.0,
    "constrained_flourishing": 3.0,
    "muddling_degraded": 2.0,
    "disempowerment": 27.4,
    "lockin": 1.8,
    "collapse": 0.5,
    "extinction": 9.7,
    "unknown_catastrophe": 2.5,
    "recovered": 3.0
  },
  "aggregates": {
    "good(broadly acceptable)": 44.1,
    "irreversible_bad": 41.9
  },
  "agi": { "median_year": 2036, "p10_year": 2031, "p90_year": 2049 },
  "events_per_world": { "nuclear_war": 0.56, "eng_pandemic": 0.71 },
  "sensitivity_P_good": {
    "respond": { "P(good)|bottom_quartile": 34.1, "P(good)|top_quartile": 54.9, "swing": 20.7 }
  }
}
```

**`outcomes`** is the heart of it: the eleven ways a century can end, each with the share of worlds that reached it. They add up to 100. The headline table at the top of this file folds them into three rows:

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

**`aggregates`** is the same result summed up: the good share and the irreversibly bad share, the two figures the rest of the project keeps coming back to.

**`agi`** tells you when the machine arrives. `median_year` is the middle world, and `p10_year` and `p90_year` are the early and late edges. Half of all worlds cross the AGI threshold between them.

**`events_per_world`** counts how often each shock lands in an average world: nuclear war, engineered and natural pandemics, warning shots, and regional wars. The two `p_at_least_one_*` lines beside it turn the pandemic and nuclear counts into the plain "did it happen at all" odds.

**`sensitivity_P_good`** ranks the dials. For each one it shows the good share in the worlds where the dial sits low against the worlds where it sits high, and the `swing` between them. A positive swing means turning the dial up helps, and a negative swing means it hurts. Read this as a rough guide only: the note in the same block explains why the Sobol indices from `sobol_century.py` are the honest ranking.

The remaining blocks (`gap_at_agi`, `structure_conditional`, `conditionals`, and the four `*_profile` blocks) are for closer reading. They record the state of the world at the moment each kind of ending was sealed. Section 3 of [`future.md`](docs/future.md) walks through them.

## Where the numbers come from

The model does not invent its probabilities. Sampling ranges are anchored to published sources: expert and superforecaster surveys on AI timelines, the Existential Risk Persuasion Tournament estimates of extinction risk, published estimates of nuclear war risk, historical pandemic frequency, UN population projections, and IPCC warming scenarios. The anchors live in `anchors.json` with their sources named, and `calibrate_century.py` reweights the ensemble toward them. It also reports how far the model already sits inside each published band before any reweighting, so you can see which parts of the model agree with the outside view and which are in tension.

One file is different. `lever-anchors.json` holds the project's own estimates of how likely each policy choice is to happen. No published survey covers those questions, so the estimates are labelled as judgements, each with its reasoning written next to it, and they are meant to be edited.

If you disagree with an anchor, change it and rerun. That disagreement, made concrete, is exactly the kind of conversation this project is for.

## How you know it is not broken

The repo checks itself. `check_century.py` is the gate:

```bash
python3 check_century.py                     # regression against stored golden outputs
python3 check_century.py --doc-figures      # every table in the documents vs fresh engine runs
python3 check_century.py --negative-control # plants a bug on purpose; the checker must catch it
```

Every figure quoted in `future.md` and in the strategy ladder of `strategy.md` is machine-checked against the engine, so the documents cannot silently drift from the code. There are further audits for the hazard accounting, the calibration, the policy feedbacks, and the correlation structure; run `python3 check_century.py --help` to see them all. The Sobol sensitivity estimator in `sobol_century.py` validates itself against a known analytic case before it touches the engine.

Runs are seeded, so the same command gives the same numbers on your machine as it did on ours.

## What is in the repo

| File | What it is |
|---|---|
| [`century_sim.py`](century_sim.py) | the engine: 800,000 worlds, year by year, NumPy only |
| [`docs/how-it-works.md`](docs/how-it-works.md) | a plain-language explainer: how the model works and what it is for |
| [`docs/future.md`](docs/future.md) | the full report: results, scenarios, sensitivity, caveats |
| [`docs/strategy.md`](docs/strategy.md) | the policy readout: which choices matter and what they buy |
| [`docs/levers-and-preparedness.md`](docs/levers-and-preparedness.md) | the plain-language companion: each realistic choice explained, and the foundations of a readiness system |
| [`docs/realistic-bet.md`](docs/realistic-bet.md) | the third view: how likely the good choices are, and what doubting them costs |
| [`docs/sensitivity-charts.md`](docs/sensitivity-charts.md) | how to read the sensitivity charts, in plain terms, lessons up front |
| [`check_century.py`](check_century.py) | the self-checking gate described above |
| [`calibrate_century.py`](calibrate_century.py) | reweights the ensemble toward the published anchors |
| [`sobol_century.py`](sobol_century.py) | which parameters drive the outcome, interactions included |
| [`plot_sensitivity.py`](plot_sensitivity.py) | builds the three sensitivity charts from the engine |
| [`Makefile`](Makefile) | shortcuts to run the model and build the charts; `make help` lists them |
| [`anchors.json`](anchors.json) | the external estimates the model is anchored to, with sources |
| [`lever-anchors.json`](lever-anchors.json) | how likely each policy choice is to happen (the third view), with the reasoning written down |
| [`golden/`](golden) | stored reference outputs the regression gate compares against |
| [`notes/`](notes) | generated working notes and the sensitivity charts (PNGs) |

## Honest limits

This is a model, and a hundred years is a long time. The outcome categories are simplifications, the parameter ranges are judgement calls anchored to today's estimates, and the model cannot contain surprises nobody has imagined. Section 8 of `future.md` spells out the caveats properly.

Read the numbers as a disciplined way to reason about which choices matter, under assumptions you can inspect and change. You can see which choices move the century from bad to good, and you can test them yourself today.
