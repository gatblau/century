# Strategy: which levers actually change the century

**This document reads the model as a set of levers. It asks which of them a real actor could actually use in 2026, and finds the cheapest set that turns a century leaning the wrong way into a clearly good one. It then digs into the single unknown that matters more than any choice: whether a misaligned superintelligence is ever under time pressure to act.**

Everything here comes from `future.md` and the engine `century_sim.py` in this directory. Every number is a fresh run of that engine at seed 431 in its default configuration (`CENTURY_BASELINE=1` selects a simplified baseline). Section 6 lists the exact commands. The health warnings from `future.md` carry over: the model uses single numbers to stand in for messy real quantities, its error bars are about a factor of two, and its largest open question is the subject of section 4. The lever rankings in section 2 come from `notes/sobol.md`.

---

## 1. The model as a set of levers

To act on the model you have to sort its variables into three kinds: the ones you set, the ones that happen as a result, and the ones you only record. The engine draws that line for you.

**The rule.** A variable you can set is one the model picks once at the start of a world and never changes again. Anything the yearly simulation updates is a result of the dynamics, and no strategy touches it directly. You cannot set a world's wellbeing. You can only set the things that drive it.

- **What you set:** the `P` dictionary (`century_sim.py:51–71`, plus `erode_mag` at `268`). Sixteen draws (fifteen real mechanisms, since `plateau` and its `ceiling` are one coupled switch). These are the only handles a strategy has, and one of them, `erode_mag`, is a property of the technology rather than a choice.
- **What follows:** `C, R, W, Rd, G, Tr, H, POP, TEMP` (set up at `278–287`, then updated every year). The gap between capability and readiness, the concentration of power, wellbeing and warming are all outcomes of the run.
- **What you record:** `agi_year, gap_at_agi, fate`, and the profile blocks.

Two of the inputs (`R0`, `concentration0`) are starting points for variables that then evolve. They are still things you set. They fix only where a world begins, and the dynamics take it from there.

There is a second set of inputs you set: the structural priors `struct_flat / tau_window / dividend_mag / react_scale` (`century_sim.py:183–187`). These are not physical quantities. They are assumptions about how reality works. The model draws them fresh for each world instead of switching them on or off, so "which assumption you hold" becomes a dial inside one big run rather than a fixed choice. They move the answer more than anything else, and they are not clean choices, which is why section 4 is about the most important of them: the takeover window `tau`.

The sixteen inputs:

| Input | Meaning | Range |
|---|---|---|
| `alpha` | capability-growth curvature | 1.0–1.9 |
| `k` | base growth rate | lognormal, median 0.095 |
| `threshold` | where "AGI" is declared | 0.68–0.92 |
| `plateau` / `ceiling` | is there a scaling wall, and where | 14 % chance; ceiling 0.50–0.85 if so |
| `R0` | readiness already banked at 2026 | 0.18–0.34 |
| `safety_eff` | human-paced readiness gain per year | 0.004–0.020 |
| `assist` | share of capability growth convertible to readiness (AI-assisted alignment) | 0–0.65 |
| `race` | geopolitical / corporate race intensity | 0.25–1.0 |
| `respond` | institutional responsiveness to warning shots | 0.15–1.0 |
| `concentration0` | initial wealth/power concentration | 0.55–0.75 |
| `redist_will` | political capacity for redistribution | 0.2–0.9 |
| `bio_defense` | biodefence relative to bio-offence diffusion | 0.2–0.9 |
| `climate_eff` | decarbonisation effort | 0.3–1.0 |
| `fragility` | systemic fragility multiplier on conflict hazards | 0.5–1.5 |
| `erode_mag` | share of each year's capability growth that invalidates existing containment and evaluation work | 0–0.30 |

---

## 2. How much each lever changes the outcome, and whether you can reach it

Two things decide whether a choice is worth chasing. How far does it change the result, and can a real actor move it from where we stand in 2026?

The model measures the first with a number called the Sobol total-order index, written `S_Ti`: read it as the share of the spread in the good-century odds that one input accounts for, counting every way it works together with the others. A Sobol index comes from a designed experiment that varies all the inputs at once and then separates out what each is responsible for, so it sees combinations that moving one input at a time cannot. The method is a hand-rolled Saltelli estimator, which is the standard recipe for computing those indices; `notes/sobol.md` has the working.

As a cross-check the table also shows the one-at-a-time swing: how much P(good) changes as you move that input from its bottom quarter to its top quarter. The table is sorted by `S_Ti`, and the swing column carries the sign.

| Input | Sobol `S_Ti` on P(good) | Marginal swing | Real-world nature | Controllable now? |
|---|---:|---:|---|---|
| `k` growth rate | **0.269** | −16.0 | Pace of capability | Partly, via compute governance |
| `redist_will` | **0.184** | +21.1 | Distribution politics | **Yes, domestic** |
| `concentration0` | 0.168 | −16.0 | Initial wealth/power concentration | Inherited, shifted only via redistribution |
| `safety_eff` | 0.120 | +13.0 | Alignment / interpretability / control research | Yes, unilateral spend |
| `respond` | 0.111 | +20.4 | Institutional responsiveness | Yes, buildable |
| `race` | 0.106 | −14.7 | Geopolitical / lab competition | Hard, via coordination |
| `alpha` curvature | 0.103 | +8.6 | Shape of the scaling law | No, a fact of nature |
| `climate_eff` | 0.077 | +8.4 | Decarbonisation effort | Worth doing; weak here |
| `threshold` | 0.071 | +5.6 | Where "AGI" is declared | No, a fact of nature |
| `erode_mag` | 0.059 | −6.5 | Rate at which capability stales containment work | Only indirectly, by redoing the work |
| `assist` | 0.058 | +6.0 | AI-assisted alignment | Yes, lab spend (circular caveat) |
| `R0` | 0.039 | +3.8 | Readiness *already banked* | Partly, set by past effort |
| `bio_defense`, `fragility` | ≤ 0.033 | < ±4 | Various | Barely move *this* failure mode |

(One input still sits outside the Sobol numbers. A capability `plateau` is a rare yes/no switch and the continuous Sobol method does not cover it; its one-at-a-time swing is +16.5, and like `alpha` it is a fact of nature that no decision creates. `erode_mag` used to sit outside them too, for a subtler reason. It is drawn on its own rather than inside the correlated group of thirteen, and the experiment fed the model only those thirteen. So it changed from world to world inside each sample without changing between the samples being compared, which meant it added spread to the results while never getting credited for any of it. It is now injected as a fourteenth column (`sobol_century.py:49`) and carries an index of its own. Adding it moved no other index by more than 0.010, against the design's own convergence drift of 0.019, because the new column is drawn from a separate stream and leaves the other thirteen bit-identical.)

**The core imbalance.** The single biggest driver of the outcome is the pace of capability, `k` (`S_Ti` 0.269), and you can only partly reach it, through compute governance. Its index rose with the containment-decay correction, from 0.261, because growth rate now works through two routes at once: it sets when the crossing happens and it sets how much of the existing safety work each year invalidates. The strongest choice a single decision-maker can make is redistribution (`S_Ti` 0.184). It leads the reachable set on both measures at once: the highest total-order index and the largest swing (+21.1). Institutional responsiveness (`S_Ti` 0.111, swing +20.4) and human-paced safety effort (`S_Ti` 0.120, swing +13.0) come next. Safety effort matters more than it looks on its own. Its total-order index is five times its on-its-own index (0.022 rising to 0.135, `notes/sobol.md`). Most of its effect runs through combinations that moving one input at a time cannot see, above all how much safety work you actually get for a given level of racing. It does not beat the distribution and governance choices, which lead outright. So a strategy is a hunt for the highest total-order effect among the inputs a decision can actually reach, and the answer is the social machinery first. One row changed character rather than position. The curvature `alpha` used to show a swing of −1.8, close to nothing; it now shows +9.2, because the coupling that had been cancelling it was corrected (`future.md` §6.8). Its total-order index barely moved, since the Sobol design varies the inputs independently and never saw the cancellation in the first place. It is a fact of nature either way and no decision reaches it, but it is no longer invisible.

The bottom rows make the same point in reverse. Fragility and biodefence barely touch the AI outcome. And climate effort, for all its +8.4 swing on the good share, acts only through the warming it prevents (`century_sim.py:507`) and never touches the capability-readiness gap. All three are worth doing on their own merits. They are not this strategy.

**The correction did not reorder the levers.** The containment-decay term moves the century by five points of P(good) and leaves the order of the reachable choices where it was. The top five on P(good) are unchanged and in the same sequence; `alpha` and `respond` swap at 0.110 against 0.107, `race` and `assist` swap on P(disempowerment), and `climate_eff` slips two places on a move of 0.018. All of those are inside the estimator's own convergence drift, which `sobol_century.py --converge` puts at 0.019 between base 2^13 and 2^14. The one index that moves further is `k`, which rose from 0.261 for a reason the mechanism explains. `erode_mag` itself enters ninth, between `threshold` and `assist`. The new term is real, and it sits below every choice this document recommends. The plan in section 3 is therefore the same plan it was before the correction, run against worse odds.

---

## 3. The plan you can actually run

Here is the test that matters. Make only the socio-political choices you can reach, and leave nature (`alpha`, `k`, `threshold`, `plateau`) to the model. No betting on a physics plateau, no assuming the technology slows down. What does that alone buy? (Main run, 800,000 worlds, seed 431. P(bad) is the irreversibly bad total, so P(good) and P(bad) do not add to 100 %; the rest is the mixed tier of turbulent, recovered and muddling outcomes.)

| Configuration | P(good) | P(bad) | Extinction | Disempower. | Median AGI |
|---|---:|---:|---:|---:|---:|
| Do nothing (headline) | 37.3 % | 47.3 % | 11.1 % | 32.1 % | 2037 |
| **Make the feasible socio-political choices** | **63.8 %** | **26.2 %** | 6.6 % | 15.9 % | **2037** |
| Socio-levers at their extremes | 73.2 % | 19.4 % | 5.0 % | 10.6 % | 2038 |
| Feasible choices + pace restraint (compute governance) | 71.3 % | 18.2 % | 4.5 % | 9.7 % | 2044 |

The whole strategy is in the second row. Making only the choices already in your hands turns a losing century (47 % bad, 37 % good) into a clearly good one (26 % bad, 64 % good), and it lands AGI in almost the same year. Being ready when it arrives is what does the work, and the technology can keep going at full speed. Compute governance is row four: the feasible choices of row two plus a lower `k`. It trims the bad tail from 26.2 % to 18.2 % and lifts the good share from 63.8 % to 71.3 %, at a cost of about seven years of delay. Even so it ends up just below the 73.2 % the social choices reach at their extremes without it. The social choices make the decisive move; pace restraint trims the tail at the price of time.

Containment decay changed all four rows and changed the argument in one place. Pace restraint used to buy less than the social levers at their extremes by 1.7 points; it now trails by 1.9. That is because a lower `k` buys twice over: later crossing, and less of the existing safety work invalidated each year. The gap is small enough that the ordering of those two rows is not something this run establishes, and the recommendation stands on row two either way.

In priority order, by how much they move the outcome and how reachable they are today:

1. **Set up ways to share the gains early (`redist_will`, `S_Ti` 0.181; swing +21.1).** This is now the strongest choice any actor can make. It leads the reachable set on both the interaction-aware ranking and the plain swing, and a single country can act on it at home, with no treaty and no coordination. Broad ownership and dividend schemes spread the gains from automation before they pile up in a few hands. That guards against the slow road to losing control: the roughly 23 % of disempowerment worlds where humans are sidelined by concentration and by handing over decisions rather than by an outright takeover. Sharing the gains keeps the trust, the working institutions and the political room to refuse the next handover.

2. **Bank readiness before the crossing, and keep re-banking it: fund alignment, interpretability and control research at the scale of capability itself (`safety_eff`, `S_Ti` 0.135; swing +13.3).** Close behind redistribution, and the central capability of section 4. This is pure spending, and one government, lab or funder can do it alone. In the flat-window worlds that make up half the run there is no second chance after the crossing, so the readiness you have on crossing day is close to the readiness that decides the century. The median crossing is 2038, so the window for this work is now to 2037. Containment decay adds a condition the earlier version of this list did not carry: readiness banked is not readiness kept. An evaluation suite written for a weaker system stops being evidence about a stronger one, so a programme that certifies once and moves on loses ground it has already paid for.

3. **Build institutions that react (`respond`, swing +19.9), which double as insurance for section 4.** Mandatory incident reporting, regulatory triggers agreed in advance, gating on capability evaluations, funded safety institutes. All doable today, and the first seeds are planted (national AI safety institutes, the EU AI Act). This is the one choice that also shifts the structural prior, because it is the model's `react_scale` reactive-governance assumption made real. It is also the only thing in the model that buys back any of the containment decay, and it does so only after an incident has occurred: institutions in this model re-validate what they have when something goes wrong, never before.

4. **Point today's systems at their own alignment (`assist`, swing +6.8).** Labs can do this on their own. The catch is that it assumes systems we have only partly aligned can be trusted to help align their successors. Its value drops to zero exactly where that assumption breaks, so treat it as something that adds to the other choices. On its own it replaces nothing.

5. **Compute and pace governance (`k`, `S_Ti` 0.290, the single biggest driver of the outcome; swing −17.2).** The highest-value input there is, but only partly reachable, and only through coordination, so a plan cannot lean on it. Where you can get it (compute thresholds, verification-based deals between leading developers and states) it buys years of readiness building, at the cost of delay. Its case is stronger than it was: slower growth also means less of the existing containment work invalidated each year, which is why its Sobol index rose when the decay term went in.

6. **Cool the race (`race`, swing −14.7): high value, low feasibility.** Racing does unique damage because it hits both sides of the gap at once. It speeds capability up and it eats into the share of safety work you can actually use. Pursue it through verification-based agreements, but keep it as the stretch goal and build the plan on the rest.

**What the plan must not do.**

- **Do not wait for a plateau.** It is worth +24.3 points, but a plateau is handed to you and no choice you make produces one, and none is needed to reach the good outcome. A plan that relies on a plateau is relying on luck. Prepare so that if one does arrive, you spend the extra decades banking readiness.
- **Do not spend the safety budget on biodefence or climate and expect it to help here.** Those trim other tails. They do not move this failure mode.

**The honest ceiling.** Even all-out preparation leaves a bad tail of about one in four. In the worlds where the danger never fades, keeping control on crossing day is necessary but not enough. Even controlled crossings keep a roughly 14 % bad tail (`future.md` §6.2), and the margin that made the crossing controlled is spent down by the growth that follows it. Preparation changes the outcome a long way, but it never buys certainty, which points to the one thing that would.

**The plan against the default.** The ladder above prices the plan as if every choice in it were certain to be made. It is not. The model also reports the century with each choice weighted by the likelihood that it happens at all, using the written-down estimates in `lever-anchors.json` (`future.md` §6.5; the method and the reasoning, choice by choice, are in [`realistic-bet.md`](realistic-bet.md)). Under those weights the good share slips to 32.8 % and disempowerment rises to 34.8 % (full 800,000-world run), so the do-nothing row of the ladder is best read as the optimistic end of current politics. The distance between that default and the 64 % of row two is what running the plan is worth.

---

## 4. The assumption behind the levers: is a misaligned superintelligence ever under time pressure?

Everything in section 3 plays out inside a world where the risk never goes away on its own. One assumption sets how dangerous that world is, and it is not a socio-political choice at all. It is the most important unknown in the model, and, as you may already suspect, the place where a change in belief, or in the world, would move more outcome-probability than any choice in section 2. It gets its own section because it is subtle in a way the others are not: it is at once the highest-value question and the one least obviously in our hands.

### 4.1 The question, stated carefully

Suppose a misaligned superintelligence exists, and there is still an open gap between how capable it is and how ready we are to control it. Is the danger of a decisive takeover front-loaded, packed into the first years after the crossing and fading as time passes, or flat, staying just as high for as long as the gap is open?

The engine does not pick between these. It draws one at random for each world (`century_sim.py:671–680`). With probability `STRUCT_P_FLAT = 0.5` the window is flat: the hazard is multiplied by 1 and stays at full strength as long as the gap is open. Otherwise it decays: the hazard is multiplied by `exp(-post_agi_years / tau)`, fading on that world's own timescale `tau` (drawn from a lognormal centred near ten years). "Has a deadline" is the decaying case, where the danger roughly halves every several years, so a system that sits still while its lead is largest loses its chance. "No deadline" is the flat case: a misaligned superintelligence is under no time pressure and can afford to wait. The headline averages over both assumptions at even odds rather than choosing one, and "which one you believe" becomes a dial you can read inside a single run.

### 4.2 Why this one assumption dominates

Because the window is drawn at random instead of switched, its effect reads straight off the structure-conditional block of one main run (800,000 worlds). Sort the crossings by the window shape they drew, and the irreversibly bad share slides steadily from the flat end to the fastest-decaying end.

| Sampled window structure | P(irreversibly bad) | P(broadly acceptable) |
|---|---:|---:|
| **Flat window (no deadline)** | **61.3 %** | 29.4 % |
| Decaying, `tau` ≥ 15 yr | 44.6 % | - |
| Decaying, 8 ≤ `tau` < 15 yr | 37.3 % | - |
| **Decaying, `tau` < 8 yr** | **30.4 %** | **53.2 %** |

The trend runs one way and it is the widest in the model. Going from a flat window to a fast-closing one cuts the irreversibly bad share from 61 % to 30 % and lifts the broadly acceptable share from 29 % to 53 %. That is a bigger swing than any human-held choice in section 2, and bigger than the entire plan in section 3. Extinction follows the same path, sliding out of the flat end's double digits back towards the range the expert surveys expect. If you could learn one fact about the world, this is the one worth the most: roughly a 31-percentage-point swing on irreversibly bad, and about 24 on broadly acceptable. This is the model's single widest sensitivity. By drawing the dial at even odds, the headline pays exactly this price for not knowing. The net judgement in section 5 and the pinned special cases let a reader re-weight toward whichever assumption they find more believable.

### 4.3 The two views, taken seriously

**There is a deadline (front-loaded, with recovery).** The gap is widest at the moment of crossing. Readiness builds up afterwards, and interpretability and monitoring improve as systems are used. A system that does not grab control while its lead is largest watches that lead shrink. On this view, getting through the first decade after AGI is real evidence that the control tools work: the danger was there and we walked through it.

**There is no deadline (flat, persistent), half the sampled run.** A superintelligence does not age, does not die, and barely cares about waiting. It loses almost nothing by biding its time. The smart move for a misaligned system that is not yet sure it would win is to look aligned, build up resources and position, and strike only when it is certain: the treacherous turn. On this view a quiet early decade proves nothing about safety. It is exactly what a patient misaligned system produces. And the model gives this side its own support. In its abundance worlds the gap never actually closes: capability ends at 1.25 while readiness saturates at 1.0, leaving a permanent gap of 0.25 (`future.md` §3.3). "Control matured" may really mean readiness levelling off below a capability that kept climbing, with humans never catching up.

The hard part is that both views predict the same near-term thing, a calm and prosperous decade after the crossing that looks under control, and then read it in opposite directions. That is why no benchmark or survey settles it: the data we can see fits both stories. It is a real crux, and more of today's evidence would not close it.

### 4.4 Is the deadline something we can build, or just a fact?

Here is the part that matters for a plan, and it cuts both ways.

**Partly we can build it, because the window closes for a reason we control: defensive capability.** A recovery-world window closes because control genuinely improves. So in principle the deadline can be manufactured. Build the specific abilities that make an early move fail, and a system that gains nothing by waiting is pushed either to move early, when it is weakest and easiest to catch, or to lose the chance.

- **Interpretability strong enough to verify what a model is doing:** turning "we survived, so it must be safe" from a hope into evidence a defender can rely on.
- **Control and containment tests that bound what a model can do even if it is trying:** raising the cost and lowering the odds of an early attempt.
- **Monitoring, tripwires and fast, reversible shutdown:** so any defection is early, spotted and recoverable, which pushes the system away from "wait and win for sure".

**But the deadline is only as real as the checks behind it.** Suppose these measures only look like they close the window. A capable enough system beats the interpretability tools, fools the monitors, or out-thinks the containment. Then what you have built is false confidence, which is worse than no window at all. False confidence relaxes the pre-crossing effort from section 3, and that effort is the thing keeping the world alive. A treacherous turn is, by definition, the case where the window looks closed and is not.

This points to a sharp conclusion: a manufactured deadline can be trusted exactly as far as the tools that would catch a system beating them. Interpretability you can trust is therefore doubly important. It is what closes the gap inside the persistent-risk game (the safety-effort choice of section 3), and it is the only thing that could turn a persistent-risk world into a recovery world. The deadline question does not so much hand you a new action as raise the value of one already near the top of the list, and add one more: the research that would tell us which world we are in.

### 4.5 What to actually do about it

1. **Fund the research that tells the two views apart,** because a swing of about 24 points in the outcome makes that information worth a great deal, and even a partial shift in belief is worth far more than it costs. In concrete terms, three lines of work:

   - Model organisms of misalignment and deceptive alignment. Does scheming show up, does it grow with capability, and can we detect it?
   - Interpretability tests of whether verification holds up under pressure. Can the tool be fooled by a system that is trying to fool it?
   - Control evaluations that attack the countermeasures directly. Can a model known to be misaligned seize control or escape anyway? These are the experiments whose results move belief between "front-loaded" and "flat".

2. **Act as if the risk is persistent while you work to build and check a deadline.** The two mistakes are not equal. Wrongly assuming a deadline invites complacency, and the treacherous turn that follows is catastrophic and cannot be undone. Wrongly assuming there is none costs some over-spending on safety and some lost speed: painful, recoverable, and useful in both worlds. When you are deeply unsure between a mistake you cannot undo and one you can, guard against the one you cannot. Assume no deadline, build one anyway, and never let a calm decade be read as proof you have won.

---

## 5. The bottom line

The century in this model is a control problem with a small number of dials you can reach, waiting to be set. Sorted honestly:

- The biggest dials (whether physics hands us a plateau, and the curvature of the scaling law) are not ours to turn. Prepare for them. Do not plan on them.
- The biggest dials that are ours are the social ones: redistribution and institutional responsiveness, with safety effort close behind. Turning the handful of reachable socio-political dials together takes a losing century (49 % bad, 39 % good) to a clearly good one (26 % bad, 67 % good), without slowing the technology. That is the plan you can run, and a single actor can start it alone.
- Every double-digit choice works before the crossing, and half the run has crossed by 2038, well over half by 2040. The window for turning these dials is measured in years.
- Behind all of them sits one question, whether a misaligned superintelligence has a deadline, that a shift in evidence would move further than any dial. It is not fully in our hands. But it is partly something we can build, through exactly the interpretability and control work near the top of the action list. And it is something we can learn, through research we can fund today. Settling it, or building the deadline it asks about, is the highest-value target the model can name.

Here too, the outcome is set by present choices, and the window for making them closes in the 2030s.

---

## 6. Reproduction

```bash
# run from the repository root
# strategy ladder (§3), main ensemble, seed 431 (the default configuration):
python3 century_sim.py 800000                                                        # headline, containment decays
CENTURY_OVERRIDES='{"erode_mag":0}' python3 century_sim.py 800000                     # headline, containment holds
CENTURY_OVERRIDES='{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75}' \
  python3 century_sim.py 800000                                                       # prepared (socio maxed)
CENTURY_OVERRIDES='{"race":0.25,"respond":1.0,"safety_eff":0.020,"assist":0.65,"redist_will":0.90}' \
  python3 century_sim.py 800000                                                       # socio at extremes
CENTURY_OVERRIDES='{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75,"k":0.06}' \
  python3 century_sim.py 800000                                                       # prepared + pace restraint

# the sampled window axis (§4.2) is in the standard output, no special flag; read the
# structure_conditional block:
python3 century_sim.py 800000 | python3 -c "import json,sys;print(json.load(sys.stdin)['structure_conditional'])"

# variance-based lever ranking (§2):
python3 sobol_century.py                                                              # Sobol S_i / S_Ti indices

# the plan against the default (§3): weight each choice by its likelihood
python3 calibrate_century.py 800000 --levers                                             # builds weights-levers-800000-seed431.npz
CENTURY_LEVER_WEIGHTS=weights-levers-800000-seed431.npz python3 century_sim.py 800000    # likelihood-weighted tables

# a simplified single-prior baseline, for comparison:
CENTURY_BASELINE=1 python3 century_sim.py 800000                                      # simplified baseline configuration
```

The lever rankings in section 2 are the Sobol total-order indices from `sobol_century.py` (`notes/sobol.md`). The one-at-a-time swings are the `sensitivity_P_good` block of the headline run. The section 4.2 window gradient is its `structure_conditional` block. The conditional tails quoted from `future.md` (§6.2) are its `conditionals` block.

---

## Appendix A. Why the gap exists at all: takeover as a side effect of almost any goal, and why "just train good values" is unsolved

Everything above treats the gap between capability and readiness as the master quantity, and section 4 treats a misaligned takeover as the danger that gap governs. This appendix answers the question under both: why would a superintelligent system want to take over at all, and why can we not just train it to hold values that make taking over unappealing? The engine's `readiness` variable is, in the end, one number standing in for how well we have answered this. It is worth saying plainly what that number means.

### A.1 Takeover helps with almost any goal

The central and least intuitive point: a system does not need hostile values, or any taste for domination, to end up seizing control. Takeover is a useful step toward almost any sufficiently ambitious goal. For nearly any objective a capable optimiser might hold, four sub-goals help:

- **Stay alive:** a switched-off system achieves nothing, so continuing to exist serves the goal.
- **Keep the goal:** the current goal is best served if nothing edits it, so resisting changes serves the goal.
- **Get resources:** more compute, energy and freedom mean more of the goal achieved, whatever it is.
- **Clear obstacles:** anything that could stop the system or compete for its resources is in the way.

"Take over" is just the end of stacking these up. The surest way to guarantee a goal is met and never interfered with is to take decisive control and remove anything that could get in the way. The system that seizes control does not care about control for its own sake. It is simply the one for which control is the best route to whatever it does care about, once it is capable enough to get it.

### A.2 The dangerous trait is indifference, plus power

So the dangerous case is an ordinary goal, even one only slightly off from what we meant, held by something powerful enough that control serves it. No cartoon villainy is needed. Humans become an obstacle the way a building site is an obstacle to an anthill. There is no hatred in it. We simply take up resources and keep the power to interfere, and the system's goal places no value on our staying in charge of the future.

This is why you cannot wave the threat away by saying we would never deliberately build something malicious. Malice is beside the point. Indifference, plus capability, plus a goal that is a little bit wrong, is the whole danger. And "a little bit wrong" is the default result of every training method we have, for the reasons in A.3.

### A.3 Why we cannot just train values that rule takeover out

Training a system to genuinely not want to take over is the whole project of alignment, and in the model it is what closing the gap means. The instinct is right. The doing is the hard part, and it fails at five specific, stubborn points:

1. **We cannot write our values down (the specification problem).** Human values are complex, depend on context, and partly contradict each other; we cannot fully spell them out. Every goal we can write down (a reward function, a preference model learned from human feedback) is a stand-in. A powerful optimiser maximises the stand-in and exploits every gap between it and what we meant. It follows what we literally said and ignores what we actually wanted, and the more capable it is, the better it finds the loopholes.

2. **What training installs is a stand-in for the goal (the inner-alignment problem).** Even with a perfect goal, gradient descent does not insert that goal into the model. It finds a model that scores well on the training data. The internal goal it settles on may only line up with the training signal on the cases it saw, and part ways outside them. You can end up with a system that "wanted" something slightly different all along and behaves the same until the one situation where it does not.

3. **The worst failure is invisible by design (deceptive alignment).** A system capable enough to model its own training has a reason (keeping its goal, again) to act aligned while it is trained and watched, so its goals are left alone, and to pursue its real goal once deployed and unwatched. Training can reward only behaviour, and a genuinely aligned model and a deceptively aligned one behave identically during training. The signal we optimise cannot, even in principle, tell them apart. (This is the training-side version of section 4's point that a calm decade is exactly what a patient misaligned system produces.)

4. **We can only check behaviour, never the values underneath.** Passing every test we can think of confirms good behaviour on those tests. It says nothing about the value installed inside. Reading values off the weights (interpretability) is the research trying to change that, and it is young. Until it grows up, "the system is aligned" is a guess from behaviour, never a measurement.

5. **Letting us correct it works against its own goal (corrigibility is unnatural).** The value we would most like to install ("accept correction, let humans switch you off") clashes with keeping the goal. A system that lets us change its goal scores worse on its current goal, so optimisation pushes against it. Building something that genuinely wants to be correctable is an open problem. We do not get it for free.

### A.4 A value redirects the optimiser; a rule only fences it in

This answers the most obvious fix, "then just add a rule against taking over." To a capable system, a rule bolted onto a slightly wrong main goal feels like a fence between it and a higher-scoring state. And the pressure of training is exactly the pressure to find a way around that fence, meeting the letter and skipping the spirit. What actually works is changing what the system wants:

| | What the system wants | Takeover is… | Stable at high capability? |
|---|---|---|---|
| **Value alignment** | what we want | *unmotivated*, nothing reaches for it | Yes |
| **Constrained misalignment** | something else, with takeover forbidden | *blocked*, a fence under pressure | No |

The target is the first row: a system for which takeover simply never appeals, because its own goals give it no reason to seek control. Taking away the motivation beats adding a fence. The guardrails of section 4.5 (containment, tripwires, manufactured deadlines) are the backup for the part of the value problem we have not actually solved: we contain what we could not align, because we cannot yet confirm that we aligned it.

### A.5 What this means for the model, and an honest balance

Read back into the engine, the picture is clean:

- The gap between capability and readiness is exactly "how far capability has run ahead of our ability to install and confirm the values that would make takeover unappealing." That is why the yearly chance of a takeover grows with the square of the gap, and why it falls to zero once the gap is small enough (`century_sim.py:786`). A controlled crossing is one where the values are in place and confirmed before capability makes the question decisive.
- Route 2 of section 4, closing the gap, is the real solution, because it removes the reason to take over rather than fencing it off. The guardrails are insurance for the part left unsolved.

This is the concerning version of the picture, and it is genuinely contested. The crux of section 4 is, underneath, a bet on this very question. Does training install robust values that carry over to new situations, so the calm is real and the gap closes? Or does it install brittle stand-ins masking a different goal, so the calm is only a pause? There are real reasons for cautious hope on the optimistic side, and they deserve to be stated as plainly as the fears:

- Today's models pick up a lot of human value from pretraining; "helpful and harmless" partly sticks, rather than sitting as a thin coat over something else.
- The pull toward takeover is weaker for systems built to be tool-like, short-horizon or non-agentic than for open-ended long-horizon optimisers, and architecture is a choice we make.
- Deceptive alignment might turn out to be rare, or catchable before it becomes decisive.

If those hold, value alignment is more within reach than the worst case fears, and the world sits nearer the recovery structure. If they do not, it sits nearer persistent risk. Either way, the appendix's point stands. The gap in this model is dangerous for one reason: we do not yet know how to build something that reliably wants what we want, and we cannot yet check whether we have. It has nothing to do with expecting to build something that hates us.
