# Century Superforecaster

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A world model you can run on your laptop.

It plays the next hundred years out 800,000 times. Each run is one possible version of 2026 to 2126: AI improves at some pace, wars and pandemics either happen or do not, governments either cope or do not. Count how all 800,000 versions ended and you have a map of what could happen, and how often.

```bash
pip install numpy
python3 century_sim.py 800000     # about a minute
```

If you want the plain-language version first, [`how-it-works.md`](docs/how-it-works.md) explains the whole thing in about a thousand words and assumes nothing.

## What it says

Two questions, side by side: what the century could be, and where it is actually heading.

| How the century ends | If every choice stays open | On its expected course |
|---|---:|---:|
| Broadly good (abundance, shared prosperity, or steady flourishing) | 37.3 % | 32.8 % |
| Mixed (rocky transitions, recoveries, muddling through) | 15.4 % | 16.4 % |
| Irreversibly bad (disempowerment, lock-in, collapse, extinction) | 47.3 % | 50.8 % |

The first column treats every good decision as available. The second weighs each decision by how likely it is to actually be taken. Both columns come from the same 800,000 worlds, and the rows cover every world, so each column adds up to 100 %.

Mixed worlds are the ones that end without a verdict. Still shaken by the arrival of AGI, rebuilding after a collapse, or muddling along under weak institutions with no AGI at all. Nothing irreversible has happened to them, but nothing is settled either.

So the century could go either way, and it is currently heading the wrong way.

## What changes the outcome

Preparation does. Take only the social and political choices we could realistically reach: institutions ready to react, real money in safety, countries cooperating, gains shared. Do that and the good share rises from 37 % to 64 %. Technology keeps racing ahead in that world. Nothing about the pace of AI changes.

Push those same choices to their extremes and it reaches 73.2 %. Add limits on large computing runs and the bad share falls furthest, to 18.2 %, for a good share of 71.3 %. In the model that last combination also delays AGI by about nine years.

The distance between where we are heading (32.8 %) and a prepared world (63.8 %) is the point of this whole project. More than 30 points of century, blocked by nothing except how unlikely those choices currently are.

Two things are worth knowing about those numbers. First, the estimates behind the second column of the table are judgements rather than survey data. They live in `lever-anchors.json` with the reasoning written next to each one, and [`realistic-bet.md`](docs/realistic-bet.md) walks through them one by one.

Second, the model assumes by default that safety testing goes stale as AI grows more capable. Turn that assumption off and the same worlds give 41.9 % good against 40.9 % bad. Nothing published settles how fast the staleness really sets in, so both readings stand. Every other figure on this page uses the default.

## Why this exists

Arguments about the future usually stop at opinion. One person says AI risk dominates everything, another says pandemics, another says none of it matters because institutions will adapt. There is rarely a way to check.

This is a way to check. The model holds the major forces people argue about: AI progress, nuclear war, engineered and natural pandemics, climate, demographics, the economy, and how governments react when things go wrong. Every uncertain quantity is drawn from a range anchored to published expert estimates, so each simulated world is a coherent "what if". Run enough of them and you see the whole spread.

The purpose is practical. If a decision changes the odds of a good century and we can take it today, that is worth knowing. If a decision feels important but barely changes anything, that is worth knowing too. Anyone can run the model, question its assumptions, change them, and see what happens.

## Five worlds

The model ships with no scenarios. A scenario is something you build: pin a few settings, then run it. Here are five, one command each, all at the full 800,000 worlds so the numbers line up with the rest of this page.

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
| Baseline (no overrides) | 37.3 % | 47.3 % | 11.1 % | 16.2 % |
| 1. Prepared acceleration | 63.8 % | 26.2 % | 6.6 % | 56.3 % |
| 2. Race to fragility | 20.4 % | 65.2 % | 15.4 % | 8.4 % |
| 3. Concentrated | 15.0 % | 57.0 % | 10.6 % | 0.0 % |
| 4. Undefended | 34.8 % | 47.7 % | 11.2 % | 15.3 % |
| 5. Plateau | 51.8 % | 6.4 % | 0.8 % | 11.1 % |

World 1 is the prepared world from the section above, reached here from a standing start. It is the cheapest reproducibility check in the repo.

Two rows are worth staring at.

The worst world is number 3, and it touches no technical setting at all. Nobody races and nobody cuts a safety corner. Capability and wealth simply start out concentrated, and the will to share them is pinned to its floor. That costs 22 points of good century, more than hard racing does. Read the extinction column and it looks harmless, barely off the baseline. Read the last column and shared abundance is 0.0 %, which is a wall rather than bad luck. The model only calls a world shared abundance once concentration falls below 0.62, and concentration only falls when there is political will to share. Take that will away and the best ending has no path from here, in any of the 800,000 worlds.

World 4 hurts far less than expected. Letting biodefence collapse raises engineered pandemics by 41 %, from 0.61 to 0.86 events per world, and still costs under 3 points of good century. In this model pandemics do real damage along the way and rarely decide how the story ends. What decides the century is what happens to capability and to power.

## The dials

Every assumption is a setting you can override. These are the ones that matter most.

| Dial | What it means | Range it is drawn from |
|---|---|---|
| `race` | how hard nations and labs race each other | 0.25 to 1.0 |
| `respond` | how strongly institutions react to warning shots | 0.15 to 1.0 |
| `safety_eff` | yearly gain in safety readiness from human work | 0.004 to 0.020 |
| `assist` | how much AI capability can be turned to safety | 0 to 0.65 |
| `redist_will` | political capacity to share the gains | 0.2 to 0.9 |
| `concentration0` | how concentrated wealth and power start out | 0.55 to 0.75 |
| `bio_defense` | biodefence investment against bio-offence diffusion | 0.2 to 0.9 |
| `k` | base speed of capability growth | typically near 0.095 |
| `alpha` | curvature of capability growth (higher is slower below the threshold) | 1.0 to 2.4 |
| `plateau` | whether the current AI paradigm stalls | true in 14 % of worlds |
| `erode_mag` | how fast new capability makes existing safety work stale | 0 to 0.30 |

Rank the dials by how much each one swings the odds of a good century and the top two are both choices: `redist_will` at 21.1 points and `respond` at 20.4. A stalled paradigm comes third at 16.5, and the fastest fact of nature, `k`, fourth at −16.0, pulling the other way.

That ordering changed when the plateau was corrected to slow growth rather than only cap it. A working plateau is a weaker lever than a broken one, because a stalled world now grinds on for decades and reaches more mixed endings instead of stopping cleanly in a good one. The strongest choice available to us is whether we are politically capable of sharing the proceeds, which is not where most AI policy is currently looking.

Section 9 of [`future.md`](docs/future.md) and section 6 of [`strategy.md`](docs/strategy.md) list every documented run, ready to copy and paste.

## Reading a run

Every run prints one JSON object. Two blocks carry the story: `outcomes` is the eleven ways a century can end with the share of worlds that reached each, and `aggregates` folds those eleven into the good share and the irreversibly bad share.

Compare the `outcomes` blocks of two runs and the difference is what that choice buys. [`reading-the-output.md`](docs/reading-the-output.md) walks through the rest of the report block by block.

## Where the numbers come from

The model does not invent its probabilities. The ranges it draws from are anchored to published sources: expert and superforecaster surveys on AI timelines, the Existential Risk Persuasion Tournament estimates of extinction risk, published estimates of nuclear war risk, historical pandemic frequency, UN population projections, and IPCC warming scenarios. The anchors live in `anchors.json` with their sources named.

`calibrate_century.py` then tilts the 800,000 worlds towards those published numbers, counting the worlds that agree with them more heavily instead of changing the model. It also reports how far the model already sits inside each published band before any tilting, so you can see which parts agree with the outside view and which are in tension.

One file is different. `lever-anchors.json` holds the project's own estimates of how likely each policy choice is to happen. No published survey covers those questions, so the estimates are labelled as judgements, each with its reasoning written next to it, and they are meant to be edited.

If you disagree with an anchor, change it and rerun. That disagreement, made concrete, is exactly the kind of conversation this project is for.

## How you know it is not broken

The repo checks itself. `check_century.py` is the gate.

```bash
python3 check_century.py                     # regression against stored golden outputs
python3 check_century.py --doc-figures      # every table in the documents vs fresh engine runs
python3 check_century.py --doc-figures-fast # the same, minus the 800,000-world sources (~3 min vs ~13)
python3 check_century.py --readability      # are the documents still readable by a person
python3 check_century.py --negative-control # plants a bug on purpose; the checker must catch it
```

Every figure quoted in `future.md`, in the strategy ladder of `strategy.md` and in the summary tables of `realistic-bet.md` is machine-checked against the engine, so the documents cannot silently drift from the code. That includes the calibration tables, whose numbers come from the reweighting rather than from any single run and so are checked against a fresh calibration instead. The full check simulates about ten million worlds and takes roughly thirteen minutes. `--doc-figures-fast` drops the 800,000-world sources and runs in about three. It names every spec it skipped, since a gate that quietly covers less than it did yesterday is worse than a slow one. The readability check measures the documents themselves: how long the sentences run, whether every technical word is explained somewhere, and whether each document opens in plain language.

Further audits cover the accounting for wars and pandemics, the calibration, the policy feedbacks, the curvature of capability growth, and the way the input ranges are correlated. Run `python3 check_century.py --help` to see them all. The sensitivity tool in `sobol_century.py` tests itself against a textbook case with a known answer before it touches the model.

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
| [`docs/reading-the-output.md`](docs/reading-the-output.md) | how to read the JSON a run prints, block by block |
| [`docs/sensitivity-charts.md`](docs/sensitivity-charts.md) | how to read the sensitivity charts, in plain terms, lessons up front |
| [`check_century.py`](check_century.py) | the self-checking gate described above |
| [`calibrate_century.py`](calibrate_century.py) | tilts the 800,000 worlds toward the published estimates |
| [`sobol_century.py`](sobol_century.py) | which parameters drive the outcome, interactions included |
| [`plot_sensitivity.py`](plot_sensitivity.py) | builds the three sensitivity charts from the engine |
| [`Makefile`](Makefile) | shortcuts to run the model and build the charts; `make help` lists them |
| [`anchors.json`](anchors.json) | the external estimates the model is anchored to, with sources |
| [`lever-anchors.json`](lever-anchors.json) | how likely each policy choice is to happen (the third view), with the reasoning written down |
| [`golden/`](golden) | stored reference outputs the regression gate compares against |
| [`notes/`](notes) | generated working notes and the sensitivity charts (PNGs) |

## Honest limits

**One assumption dominates, and it is a coin flip.** Suppose an AI ends up more capable than anyone can control. Does that danger ever pass, or does it sit there for as long as the gap is open? Nobody knows, so the model tosses a coin: half the futures say the danger fades, half say it never does. In the futures where it fades quickly 29.5 % end irreversibly badly, and in the futures where it never fades 59.1 % do. Every headline number on this page is the average of those two halves. That coin flip moves the century further than any choice in the table above, and it is the main reason the extinction figure here sits above most expert surveys. `CENTURY_STRUCT_P_FLAT` weights the coin if you think one side is likelier.

This is a model, and a hundred years is a long time. The outcome categories are simplifications. The ranges are judgement calls anchored to today's estimates. The model cannot contain surprises nobody has imagined. Section 8 of [`future.md`](docs/future.md) spells out the caveats properly.

Read the numbers as a disciplined way to reason about which choices matter, under assumptions you can inspect and change. You can see which choices move the century from bad to good, and you can test them yourself today.

## Where to read next

- [`how-it-works.md`](docs/how-it-works.md): what this is and how it works, in about a thousand words, assuming nothing.
- [`levers-and-preparedness.md`](docs/levers-and-preparedness.md): each realistic choice explained, and what it buys.
- [`realistic-bet.md`](docs/realistic-bet.md): how likely those choices are, and what doubting them costs.
- [`reading-the-output.md`](docs/reading-the-output.md): the JSON report, block by block.
- [`future.md`](docs/future.md): the full report, every number and every caveat.
- [`strategy.md`](docs/strategy.md): what to do about it.
