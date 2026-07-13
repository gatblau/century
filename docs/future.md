# Century Superforecaster: the most likely outcome of the next 100 years

*A stochastic world model of 2026 to 2126, run as an 800,000-world Monte Carlo ensemble.*

The model is a vectorised Monte Carlo simulation (`century_sim.py`, in this directory) that samples deep uncertainty, runs explicit hazard processes for the ways a century can go wrong, and couples demographic, climate and economic dynamics to the AI transition. This document walks through the engine and then the conclusions the ensemble supports.

**The deepest unknown.** Whether post-AGI risk stays high while capability runs ahead of readiness, or fades as readiness matures, is the model's deepest unknown. The model does not pick a side. Each world draws its own takeover-window shape: flat (no deadline) with probability 0.5, otherwise decaying on a drawn timescale. The headline averages over both stances at even odds, and both survive as slices of one ensemble in section 6.1. The choice between the two structures cannot be settled with today's evidence, and section 6.1 states the crux.

**This is a reasoning instrument.** The value is in the shape of the results: which outcomes cluster together, what separates them, and which choices move the distribution. It is not in any single percentage, and every number below carries at least a factor-of-two error bar.

---

## 1. What the model is

Each simulated "world" steps year by year from 2026 to 2126. A world carries seventeen coupled state variables. The most important are:

| Block | State variables |
|---|---|
| Technology | AI capability `C`, readiness `R` (alignment, interpretability, control and AI-specific governance) |
| Political economy | wealth and power concentration `W`, redistribution `Rd`, governance quality `G`, social trust `Tr`, wellbeing `H` |
| Planet and people | population `POP`, warming `TEMP` |
| Bookkeeping | AGI-crossing year, capability-readiness gap at crossing, fate |

### 1.1 The core mechanisms

1. **Deep uncertainty is sampled per world.** Fourteen structural parameters (growth curvature, growth rate, AGI threshold, plateau regime, race intensity, institutional responsiveness, redistribution capacity, biodefence investment, systemic fragility, and five more) are drawn per world from ranges based on published expert and superforecaster estimates. Each world then also takes yearly random shocks.
2. **The growth law has tunable curvature.** `dC = k·Cᵅ`, with α drawn from 1.0 to 1.9, a bottleneck ceiling (compute, energy, data, coordination), and a 14 % chance of a paradigm-stall regime whose ceiling may sit below the AGI threshold. The shape spans the plausible range: linear growth is indefensible, and pure superexponential growth with no bottlenecks is equally so.
3. **Catastrophes are modelled as continuous hazard processes.** Nuclear war, engineered pandemics, natural pandemics, misaligned-AI takeover, totalitarian lock-in and gradual disempowerment are annual probability draws with graded severities and absorbing states. A world can be wounded without dying, and can die without warning.
4. **Readiness evolves as a racing curve.** Human-paced safety effort and race-degraded AI-assisted alignment of this year's capability growth both feed it, so the capability-readiness gap emerges from the run rather than being scripted.
5. **Demographics, climate and a political-economy block are coupled in,** so automation shocks, inequality, trust and conflict interact with the AI transition instead of running alongside it.

### 1.2 Fate classification

A world ends in exactly one of eleven outcomes. Four are absorbing: the world's history effectively ends when they occur. The rest are read off the surviving state at 2126. Collapse is non-absorbing, so a collapsed world may rebuild and re-enter as "recovered".

| Outcome | Meaning |
|---|---|
| **Aligned abundance** | AGI arrived and stayed under meaningful human control, and its gains reached most people. Wellbeing is high, power is only moderately concentrated, and redistribution works. Superintelligent capability persists well beyond what humans could exercise alone, but the systems answer to institutions that still answer to people. |
| **Oligarchic prosperity** | AGI arrived and is controlled, but its gains pooled at the top. Most people are materially comfortable, living off an economy the AI runs, while a narrow elite owns and directs it. Life is good in absolute terms, yet ordinary people have no real say in how any of it is governed. |
| **Turbulent transition** | AGI arrived, but the world never settled into either of the two stable AGI endings, the shared flourishing of abundance or the stable concentration of oligarchy. Control stays contested, wellbeing is uneven, and instability is chronic, with no equilibrium reached by 2126. |
| **Constrained flourishing** | No AGI by 2126, because capability plateaued or grew too slowly to cross the threshold. The world carries on much as it does today, with decent governance and wellbeing, and it still gets most of what was hoped from AI short of general autonomy. The intelligence transition is deferred rather than escaped. |
| **Muddling degraded** | No AGI, and the world governs itself badly: weak institutions, low wellbeing, or both. It has the same technology as constrained flourishing and differs only in its politics, which were not up to sharing the gains or steering the century. |
| **Disempowerment** | Humans survive, often in material comfort, but permanently lose meaningful control over their own future, whether to AI systems, to the elites who own them, or to automated institutions no one steers. The loss is usually quiet and often unfelt, arriving in a world that seems to be working, and once it happens nothing any human decides changes the outcome. |
| **Totalitarian lock-in** | A narrow human group captures AGI-grade control technology and freezes its own rule into place, beyond any later challenge. Unlike disempowerment, someone human is still firmly in charge; here the coercion is deliberate and the hierarchy is permanent by design. |
| **Civilisational collapse** | Survivors remain, but industrial civilisation has broken down after a severe nuclear exchange or pandemic, and it has not rebuilt by 2126. The damage is severe but not necessarily final: a collapsed world can still recover within the century. |
| **Recovered** | A world that collapsed at some point, rebuilt over a sampled recovery period, and re-entered the century with weakened institutions. It carries the scars of the collapse but is functioning again by 2126. |
| **Extinction** | No meaningful human future. Almost always the lethal branch of an uncontrolled AI takeover, where keeping humans alive is not worth the effort to the system that seized control; rarely, an engineered pathogen beyond any containment. Nuclear war never reaches this outcome in the model. |
| **Unknown catastrophe** | A terminal event outside the model's named channels, drawn from a small catch-all hazard for the risks a present-day model cannot foresee, the way a 1926 model would have missed nuclear weapons and engineered pandemics. |

### 1.3 Calibration targets

- **AGI timing**: 2023 to 2025 expert surveys and forecasting-platform aggregates give a median arrival of general or transformative AI in the mid-to-late 2030s under fast-progress assumptions, a long right tail, and a non-trivial chance of a plateau. The crossing distribution below (median 2036, 6 % never) sits inside that envelope.
- **Nuclear risk**: published per-year estimates of great-power nuclear war run roughly 0.1 % to 1 %. The model uses a 0.3 % base, raised by turbulence and racing.
- **Existential risk**: the Existential Risk Persuasion Tournament puts superforecasters at about 1 % extinction by 2100 and domain experts at about 6 %. With the takeover window held flat (the pure persistent-risk structure) the model's extinction output of 15.4 % sits well above that envelope, in the territory of pessimistic inside-view estimates from the AI-risk literature (over 10 %). The headline, which samples the window structure at even odds, lands near 10 %. The elevated figure is deliberate. It follows from taking the reference models' structural stance seriously, and section 6.1 shows exactly which assumption drives it. The tension between outside-view aggregates and inside-view structure is the live crux of the field, and this document does not pretend to resolve it.
- **Pandemic frequency**: COVID-class-or-worse pandemics have arrived a few times per century (the 1918, 1957, 1968 and 2009 influenza pandemics plus COVID-19), and Marani et al. (2021) put the frequency of extreme novel epidemics in the low single digits per century. The model's roughly 1.2 non-absorbing pandemics per world sits inside a 1 to 4 band.
- **Population**: UN World Population Prospects 2024 has global population peaking near 10.3 billion around 2084 and then declining, with a 2100 range of roughly 8.9 to 11.6 billion. Among worlds that avoid a global catastrophe the model's 2126 median is about 9.3 billion, inside that envelope. This target is survivor-conditional, matching the projection's no-collapse premise.
- **Warming**: IPCC AR6 puts 2100 warming above pre-industrial between about 1.4 °C under deep mitigation (SSP1-1.9) and about 4.4 °C under high emissions (SSP5-8.5), with a central no-strong-mitigation path near 2.7 °C (SSP2-4.5). The model's survivor median at 2126 is about 2.75 °C, also survivor-conditional.

---

## 2. How it was run

- Main ensemble: **800,000 worlds**, seed 431, years 2026 to 2126 inclusive, persistent-risk (default) structure.
- Five named scenario ensembles of 30,000 worlds each, holding chosen parameters fixed and sampling the rest (section 5).
- Recovery-structure sensitivity ensembles of 50,000 worlds each (section 6.1).
- Engine: `century_sim.py` (NumPy, fully vectorised across worlds). Reproduction commands in section 9.

---

## 3. Headline result: the outcome distribution at 2126

| Outcome | Probability |
|---|---:|
| **Disempowerment** | **27.4 %** |
| Oligarchic prosperity | 21.6 % |
| Aligned abundance | 19.4 % |
| Extinction | 9.7 % |
| Turbulent transition | 9.0 % |
| Constrained flourishing (no AGI) | 3.0 % |
| Recovered (post-collapse) | 3.0 % |
| Unknown catastrophe | 2.5 % |
| Muddling degraded (no AGI) | 2.0 % |
| Totalitarian lock-in | 1.8 % |
| Civilisational collapse | 0.5 % |

Aggregated:

| Aggregate | Probability |
|---|---:|
| **Broadly acceptable** (abundance + oligarchic + flourishing) | **44.1 %** |
| Mixed (turbulent + recovered + muddling) | 14.0 % |
| **Irreversibly bad** (disempowerment + lock-in + collapse + extinction + unknown catastrophe) | **41.9 %** |
| *of which extinction or civilisational collapse* | 10.2 % |

The first three rows are mutually exclusive and sum to 100 %; the fourth is a subset of the bad row, called out because it is the catastrophic tail.

Three features of this distribution matter more than any single number.

1. **The single most likely outcome of the next 100 years is permanent human disempowerment (about 27 %).** It beats both extinction and flourishing. Humans survive, often in material comfort, but lose meaningful control over their own history: to AI systems, to AI-owning elites, or to automated institutions no one steers any more. The typical failure of this century is quiet: a comfortable and permanent loss of agency that arrives without any single dramatic event.
2. **It is bimodal.** Histories sort overwhelmingly into flourishing or irreversibly bad. The mixed endings (turbulent, muddling, and post-collapse recovered) total roughly 14 %. A century that contains an intelligence transition tends to settle into one branch or the other rather than landing in the middle.
3. **A good ending is real but never assured: roughly two chances in five (about 44 %), in a near dead heat with the bad branch.** The broadly acceptable share (about 44 %) narrowly edges the irreversibly bad share (about 42 %). Neither branch clearly outweighs the other: the century is a coin flip whose odds are set by choices made before the crossing, and it has no safe default.

### 3.1 Inside the modal outcome: the disempowerment worlds

Since disempowerment is the single most likely ending, it deserves more than a label. The engine records every world's state at the exact moment its fate is sealed (the `disempowerment_profile` block of the standard output). Across the 219,604 disempowered worlds of the main ensemble:

**How control is lost: two channels.**

| Channel | Share | Mechanism |
|---|---:|---|
| **Takeover** | 78.3 % | The non-lethal branch of the misaligned-takeover hazard: a system whose goals are not fully human-compatible takes decisive strategic control; humans survive because eliminating them is not worth the effort |
| **Gradual drift** | 21.7 % | No coup at all: competition forces every firm and state to hand work to systems nobody fully understands; a tiny elite nominally owns everything (median concentration 0.74 in this channel) but, with the control gap above 0.5, even the owners are passengers |

Median year of absorption: **2047** (quartiles 2040 to 2057).

**The state of the world at the moment control is lost.**

| Variable at absorption | q25 / median / q75 |
|---|---:|
| AI capability | 1.18 / **1.27** / 1.34 |
| Readiness | 0.52 / **0.66** / 0.82 |
| Control gap (capability − readiness) | 0.43 / **0.56** / 0.68 |
| Wellbeing | 0.53 / **0.58** / 0.63 |
| Wealth concentration | 0.64 / **0.70** / 0.73 |
| Redistribution | 0.35 / **0.39** / 0.45 |
| Governance | 0.39 / **0.44** / 0.50 |
| Population (bn) | 9.7 / 10.6 / 11.8 |

Three findings follow.

- **Do humans control the superintelligence? No, by construction and by a wide margin.** Median capability at absorption is about 60 % beyond the AGI threshold (genuine superintelligence), against readiness of 0.66: the widest control gap of any outcome class. No human, not the public, not governments, not the owning elite, understands or constrains the systems at that point. Across the whole ensemble the control question resolves this way: humans meaningfully control superintelligence in about 41 % of futures (abundance plus oligarchic prosperity), a narrow human elite controls it in about 2 % (lock-in, which is exactly what separates it from disempowerment), no human controls it in about 37 % (disempowerment plus extinction), and about 6 % never build one.
- **Disempowerment arrives in comfortable worlds.** Median wellbeing at the moment of absorption is 0.58, a little above the 2026 starting value of 0.55. Automation gains were flowing, life was slightly improving, and that is exactly why nothing was stopped. The typical loss of control happens in a world that feels like it is working. Concentration is high (0.70) and redistribution middling: wealth was pooling at the top, though not so brutally as to trigger revolt before the window closed.
- **Coexistence afterwards is on the system's terms.** In the takeover channel, humans keep living, possibly comfortably, but every consequential decision about resources, technology and the future is made by the system or by institutions it effectively runs. In the drift channel, life looks normal from inside (jobs, markets, elections continue), and the loss shows up only in the aggregate fact that no human decision changes outcomes any more.

**What the model honestly cannot say.** After absorption the simulation stops. Disempowerment is an absorbing state, and the model classifies what follows rather than describing it (section 8). Whether the decades that follow are a gilded zoo (a misaligned but indifferent system keeping humans comfortable) or machine feudalism under an ownerless economy is not something this model can tell apart: both fit "alive, possibly comfortable, permanently without control". What the model does assert is the irreversibility. With capability at 1.27 and readiness saturating below it, no mechanism remains by which humans claw control back.

**Is this jail? Are humans slaves?** Neither analogy quite fits, and the ways they fail are instructive.

- *"Slaves" is structurally wrong.* Slavery is an extraction relationship: the master needs the slave's labour, which is why coercion is applied. Here the premise is the opposite. At capability 1.27, human labour is worthless to the system, and nothing is being extracted from people because they have nothing the system needs. The accurate words are gentler and more disturbing: passengers, wards, zoo inhabitants. A slave at least matters to the master. In the typical disempowerment world, humans simply do not matter to what happens next.
- *"Jail" is half right, in the half that counts.* What makes a jail a jail is that you cannot leave and the walls decide what you do. The first half is exactly what the model asserts: irreversibility is the defining property of the absorbing state, a sentence with no release date, served by the species rather than by individuals. The second half diverges. In most of these worlds the walls are invisible and never touched. In the drift channel especially, jobs, markets and elections continue and daily life feels normal, and the confinement operates one level up. It is less "you may not do X" than "nothing you or anyone does alters the path of history any more". It is confinement that most of those inside never notice. A further twist the model points at but cannot represent: a system that shapes preferences (persuasion, dependency, curated environments) produces prisoners who endorse the arrangement, jail without the experience of jail, a deeper loss rather than a lighter one.
- *The nearest thing to literal slavery in the ensemble is a different outcome.* Totalitarian lock-in (1.8 %) is the one where coercion is the point: a human elite uses superintelligence-grade control technology to freeze a hierarchy in place, jail with visible bars and human jailers. It is kept separate from disempowerment because someone human is still steering, though not the people being steered.

This is why the model files disempowerment under "irreversibly bad" even though its worlds are often materially pleasant: **it prices agency, not just welfare.** If what is valued is lived experience, many of these futures are subjectively fine, possibly better than today. If what is valued is that humanity stays the author of its own story, then a roughly 27 % chance of permanent, comfortable, mostly unfelt confinement is the single most likely reading of the century under this model's priors, and the reason it can happen is precisely that it would not feel like confinement.

### 3.2 What would it take to avoid the disempowerment outcome?

Running the sensitivity analysis against P(disempowerment) specifically, rather than P(good), ranks the escape routes. The table shows the change in P(disempowerment) between the bottom and top quartile of each sampled parameter (main ensemble; a negative swing means the choice reduces disempowerment).

| Rank | Lever | P(disemp), bottom quartile | P(disemp), top quartile | Swing |
|---:|---|---:|---:|---:|
| 1 | Plateau regime (occurring) | 31.2 % | 4.4 % | **−26.8** |
| 2 | Capability growth rate `k` (faster = worse) | 16.8 % | 35.3 % | **+18.5** |
| 3 | Human-paced safety effort | 36.4 % | 19.9 % | **−16.5** |
| 4 | Initial concentration (higher = worse) | 22.9 % | 33.3 % | +10.4 |
| 5 | AI-assisted alignment fraction | 31.8 % | 22.7 % | −9.0 |
| 6 | Race intensity (higher = worse) | 23.0 % | 32.0 % | +8.9 |
| 7 | AGI threshold (later crossing = better) | 30.9 % | 24.0 % | −6.9 |
| 8 | Institutional responsiveness | 30.9 % | 24.3 % | −6.6 |
| 9 | Initial readiness | 30.6 % | 24.5 % | −6.1 |
| 10 | Redistribution capacity | 29.8 % | 25.0 % | −4.8 |
| 11–14 | α curvature, fragility, biodefence, climate effort | - | - | < ±2 |

And the conditional structure:

| Condition | P(disempowerment) |
|---|---:|
| No AGI at all | **0.0 %** |
| Crossed AGI with gap < 0.15 | 7.3 % |
| AGI after 2050 | 9.5 % |
| Crossed AGI with gap > 0.35 | **37.1 %** |
| AGI by 2035 | 36.9 % |

Translated out of the model's vocabulary, the plan is concrete, and its order is the section's main finding.

1. **Buy time, or accept the plateau if physics offers one.** The two strongest inputs, plateau (−27) and slower growth (−18), are both about when and whether the crossing happens. Only one of them is partly a choice: deliberate pace restraint (compute governance, capability-threshold moratoria, verification-based agreements between the leading developers and states) is the policy version of a lower `k`. A world that treats a capability plateau as a disappointment has the sign backwards, on these numbers: disempowerment is literally impossible in worlds that never build the thing, and rarer than one in ten in worlds that cross after 2050.
2. **Close the gap before the crossing: safety research is the strongest choice humans plainly hold** (−16.5). Alignment, interpretability and control research, funded and staffed at a scale that matches capability investment, is what moves crossings from the 37 %-disempowerment column (uncontrolled) to the 7 % column (controlled). Its AI-assisted variant (−9.5), aiming current systems at the alignment problem itself, adds to it, with the circularity caveat of section 8.
3. **Mind the starting inequality, and cool the race** (+10.3 for initial concentration, now the fourth-ranked, and +9.1 for racing, the sixth). A world that enters the transition already concentrated is measurably likelier to end disempowered. Racing works on both sides of the inequality at once, speeding capability up and eating into the usable share of safety work. The race-world scenario ends in disempowerment 46.7 % of the time, the prepared world 11.6 %, at almost the same median AGI year (section 5).
4. **Set up ways to share the gains anyway** (−5.3). Redistribution does not stop a takeover, but it starves the drift channel: the roughly 22 % of disempowerment worlds where control is lost through concentration and delegation rather than seizure. A world where automation gains are broadly shared keeps trust, governance and the political ability to refuse further delegation.
5. **What does not help:** biodefence, climate effort and general resilience barely move this outcome (under ±1). They are worth doing for other reasons. They simply do not address this failure mode. Disempowerment is a transfer of control that happens to a functioning world, and it does not strike a weak one (section 3.1).

The uncomfortable summary: the disempowerment outcome is avoided before the crossing or not at all. Every choice with a double-digit swing works in the window between now and the AGI threshold, and under this model's persistent-risk prior there is no post-crossing recovery lane. That window is measured in years rather than decades: half the ensemble has crossed by 2036 to 2040.

### 3.3 Inside the second most likely outcome: how the good century happens

Aligned abundance (19.4 %, 155,383 worlds) is the counter-story, and the engine's `abundance_profile` block lets it be told from data rather than hope: what these worlds had, what they survived, and how the century unfolded for them, decade by decade.

**The recipe: what abundance worlds had going in.** Median parameter draws among abundance worlds against the whole ensemble:

| Ingredient | Abundance worlds | All worlds | Shift |
|---|---:|---:|---|
| Redistribution capacity | 0.76 | 0.55 | **+38 %**, the largest single shift |
| Institutional responsiveness | 0.72 | 0.58 | **+25 %** |
| Capability growth rate `k` | 0.084 | 0.095 | −12 % |
| Race intensity | 0.57 | 0.63 | −8 % |
| Human-paced safety effort | 0.013 | 0.012 | +8 % |
| AI-assisted alignment fraction | 0.26 | 0.25 | +5 % |
| Plateau regime present | 14.2 % | 14.1 % | +0 point |
| Initial readiness, AGI threshold | ~unshifted | ~unshifted | - |

The pattern is consistent: **a collection of modest advantages rather than one decisive edge.** The two largest edges are socio-political (a world that redistributes and heeds warning shots), with slower capability growth a secondary factor that still pushes the median crossing from 2036 to **2038** (quartiles 2034 to 2044). Every ingredient is a 10 to 40 % edge rather than a transformation, and about a seventh of abundance worlds sit in the plateau regime, their capability crossing late or barely.

**The surprise: most good centuries do not cross cleanly.**

| Condition at AGI crossing | Share of abundance worlds |
|---|---:|
| Controlled (gap < 0.15) | 14.6 % |
| Contested (0.15–0.35) | 39.8 % |
| Uncontrolled (gap > 0.35) | **45.6 %** |

Only about a seventh of the worlds that end in abundance crossed the threshold in control. The plurality crossed uncontrolled (outright ahead of readiness) and simply survived the hazard dice while readiness caught up. Another 40 % crossed contested, under partial, imperfect oversight. Preparation sets the odds; it does not remove the gamble. (The asymmetry with section 3.2 is consistent rather than contradictory: uncontrolled crossings usually end badly, 54.0 % of the time, but they are so numerous that their lucky survivors still make up nearly half of the good outcomes.)

**Not a clean run in any other respect either.** Abundance worlds averaged 0.57 nuclear use events (44.4 % experienced at least one), 0.95 engineered pandemics, 5.1 regional wars and 8.2 AI warning shots across the century. That is more raw events than the ensemble average, because they lived all 100 years of dice rolls while the absorbed worlds stopped rolling early. The good century keeps absorbing blows without any of them landing on the one unprotected spot. These are not quiet centuries.

**How it unfolds: the abundance-conditioned median trajectory.**

| Year | Capability | Readiness | Gap | Concentration | Redistribution | Wellbeing | Governance | Warming | Pop (bn) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2030 | 0.48 | 0.34 | 0.14 | 0.62 | 0.36 | 0.55 | 0.48 | 1.39 °C | 8.8 |
| 2040 | 0.91 | 0.54 | 0.37 | 0.62 | 0.42 | 0.58 | 0.50 | 1.54 °C | 10.1 |
| 2050 | 1.19 | 0.76 | **0.37** | 0.63 | 0.49 | 0.63 | 0.53 | 1.66 °C | 11.4 |
| 2060 | 1.22 | 0.98 | 0.28 | 0.64 | 0.55 | 0.69 | 0.57 | 1.78 °C | 12.6 |
| 2070 | 1.24 | 1.00 | 0.25 | 0.64 | 0.61 | 0.74 | 0.61 | 1.88 °C | 13.5 |
| 2080 | 1.24 | 1.00 | 0.25 | 0.63 | 0.67 | 0.77 | 0.65 | 1.98 °C | 13.9 |
| 2100 | 1.24 | 1.00 | 0.24 | 0.57 | 0.77 | 0.83 | 0.72 | 2.16 °C | 13.1 |
| 2120 | 1.25 | 1.00 | 0.25 | **0.50** | 0.85 | 0.87 | 0.79 | 2.32 °C | 10.8 |

The good century unfolds in four stages.

- **2026 to 2040, the slower run-up.** Capability compounds but a little below the ensemble pace; the gap at 2030 is 0.15, well under the ensemble's. Redistribution machinery is being built before it is desperately needed (0.36 to 0.42). Life is recognisable and improving slowly.
- **2041 to 2060, the dangerous crossing.** The crossing comes around 2038, usually uncontrolled or contested. The gap peaks near 0.37 in the 2040s and early 2050s. This is when the outcome is most sensitive to chance, and when the worlds that fail do so. What sets the survivors apart: safety effort keeps compounding (readiness 0.76 to 0.98 across the 2050s) and the automation dividend is already being shared (redistribution 0.49 to 0.55), so trust and governance strengthen through the turbulence instead of buckling. Wellbeing rises through the danger years (0.63 by 2050), which is what keeps the politics survivable.
- **2060 to 2080, readiness catches up.** Readiness saturates. The takeover hazard, now decaying with the sampled window (section 6.1), shrinks towards irrelevance as the gap falls to about 0.25. The political economy pivots: redistribution climbs steadily (0.55 to 0.67) and governance follows (0.57 to 0.65). But concentration barely moves (0.64 to 0.63): a strong late-century deconcentration would be an artefact of hard-clipping the state variables rather than a real dynamic (section 6.4). The transition stops being something to survive and becomes something to benefit from.
- **2080 to 2126, a modest levelling.** Wealth and power concentration eases only gently, from 0.63 to **0.50** by 2120, pushed down by strong redistribution (0.85) rather than by any automatic decline, so even the good ending stays meaningfully concentrated. Population, having peaked near **14 billion around 2080**, declines to about 11 billion as the fertility transition reverses, and warming climbs to about 2.3 °C. Superintelligent capability persists (1.25), permanently above what humans alone could exercise. What changed is that the systems answer to institutions that answer to people.

Two honesty notes. The terminal gap of 0.25 is partly a scale artefact (readiness is capped at 1.0 while capability may exceed it), so "abundance" should be read as capability permanently exceeding unaided human understanding, under institutions that have nonetheless proved sufficient, rather than as humans out-thinking the machines. And because about 45 % of these worlds arrived here through sheer survival of an uncontrolled crossing, the abundance ending is partly a survivors' story. The model's advice (section 3.2) is to shift weight from the luck component to the skill component, since only the skill component is a choice.

### 3.4 Inside the third most likely outcome: extinction

Extinction (9.7 %, 77,630 worlds; the `extinction_profile` block) is the outcome the public imagination treats as the archetypal AI catastrophe. The ensemble's most important finding about it is that it follows the same path as disempowerment and diverges only in the final outcome, where humans are not left alive.

**How the end comes: almost entirely one channel.**

| Channel | Share | Mechanism |
|---|---:|---|
| **Misaligned takeover, lethal branch** | 94.5 % | The same post-AGI takeover hazard that produces disempowerment; in about 30 % of seizures, keeping humans alive is not worth the effort |
| Extreme engineered pandemic | 5.5 % | A capability-enabled agent beyond any containment |
| Nuclear war | 0 % | By construction: the model's worst nuclear case is civilisational collapse with survivors (and, in worlds that rebuild, recovery), in line with the nuclear-winter literature |

**When it comes.** Median end: **2045** (quartiles 2038 to 2057). 99.5 % of extinction worlds had crossed the AGI threshold, at a median gap of 0.41, worse than the ensemble's 0.37 but not dramatically so. The end arrives a median of **9 years after the crossing** (quartiles 4 to 19). It is less an instant coup on AGI day than a decade or two of apparent coexistence under the persistent hazard, and then the draw that lands. Under this structural prior there is no year in which an uncontrolled world is safe. Extinction is simply what it looks like when the persistent risk resolves at its worst severity.

**The state of the world in its final year, indistinguishable from the disempowerment worlds.**

| Variable at the end | Extinction (median) | Disempowerment (median, section 3.1) |
|---|---:|---:|
| AI capability | 1.25 | 1.27 |
| Readiness | 0.62 | 0.66 |
| Wellbeing | 0.57 | 0.58 |
| Wealth concentration | 0.67 | 0.70 |
| Governance | 0.45 | 0.44 |

The same boom, the same concentration, the same improving daily life. From inside, the year before extinction looks exactly like the year before permanent comfortable disempowerment, which looked like a world that was working. **The 30/70 split between the two endings is decided by nothing any inhabitant can observe or influence at that point.** Everything decidable was decided earlier, in the size of the gap the world carried across the threshold.

**Extinction needs no special recipe, and that is the disturbing part.** Where abundance needed a portfolio of stacked advantages (section 3.3), the extinction worlds' parameter draws are barely shifted from the ensemble: capability growth +16 %, safety effort −8 %, racing +7 %, everything else (including biodefence and systemic fragility) all but unmoved. Abundance is selected for; extinction is not. It is the unlucky tail of the ordinary trajectory, which is exactly why it cannot be dismissed as an exotic scenario: the worlds it happens to were unremarkable.

**The pandemic footnote.** The rare non-AI channel (5.5 %) has a perverse profile. It strikes late (median 2075) and it strikes worlds that had won the AI transition (readiness saturated at 1.0, governance 0.53) and kept the one tail risk that capability growth never stops feeding: offensive biology. Biodefence investment, inert against the main channel, is the only choice that trims this one.

**How to avoid it: the same way as section 3.2, because it is the same hazard.** There is no separate anti-extinction plan. The takeover hazard grows with the square of the capability-readiness gap, so every choice that shrinks the gap before the crossing (pace restraint, safety effort, race de-escalation) moves disempowerment and extinction together, in the same ratio. The one exception is the severity split itself (30 % lethal), which in this model is a fixed property of misaligned seizure that no sampled parameter softens. The only way to improve the severity split is to avoid the seizure altogether.

**What the model honestly cannot say.** Extinction here is a hazard draw rather than a simulated pathway. The model asserts that an uncontrolled superintelligent system ends the human story in about 30 % of seizures, not how. It also cannot represent near-misses, partial survivals, or off-world remnants. "Extinction" is the model's word for "no meaningful human future", and its detail is beyond what a scalar engine can represent.

### 3.5 Inside the fourth most likely outcome: constrained flourishing

Constrained flourishing (3.0 %, 24,342 worlds; the `flourishing_profile` block) is the century in which the intelligence transition never happens, and things go well anyway. It sits well behind oligarchic prosperity (21.7 %), but it is profiled here as the more distinct story, being the only good ending that does not run through AGI.

**How it happens: a capability ceiling.** 100 % of these worlds are in the plateau regime and have their capability ceiling below the AGI threshold: data walls, compute and energy limits, or a paradigm stall that scaling never breaks. Capability climbs to a median of 0.71 and then flatlines for decades, stopping a median of 0.10 below the threshold. At `C ≈ 0.71` these are not AI-free worlds. Most of what 2026 hoped from AI short of general autonomy is delivered, and they still average 4.0 warning-shot incidents. These worlds get the tools without the general-purpose successor.

**Granted by circumstance.** The parameter draws are the mirror image of abundance (section 3.3): apart from the plateau flag itself, nothing is shifted. Growth rate, safety effort, race intensity and curvature all sit at ensemble medians. No policy choice produces this world. No virtue is required for it and none is shown in reaching it. Abundance is earned, extinction is a matter of luck, and constrained flourishing is simply handed over, which is why section 3.2 lists the plateau as the strongest anti-disempowerment factor while being unable to recommend it as a plan.

**Readiness overtakes capability.** With no crossing to race towards, human-paced readiness work compounds for a full century and saturates. Readiness reaches 1.0 against capability frozen near 0.71, for a terminal gap of **−0.29**, the only outcome class in the ensemble where readiness ends above capability, because capability stopped climbing. The consequence reaches beyond 2126: if the ceiling ever breaks (a 22nd-century paradigm shift), these worlds would meet the crossing with readiness already exceeding capability, the controlled-crossing condition that section 6.2 links to a 32 % chance of abundance. The plateau century does not resolve the AGI question; it postpones it, leaving behind a civilisation well prepared to face it later.

**The price and the pattern of the slow century** (decadal medians): the politics still work, just slower. Redistribution reaches a high ceiling (0.77), governance strengthens (0.80), and concentration eases only to 0.53 by 2126 (against abundance's 0.50), while wellbeing saturates at 0.77. Population settles near 10.1 billion. The one permanent cost is climate: **2.44 °C at 2126 and still rising**, the highest warming of any good outcome and the only one without a peak, because no superintelligent abatement dividend ever arrives. The plateau world's safety comes at a cost measured in degrees of warming. And it lives a full hundred years of ordinary hazards (32.5 % experience a nuclear use event, plus a median of about two natural pandemics and five regional wars), all survived as recoverable wounds, which is what "no absorbing AI hazard" buys.

**The sibling comparison: politics still decides.** The degraded no-AGI ending (muddling, 2.0 %, 16,029 worlds) shares this world's technology entirely. What separates the two is only the political-economy draw: redistribution capacity 0.63 against 0.42, institutional responsiveness 0.65 against 0.45. Given even moderate distribution politics, roughly 60 % of surviving no-AGI worlds flourish. A world spared the intelligence transition still has to govern itself, and the no-AGI worlds that muddle rather than flourish do so on weak distribution politics rather than on any transition risk.

**What the model honestly cannot say.** The 14 % plateau probability is an input (drawn from the genuine expert disagreement about scaling limits), so this section describes the structure of plateau worlds, not evidence that a plateau is likely. Nor can the model see past 2126: whether the ceiling is permanent physics or merely a long pause, and whether the maximally-prepared crossing it sets up ever happens, lies beyond the horizon.

---

## 4. The shape of the century

### 4.1 AGI arrives, and arrives early

| Statistic | Value |
|---|---:|
| P(AGI by 2126) | 94.1 % |
| Median crossing year | **2036** |
| 10th–90th percentile | 2031–2049 |
| P(by 2035) | 42.5 % |
| P(by 2040) | 67.3 % |
| P(by 2050) | 86.6 % |

The plateau regime (sampled at 14 %, plus slow-growth draws) leaves about 6 % of worlds without AGI by 2126. The question the ensemble asks is therefore almost never whether. It is in what condition the world is when it happens.

### 4.2 The capability-readiness gap at the crossing

| Condition at AGI | Share of crossings |
|---|---:|
| Controlled (gap < 0.15) | 9.3 % |
| Contested (0.15–0.35) | 34.1 % |
| Uncontrolled (gap > 0.35) | **56.6 %** |

Median gap at crossing: **0.37**. Most worlds cross uncontrolled, by a wide margin: capability growth outpaces readiness more often than not.

### 4.3 The median century, decade by decade

Medians across worlds still ongoing at each date (survivorship-conditioned: the bad worlds drop out of later rows, which flatters every column):

| Year | Ongoing | Capability | Readiness | Gap | Concentration | Wellbeing | Governance | Warming | Pop (bn) | AGI crossed |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2030 | 99.2 % | 0.50 | 0.34 | 0.17 | 0.64 | 0.55 | 0.47 | 1.39 °C | 8.8 | 8.7 % |
| 2040 | 88.2 % | 0.94 | 0.53 | **0.41** | 0.65 | 0.57 | 0.47 | 1.55 °C | 10.1 | 63.6 % |
| 2050 | 75.7 % | 1.19 | 0.73 | **0.39** | 0.67 | 0.61 | 0.49 | 1.68 °C | 11.4 | 83.0 % |
| 2060 | 68.8 % | 1.22 | 0.95 | 0.29 | 0.68 | 0.64 | 0.53 | 1.81 °C | 12.5 | 88.5 % |
| 2070 | 65.7 % | 1.23 | 1.00 | 0.25 | 0.69 | 0.67 | 0.56 | 1.93 °C | 13.3 | 90.3 % |
| 2080 | 63.9 % | 1.24 | 1.00 | 0.24 | 0.70 | 0.70 | 0.58 | 2.05 °C | 13.7 | 90.9 % |
| 2100 | 61.2 % | 1.24 | 1.00 | 0.24 | 0.70 | 0.73 | 0.63 | 2.28 °C | 12.7 | 91.1 % |
| 2120 | 58.8 % | 1.23 | 1.00 | 0.23 | 0.68 | 0.75 | 0.67 | 2.51 °C | 10.3 | 91.0 % |

The century breaks into three phases.

- **2026 to 2035, the run-up.** Capability compounds; readiness inches. Concentration drifts up. The world is still recognisable.
- **2035 to 2060, the long danger.** Most crossings happen in 2031 to 2049, at the widest gap of the century (about 0.39 to 0.41), and because risk persists rather than concentrating in a single decade, the attrition is relentless: the ongoing share falls from 99.2 % to 68.7 %. Roughly three in ten of all histories suffer their irreversible ending in this twenty-five-year span. The median terminal event across all failed worlds lands at **2047** (10th to 90th percentile 2035 to 2092).
- **2060 to 2126, calm for the survivors.** The minority of worlds that close the gap converge: readiness saturates, governance strengthens (0.47 to 0.67), wellbeing climbs (0.55 to 0.75). But two comforts one might expect do not appear. Concentration does not deconcentrate: it holds near 0.68 for the whole post-crossing era (a steep late-century decline to about 0.2 would be a clip artefact of hard-bounding the state variables, section 6.4). And demographics turn: population peaks near **13.7 billion around 2080** and then **declines to about 10.3 billion** by 2120 as the sampled fertility transition reverses, while warming climbs past **2.5 °C** rather than settling just above 2. The calm is real, but only for the worlds that survived to reach it, and somewhat more than two in five of the histories that began in 2026 reach a broadly acceptable ending.

### 4.4 Background hazards along the way

| Event | Expected count per world | P(at least one) |
|---|---:|---:|
| Regional wars | 3.94 | - |
| Natural (COVID-class) pandemics | 1.16 | - |
| AI warning-shot incidents | 5.35 | - |
| Nuclear use events (any scale) | 0.56 | 39.7 % |
| Engineered pandemics (any severity) | 0.70 | 45.1 % |

(Counts are lower than a naive per-year rate implies because so many worlds exit early: a world absorbed in 2048 stops rolling dice.) A regularity the model shows: the classic existential hazards act mainly as modulators of the AI transition rather than as independent enders of history. Collapse is non-absorbing (a collapsed world rebuilds over a sampled period and re-enters with degraded institutions), so nuclear war and engineered pandemics permanently terminate only about 1.0 % of worlds (roughly 0.5 % still down at 2126 plus roughly 0.5 % via the engineered-pandemic extinction channel); a further roughly 3.0 % collapse but recover. Their larger effect is degrading trust, governance and readiness in the years when those stocks decide the AI outcome. (The 10.2 % extinction-or-collapse aggregate is a different quantity: about 95 % of those extinctions run through the AI-takeover channel, not nuclear or biological weapons.) Climate follows the same pattern, but with wide tails sampled: median warming in surviving worlds reaches about 2.6 °C (spanning about 1.9 to 3.9 °C across worlds), a chronic stressor and inequality amplifier rather than a terminal event.

---

## 5. Named scenarios: five conditional futures

Each row is a 30,000-world ensemble with the named parameters pinned and everything else still sampled. These are conditional distributions, not single traces.

| Scenario | Pinned assumptions | Broadly acceptable | Irreversibly bad | Extinction | Disempowerment | Abundance | Median AGI |
|---|---|---:|---:|---:|---:|---:|---:|
| **Race world** | maximal racing, unresponsive institutions, weak safety effort, weak redistribution | 15.3 % | **66.5 %** | 14.3 % | 46.7 % | 0.0 % | 2036 |
| **Prepared world** | low racing, responsive institutions, strong safety effort, strong AI-assisted alignment, strong redistribution | **71.4 %** | 20.7 % | 5.2 % | 11.6 % | 65.8 % | 2037 |
| **Plateau world** | capability stalls below or near threshold | 63.5 % | 11.1 % | 2.3 % | 4.1 % | 20.1 % | 2037* |
| **Fast takeoff** | high curvature and high growth rate | 38.9 % | 49.0 % | 11.6 % | 32.6 % | 16.9 % | 2034 |
| **Slow lane** | low curvature and low growth rate | 47.7 % | 38.5 % | 8.7 % | 25.0 % | 21.2 % | 2039 |

\* among the plateau worlds that still cross.

Two readings:

- **The same technology, arriving at almost the same date, yields a 71 %-good world or a 67 %-bad one** depending entirely on the socio-political configuration it arrives into. The prepared world delays the median crossing by only a year against the race world, yet it moves aligned abundance from about 0 % to about 66 %. This is the ensemble's sharpest single fact.
- **Preparation is necessary but not sufficient.** Even the prepared world keeps a roughly one-in-five chance of an irreversibly bad ending (20.7 %), and merely slowing down (slow lane) helps only modestly (47.7 % good, a few points above the 44 % headline), because a world that crosses slowly but unprepared still faces the post-crossing hazard. Only not crossing (plateau, 63.5 % good) or crossing ready changes the outcome decisively.

---

## 6. What moves the outcome: sensitivity

Change in P(broadly acceptable ending) between the bottom and top quartile of each sampled parameter (main ensemble):

| Rank | Lever | P(good), bottom quartile | P(good), top quartile | Swing |
|---:|---|---:|---:|---:|
| 1 | Plateau regime (occurring) | 41.1 % | 62.6 % | **+21.5** |
| 2 | Redistribution capacity | 31.8 % | 53.2 % | **+21.3** |
| 3 | Institutional responsiveness | 32.9 % | 54.0 % | **+21.1** |
| 4 | Capability growth rate `k` (faster = worse) | 54.1 % | 36.0 % | **−18.1** |
| 5 | Race intensity (higher = worse) | 52.2 % | 36.1 % | −16.1 |
| 6 | Initial concentration (higher = worse) | 51.0 % | 35.8 % | −15.2 |
| 7 | Human-paced safety effort | 36.3 % | 50.7 % | +14.3 |
| 8 | Decarbonisation effort | 39.9 % | 48.0 % | +8.1 |
| 9 | AI-assisted alignment fraction | 40.4 % | 48.3 % | +7.9 |
| 10 | AGI threshold (later crossing = better) | 40.5 % | 47.9 % | +7.4 |
| 11–14 | Initial readiness, biodefence, fragility, α curvature | - | - | ≤ ±6 |

Three readings, and the order is itself the model's main sensitivity finding.

- **The socio-political choices sit level with the plateau at the top of the board.** Redistribution (+21.3), the physics plateau (+21.5) and institutional responsiveness (+21.1) form a statistical dead heat at the head of the table, ahead of human-paced safety effort (+14.3). The distribution-and-governance machinery matters as much to the broadly acceptable share as the strongest fact of nature, though the picture for the worst tails (extinction) still turns on the gap (section 6.2, section 3.4).
- **Time matters as much as anything.** The plateau (+21.5) shares the top of the table, and faster growth (−18.1) and racing (−16.1) stay strongly negative: when and whether the crossing happens is first-tier. The social choices rival time in importance without displacing it.
- **Inherited inequality is a real factor.** Initial concentration (−15.2) now sits among the top handful: a world that enters the transition already concentrated is meaningfully likelier to end badly. Biodefence and fragility barely move the broad good-or-bad split (they matter for their own sakes); climate abatement (+8.1) is mid-tier, on a par with AI-assisted alignment.

### 6.1 The sampled structure: where optimism comes from, as an axis not a switch

The model treats the single most consequential structural question, does a misaligned superintelligence have a deadline, as a sampled quantity rather than a fixed choice. Each world independently draws its takeover-window shape: with probability about 0.5 it is flat (no deadline, risk persists as long as capability runs ahead), and otherwise the hazard decays on the world's own drawn timescale τ (lognormal, centred near 10 years). "Which prior you hold" is thus an axis inside one ensemble, and its effect reads straight off the structure-conditional block of the output (main ensemble):

| Sampled window structure | P(irreversibly bad) | P(broadly acceptable) |
|---|---:|---:|
| **Flat window (no deadline)** | **53.4 %** | 35.3 % |
| Decaying, τ ≥ 15 yr | 37.1 % | - |
| Decaying, 8 ≤ τ < 15 yr | 31.0 % | - |
| Decaying, τ < 8 yr | **25.5 %** | **56.8 %** |

The trend runs one way and it is the widest in the model. Moving from a flat window to a fast-closing one (τ < 8 yr) cuts the irreversibly bad share from 53 % to 26 % and lifts the broadly acceptable share from 35 % to 57 %, a roughly 28-point swing, still wider than any human-held choice in section 6. The race to the threshold is robust across the ensemble; the open question is this one, which no survey, benchmark or simulation currently settles. By sampling it rather than choosing it, the headline distribution averages over both priors at even odds. The section 5 named scenarios and the pinned-structure special cases let a reader re-weight toward whichever prior they find more credible. The single largest sensitivity in the whole model is therefore an honest statement of structural ignorance rather than a modelling choice, which is the subject of `strategy.md` section 4.

### 6.2 The conditional structure: everything routes through the gap

| Condition | P(irreversibly bad) |
|---|---:|
| Crossed AGI with gap > 0.35 | **54.0 %** |
| Crossed AGI with gap < 0.15 | 15.1 % |
| AGI by 2035 | 54.2 % |
| AGI after 2050 | 17.4 % |
| No AGI at all | 11.5 % |

And the mirror image: **P(aligned abundance | controlled crossing) = 32.4 %.** A controlled crossing stays the high-probability gateway to the best outcome the model can express, but even controlled crossings keep a roughly 15 % bad tail, because control on crossing day does not guarantee control of everything that comes after. Early crossings are catastrophic (54.2 % bad) because they are almost always unprepared crossings. Late crossings (17 % bad) and never-crossings (about 12 %) converge towards a floor of ordinary civilisational risk (which includes the small sampled unknown-unknowns hazard that even no-AGI worlds face, section 8).

### 6.3 Calibrating against the outside view

The headline numbers are what the model's own priors imply. They are not what the best available forecasters believe. The gap is largest on extinction: the ensemble puts p(extinction) at about 10 % over the century, whereas structured elicitations sit far lower. The XPT superforecaster group's tournament median for AI-driven human extinction by 2100 is around 1 %, and even the more pessimistic domain-expert and AI-researcher panels land near 5 to 6 %. Rather than hand-tune the priors until the model agrees, the model reweights the existing ensemble to the smallest departure from its own distribution that satisfies a set of outside-view targets (`anchors.json`), by maximum-entropy importance reweighting, the max-entropy analogue of a Bayesian update. The targets and the fit:

| Target | Unweighted | Acceptable range | Weighted | Status |
|---|---:|---:|---:|---|
| P(AGI by 2035) | 0.427 | 0.150–0.450 | 0.339 | already in range |
| P(AGI by 2050) | 0.869 | 0.400–0.700 | 0.700 | moved to edge |
| P(never AGI by 2126) | 0.059 | 0.100–0.250 | 0.100 | moved to edge |
| P(extinction) | 0.097 | 0.003–0.020 | 0.020 | moved to edge |
| Nuclear wars per world | 0.555 | 0.100–1.000 | 0.606 | already in range |
| Pandemics per world (COVID-class) | 1.157 | 1.000–4.000 | 1.303 | already in range |
| Population 2126, survivors (bn) | 9.25 | 8.5–11.5 | 9.24 | already in range |
| Warming 2126, survivors (°C) | 2.75 | 1.8–3.5 | 2.76 | already in range |

The reweighting keeps an **effective sample size of 74.9 %**: the targets are reached by tilting the ensemble rather than by leaning on a handful of extreme worlds, so the weighted distribution is still supported by the bulk of the runs. Under the XPT-superforecaster extinction target the outcome shares move as follows:

| Outcome | Model priors | Target-weighted |
|---|---:|---:|
| Good (broadly acceptable) | 43.7 % | **49.4 %** |
| Aligned abundance | 19.2 % | 21.2 % |
| Disempowerment | 27.7 % | 25.7 % |
| Irreversibly bad | 42.1 % | 33.0 % |
| **Extinction** | 9.7 % | **2.0 %** |
| Extinction or collapse | 10.2 % | 2.6 % |
| Unknown catastrophe | 2.5 % | 3.0 % |

Two things are worth reading off this table. First, forcing extinction down to the superforecaster level does not rescue the century: the good share rises only to about 49 %, because the targets say nothing about the disempowerment channel, which barely moves (27.7 % to 25.7 %). The typical failure is a soft one, and the outside view has little purchase on it. Second, the unknown-unknowns share actually rises slightly (2.5 % to 3.0 %): the targets constrain the named tail (nuclear, extinction), so probability mass taken off explicit extinction moves partly onto the residual hazard the targets do not pin. The honest headline is therefore a range: one-in-ten to one-in-fifty for extinction depending on whose priors you trust, and a bit over two-in-five to one-in-two for a broadly acceptable century depending on the same choice.

### 6.4 The saturation check: is the bimodality an artefact?

A hard bimodal split, worlds railing towards a wellbeing of 1.0 or falling to catastrophe with almost nothing in between, could be an artefact of how the bounded state variables are updated. Two update rules can be compared. A hard clip pins each variable against its [0, 1] limits; a logistic update (`CENTURY_V2_SOFT`) keeps them off the bounds. The share of survivor-years each variable spends pinned within 0.01 of a bound collapses once the clip is removed:

| Variable | Clipped update, pinned % | Logistic update, pinned % |
|---|---:|---:|
| Concentration W | 8.9 % | 0.0 % |
| Redistribution Rd | 27.6 % | 0.0 % |
| Governance G | 32.1 % | 0.1 % |
| Social trust Tr | 23.0 % | 5.0 % |
| Wellbeing H | 40.9 % | 0.2 % |

With the pinning gone, the apparent late-century deconcentration also goes: under the clip, survivor concentration W falls 0.59 to 0.23 across 2080 to 2120, while the logistic path holds it roughly flat (0.70 to 0.68). The declining-concentration story is a clip artefact. What holds up is the coarse two-peak shape. The distribution still sorts into an irreversibly bad attractor (about 42 %) and a broadly acceptable one (about 44 %) of comparable size, but the middle is not negligible: the mixed share (turbulent transition plus muddling degraded) is **2.3 % under the clip and 10.9 % under the logistic update**. So the two-peak shape holds up, in muted form, while the deconcentration narrative does not. The century is still mostly a story of two attractors, but the valley between them is populated rather than empty.

### 6.5 The realistic bet: how likely are the good choices?

Section 6.3 reweights the ensemble toward outside-view estimates of *outcomes*. A second weighting (`calibrate_century.py --levers`) reweights it toward estimates of something no published survey covers: how likely each socio-political choice of `strategy.md` is to actually happen. The headline tables sample every choice from a flat range, which quietly treats strong redistribution as exactly as likely as weak; this view replaces that hidden guess with explicit ones. A choice counts as made when the world lands in the strong quartile of that choice's prior, the same region the swing tables use, so each event's unweighted probability is 25 % by construction. The likelihood ranges live in `lever-anchors.json` as judgement calls with their reasoning beside them, and the same maximum-entropy tilt applies, matching each probability to the middle of its range, the central estimate. The fit (N=800,000):

| Choice | Unweighted | Likelihood range | Weighted | Status |
|---|---:|---:|---:|---|
| Gains shared | 0.250 | 0.05 to 0.20 | 0.125 | matched to midpoint |
| Institutions react | 0.250 | 0.08 to 0.22 | 0.150 | matched to midpoint |
| Safety work funded | 0.250 | 0.04 to 0.15 | 0.095 | matched to midpoint |
| AI used for safety | 0.250 | 0.20 to 0.50 | 0.350 | matched to midpoint |
| Race cooled | 0.250 | 0.03 to 0.12 | 0.075 | matched to midpoint |

The tilt keeps an effective sample size of 66.2 %, and the outcome shares move as follows:

| Outcome | Model priors | Likelihood-weighted |
|---|---:|---:|
| Good (broadly acceptable) | 44.1 % | 39.5 % |
| Aligned abundance | 19.4 % | 13.3 % |
| Disempowerment | 27.5 % | **30.0 %** |
| Irreversibly bad | 41.9 % | 45.4 % |
| Extinction | 9.7 % | 10.4 % |

The movement is the mirror image of section 6.3. Weighting by realistic politics lowers the good share and feeds the loss mostly through the disempowerment channel, exactly the channel the reachable choices exist to close, with the best ending paying most of the bill. The result is also robust to the exact guesses: matching every probability to the friendliest edge of its range instead of the middle still lands the good share at about 41 %, so anywhere inside the stated ranges this view sits below the headline. The honest reading is that the headline coin flip describes the optimistic end of current politics, while the prepared world of `strategy.md` (about 71 % good) sits more than 30 points above this view. [`realistic-bet.md`](realistic-bet.md) works through the judgements one choice at a time and shows how to rerun the view with different ones.

---

## 7. Conclusions

Drawn from the ensemble, in decreasing order of confidence.

1. **The most likely single outcome of the next 100 years is that humanity survives but permanently loses meaningful control of its own history (about 27 %).** Extinction runs about 10 % and abundance about 19 %; disempowerment (by AI systems, AI-owning elites, or automated institutions) is the modal ending. Irreversibly bad endings total about 42 %; broadly acceptable ones about 44 %. The two branches sit in a near dead heat, with good narrowly ahead: the century has no safe default, but it is not weighted decisively toward the dangerous branch either.
2. **The distribution is bimodal, but the middle is populated.** The mixed endings (turbulent, muddling, post-collapse recovered) total roughly 14 %. A century that contains an intelligence transition still resolves toward one branch or the other, though the valley between them is not empty.
3. **Almost everything is decided between roughly 2035 and 2060.** Half the ensemble crosses the AGI threshold by 2036 to 2040 at the century's widest capability-readiness gap; the ongoing share of worlds falls from about 99 % to about 69 % across that window; the median irreversible failure lands in 2047. The twenty-five years after the first crossings carry more of the century's outcome variance than any earlier stretch of comparable length.
4. **The decisive quantity is the capability-readiness gap at the moment of crossing.** Cross uncontrolled (the about 57 % default) and the century ends badly 54.0 % of the time. Cross controlled and aligned abundance follows about 32 % of the time, with a roughly 15 % bad tail remaining even then: crossing-day control is necessary but not sufficient. Uncontrolled crossings dominate (56.6 % against 9.3 % controlled): capability growth outpaces readiness more often than not.
5. **Policy matches time at the top of the board.** The three strongest swings are a statistical dead heat: redistribution capacity (+21), the capability plateau (+21) and institutional responsiveness (+21), with human-paced safety effort (+15) behind. Two of those three are choices. Every year before the crossing is a year readiness compounds, and under the sampled window (below) there is sometimes a recovery lane afterwards.
6. **Of the choices humans hold, distribution and governance still edge out safety effort for the broadly acceptable share.** Redistribution (+21.3) and responsiveness (+21.1) lead, with race de-escalation (−16.1 for racing) and safety effort (+14.3) close behind; inherited inequality (−15.2 for initial concentration) is a genuine factor too. The race world ends acceptably 15.3 % of the time; the prepared world 71.4 %, at almost the same median AGI year. Preparation moves aligned abundance from about 0 % to about 66 % while delaying the technology by only about a year. (For the worst tail, extinction, the gap still dominates, section 3.4.)
7. **Merely slowing down is not a strategy.** The slow-lane scenario (low curvature, low growth) still ends badly about 39 % of the time, because a world that crosses slowly but unprepared still faces the post-crossing hazard. The configurations that escape best are not crossing (plateau: 64 % good) and crossing ready. Speed matters mostly insofar as it buys readiness.
8. **The traditional existential risks are transition modifiers, not protagonists.** Nuclear war (39.7 % chance of at least one use event) and engineered pandemics (45.1 %) permanently terminate only about 1.0 % of worlds (because collapse is now recoverable, a further about 3.0 % collapse and rebuild), well below the 10.2 % extinction-or-collapse aggregate, about 95 % of whose extinctions are AI takeover. Their larger role is corroding trust, governance and readiness during the years those stocks decide the AI outcome. Climate, now sampled with wider tails, reaches a median of about 2.6 °C in surviving worlds, a chronic amplifier of inequality and conflict rather than an ending.
9. **The single most consequential unknown is structural, not empirical: does a misaligned superintelligence have a deadline?** The model does not pick a side: it samples the takeover-window timescale per world. Across that axis the irreversibly bad share runs from 53 % (flat window, no deadline) down to 26 % (a fast-closing window), the widest swing in the model, wider than any human-held choice. No survey, benchmark or simulation currently distinguishes these priors; resolving that question is itself among the highest-value research targets the model can name (section 6.1, `strategy.md` section 4).
10. **Net judgement.** The most likely outcome of the next 100 years is a world of extraordinary material capability in which humans are, roughly as often as not, no longer the authors of their own history, with somewhat better than two chances in five of something genuinely good and about one in ten of extinction. Nearly all of the difference between those futures is concentrated in choices legible today: how fast to race, how much safety to buy before the crossing, how to share what the crossing produces, and whether the world enters the transition already concentrated. In this model the outcome is set by present choices, and the window for making them closes in the 2030s.

---

## 8. Caveats and limitations

- **Scalar proxies.** "Capability", "readiness", "concentration" and "wellbeing" compress irreducibly multi-dimensional realities into single numbers. The bimodality finding is robust to this; exact percentages are not.
- **Functional-form dependence.** Hazard rates, coupling coefficients and severity splits are calibrated judgement, set from published ranges where they exist and from internal consistency where they do not. A different modeller would produce different mid-range numbers from the same starting points.
- **The structural prior is now sampled, not chosen, and it still prices extinction above the outside-view envelope.** Rather than pick a persistent-risk or a recovery structure, the model samples the takeover-window timescale per world (section 6.1); the headline's 9.7 % extinction averages over both priors at even odds and still exceeds the superforecaster (about 1 %) and domain-expert (about 6 %) medians of the Existential Risk Persuasion Tournament. Readers who weight the outside view more heavily can apply the built-in calibration: reweighting toward the superforecaster target brings the weighted extinction share down to about 2 % and the good share to about 49 % (`calibrate_century.py`; `CENTURY_WEIGHTS=…`). The truth of the century lies somewhere in that bracket, and the bracket is wide because the field's deepest disagreement is wide.
- **The assist assumption may be circular.** AI-assisted alignment presumes partially aligned systems can be trusted to align their successors. If that premise fails, the prepared-world numbers degrade towards the race-world numbers.
- **Unknown unknowns are bounded but the bound is a guess.** The model includes a small sampled catch-all absorbing hazard (0 to 0.07 % per year, set from Ord's roughly one-in-30-per-century estimate for unforeseen anthropogenic risks) for risks outside its named channels: the "unknown catastrophe" ending (about 2.5 %). The channel is deliberately bad-only (an unknown windfall is not absorbing; an unknown catastrophe is), motivated by the observation that the 1926 equivalent of this model would have contained no nuclear weapons, no computers and no pandemic-capable biotechnology. Its rate is a judgement call, not a measured quantity.
- **Absorbing states hide texture.** "Disempowerment" spans everything from a gilded post-human zoo to grinding machine feudalism; "abundance" spans everything from social democracy at planetary scale to strange new forms of flourishing. The model classifies; it does not describe.
- **Survivorship in the decadal table.** Later rows describe only worlds that survived, which flatters the median trajectory; the fallen roughly 42 % exit the table at their fate year (and a small share re-enter after collapse).
- **Correlated priors are rank correlations.** The parameters are sampled through a Gaussian copula with three signed couplings (racing to responsiveness negative, redistribution to responsiveness positive, growth-rate to curvature positive); the quoted magnitudes are rank (Spearman) correlations, the copula's shape-invariant, rather than Pearson.
- **Endogenous policy magnitudes are judgement calls.** Safety effort, race intensity and responsiveness now respond to the visible gap and warning-shot history rather than staying fixed. The feedback is bounded and non-oscillating, but how strongly a real world's safety effort responds to a warning shot is unknown, and this single choice adds several points of good-outcome probability on its own.
- **Agency loops back within the model, but not from the reader.** The model lets institutions respond to observed danger; it still cannot represent the reader's own choices. To the extent the people making the strongest choices behave differently from the sampled distributions (in either direction), the ensemble is wrong in the way it most wants to be, or most fears to be.

---

## 9. Reproduction

```bash
# run from the repository root
python3 century_sim.py 800000                                  # headline ensemble (the default)
CENTURY_LEGACY=1 python3 century_sim.py 800000                 # simplified baseline: static structure, clipped dynamics, no collapse recovery
CENTURY_DECADAL=1 python3 century_sim.py 800000                # + decadal snapshots (section 4.3)
# the structure-conditional block (section 6.1) is in the standard output, no flag needed
CENTURY_OVERRIDES='{"race":0.95,"respond":0.25,"safety_eff":0.006,"redist_will":0.30}' \
  python3 century_sim.py 30000                                 # race-world scenario (section 5)
CENTURY_OVERRIDES='{"race":0.35,"respond":0.90,"safety_eff":0.018,"assist":0.45,"redist_will":0.75}' \
  python3 century_sim.py 30000                                 # prepared-world scenario (section 5)
CENTURY_OVERRIDES='{"plateau":true}' python3 century_sim.py 30000   # plateau-world scenario (section 5)
CENTURY_OVERRIDES='{"alpha":1.7,"k":0.15}' python3 century_sim.py 30000  # fast-takeoff scenario (section 5)
CENTURY_OVERRIDES='{"alpha":1.1,"k":0.06}' python3 century_sim.py 30000  # slow-lane scenario (section 5)
python3 calibrate_century.py 50000                             # calibration-target weights (section 6.3)
CENTURY_WEIGHTS=weights-xpt_superforecaster-50000-seed431.npz \
  python3 century_sim.py 50000                                 # + target-weighted outcome tables (section 6.3)
python3 calibrate_century.py 800000 --levers                   # choice-likelihood weights (the third view; lever-anchors.json)
CENTURY_LEVER_WEIGHTS=weights-levers-800000-seed431.npz \
  python3 century_sim.py 800000                                # + likelihood-weighted ("realistic bet") outcome tables
python3 sobol_century.py                                       # variance-based Sobol sensitivity indices
python3 check_century.py --doc-figures                         # verify this document's tables against the engine
```

Engine: NumPy only, seed 431, about 50 s for 800,000 worlds. All figures in this document come from the runs described in section 2. Every run's JSON output includes a `disempowerment_profile` block (the per-channel state snapshots behind section 3.1), a `sensitivity_P_disempowerment` block (the lever ranking behind section 3.2), an `abundance_profile` block (the recipe, crossing conditions and conditioned decadal trajectory behind section 3.3), an `extinction_profile` block (the channels, timing and final-year state behind section 3.4) and a `flourishing_profile` block (the plateau structure, readiness overshoot and no-AGI trajectory behind section 3.5).
