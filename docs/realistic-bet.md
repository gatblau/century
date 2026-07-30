# The realistic bet: how likely are the good choices?

*The other documents show that a handful of choices, made in time, turn a century that leans the wrong way into a clearly good bet. This page asks the awkward follow-up: how likely is the world to make those choices at all? It gives an honest estimate for each one, shows what those estimates do to the odds, and explains how to disagree and rerun.*

---

## 1. Three ways to read the model

The model plays out 800,000 possible futures. Those futures can be counted three ways, and the repository reports all three side by side.

| Reading | The question it answers | Good century | Bad century |
|---|---|---:|---:|
| The headline | what could happen, if every choice stays open? | 40.4 % | 46.6 % |
| The outside view | what do professional forecasters expect? | 44.5 % | 41.3 % |
| The realistic bet | where is the century actually heading? | 35.6 % | 50.5 % |

The headline is the number the rest of this repository leads with. It treats every choice as open, so it describes potential. The outside view adjusts the totals to match published expert forecasts about things like extinction risk. The realistic bet, this page, applies an honest likelihood to each choice and reads off what is left. If you want one number for "where are we actually heading", it is the last row.

A doctor would put the difference this way: with the treatment, your odds are good; knowing how rarely patients actually take the treatment, your odds today are worse. Same disease, same medicine. One number describes the possibility, the other the path we are on.

The headline and realistic-bet figures come from the full 800,000-world run, the same one every other document quotes. The outside view is built at the 50,000-world calibration size, so its row is a touch less precise.

The headline row itself has a companion the model reports beside it. It assumes that testing and containment work goes stale as capability grows, which is the model's default; pin that decay to zero and the same worlds give 45.5 % good against 39.5 % bad. Nothing anyone has published fixes how fast the decay runs, so the two readings are both live and this page uses the default throughout ([`future.md`](future.md) §3).

## 2. The hidden guess in the headline number

The headline result looks neutral about the choices. It is not.

To build its worlds, the model rolls dice for each choice. Those dice are fair: a world where the gains of AI are widely shared comes up just as often as a world where they are hoarded. A watchful regulator comes up just as often as a captured one.

Fair dice sound neutral. They are actually a forecast in disguise. They treat every setting of each choice, strong or weak, as equally likely, and nobody believes that. The companion document about the choices ([`levers-and-preparedness.md`](levers-and-preparedness.md)) spends pages on what stands in the way: wealth resists being shared, regulators get captured, safety budgets stay small, and nobody slows down first.

So this page replaces the fair dice with weighted ones, and writes the weights down where everyone can see them.

## 3. How we score each choice

Each choice in the model is a dial, not a switch. So we need a rule for saying "this world made the choice".

The rule: a world counts as having made a choice when its dial sits in the strongest quarter of the range. This is the same cut the other documents already use when they measure what a choice is worth. With fair dice, every choice lands in that strong quarter exactly 25 times in 100.

That gives the estimates in the next section a simple meaning. An estimate of 5 to 20 % says: less likely than chance. An estimate straddling 25 % says: the fair dice were about right.

## 4. The likelihood of each choice

| The choice | What it would look like in the real world | How likely by ~2035 | Why |
|---|---|---|---|
| Share the gains | a major economy runs a scheme that pays AI profits out to most citizens, and it survives an election | 5 to 20 % | schemes like this are rare in history, and the people who would fund one are the people who gain from its absence |
| Institutions that react | a real regulator for frontier AI: agreed triggers, compulsory incident reports, and at least one enforcement action on record | 8 to 22 % | there is momentum (safety institutes, the EU AI Act), but nowhere enforces this yet, and regulators move in years while AI moves in months |
| Fund the safety work | research on steering and testing AI funded at a level comparable with the money spent making AI stronger | 4 to 15 % | today the safety budget is a small fraction of the capability budget, and gaps that size rarely close in a decade |
| Use AI for safety work | AI labs routinely use their own systems to test and check the next ones | 20 to 50 % | labs can do this alone, it is in their own interest, and it is already happening |
| Cool the race | the leading powers sign a deal to limit the race, with real checking, and honour it | 3 to 12 % | it needs rivals to trust a verification system, and history has few such deals signed before a disaster forces them |

These numbers are honest guesses, not measurements. No survey can settle "will a major economy share the AI gains by 2035". What we can do is write each guess down with its reasoning, in one editable file ([`lever-anchors.json`](../lever-anchors.json)). If you think a number is wrong, change it and rerun. Section 6 shows how.

The adjustment sets each probability to the middle of its range, which is the estimate itself rather than a hopeful or harsh corner of it. And it bends the 800,000 worlds as little as possible while getting there: 66 % of them still count afterwards, so the results do not hang on a few extreme worlds.

## 5. What this does to the century's odds

| Outcome | The headline | The realistic bet |
|---|---:|---:|
| Good century | 40.4 % | 35.6 % |
| The best ending (aligned abundance) | 18.2 % | 12.4 % |
| Humans lose control quietly (disempowerment) | 31.4 % | 34.4 % |
| Irreversibly bad century | 46.6 % | 50.5 % |

The century leans further the wrong way: roughly 36 good against 51 irreversibly bad. Three things stand out.

First, where the loss goes. The odds get worse mainly through the quiet ending, where humans stay alive but stop steering, and the best ending pays most of the bill (18.2 % falls to 12.4 %). That fits: the choices in section 4 are exactly the ones that block the quiet path, so doubting them puts probability back on it.

Second, the conclusion is not hanging on one harsh guess. Rerun the adjustment against the friendliest edge of every range instead of the middle and the good share still only reaches about 39 %. Anywhere inside the stated ranges, the realistic bet lands below the headline, which makes the headline the optimistic reading of current politics rather than the neutral one.

Third, the size of the prize. With the choices actually made, the model's good share is about 68 in 100. At the estimated likelihoods it is 35.6. That gap of more than 30 points is not blocked by physics or by any rival. It is only unlikely, and unlikely is a thing a decision can change.

## 6. How to run it and change it

```bash
# run from the repository root
python3 calibrate_century.py 800000 --levers       # build the weights and print the fit
CENTURY_LEVER_WEIGHTS=weights-levers-800000-seed431.npz \
  python3 century_sim.py 800000                    # report now includes the realistic-bet tables

# all three readings in one report (50,000 worlds: the outside-view weights ship at that size):
CENTURY_WEIGHTS=weights-xpt_superforecaster-50000-seed431.npz \
CENTURY_LEVER_WEIGHTS=weights-levers-50000-seed431.npz \
  python3 century_sim.py 50000

# to disagree: edit a p_range in lever-anchors.json, then
python3 calibrate_century.py 800000 --levers
CENTURY_LEVER_WEIGHTS=weights-levers-800000-seed431.npz python3 century_sim.py 800000
```

The first command prints a fit report: each estimate, where the model started, and where the weighting landed. A range the model cannot reach announces itself in that report instead of failing silently. `python3 check_century.py --lever-audit` tests the whole path end to end.

## 7. What to keep in mind

- **The estimates are judgements.** That is the nature of the question. The defence is that they are written down, reasoned, and trivial to change.
- **The scoring rule is a convention.** "Strongest quarter of the dial" is one reasonable cut. A stricter or looser cut would give different numbers.
- **The choices are linked.** In the model, a racing world tends to have sleepy institutions, and a sharing world tends to have alert ones. The weighting keeps those links.
- **The world can still learn.** These estimates are about where a world starts. In the model, a scare can still wake institutions up mid-century, at whatever speed they are capable of.
- **The estimates drive everything.** The view sits exactly on the middle of the stated ranges, so it is only as good or as bad as those ranges. If you think they are too kind or too harsh, edit them in `lever-anchors.json` and rerun; do not squint at the output.
