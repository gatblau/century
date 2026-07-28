# How Century Superforecaster works

Nobody knows how the next hundred years go. This model handles that by refusing to guess once.

It builds 800,000 different versions of the future and plays each one out year by year, from 2026 to 2126. Every version makes slightly different assumptions about how fast AI improves, how likely wars and pandemics are, and how well governments cope. At the end it counts how the 800,000 versions turned out. That count is the answer: a map of what could happen and how often.

## How a world plays out

Each of the 800,000 worlds starts the same way. It draws its own settings from a set of ranges. One world gets fast AI progress and weak institutions. Another gets slow progress and strong cooperation. Those ranges are the model's assumptions, and they are written down where anyone can see them.

Then the world runs forward, a year at a time. Each year something can happen: a nuclear war, a pandemic, an AI warning shot, a slow loss of human control. How likely each one is depends on the state that world is in, so a tense, racing world is more dangerous than a calm, prepared one. After a hundred years the world has landed somewhere, broadly good, broadly bad, or in between, and the model records where.

One of the things a world tracks each year is how ready it is for the AI it has: how well it can test, understand and contain the systems it has built. Safety work adds to that stock, and the AI itself can be pointed at the problem. But the stock also leaks. Every jump in capability makes part of last year's testing regime out of date, because the tests were written for a weaker system. A world that keeps building without redoing that work loses ground even while it is running hard. How fast the leak runs is a number nobody has measured, so the model reports its headline twice, once for a world where containment decays and once for a world where it holds.

Do that 800,000 times and you have the full spread.

## Why trust it

It is not a crystal ball and does not pretend to be. Here is the honest case for it.

You can see everything it assumes. Every number sits in a file you can open. If you think the odds of nuclear war are too high, find that number, change it, and run it again. Nothing is hidden.

The ranges are not one person's hunch. They come from published expert surveys, forecasting tournaments, UN population projections and IPCC climate scenarios, all listed in `anchors.json` with their sources.

It repeats exactly. The runs are seeded, so you get the same numbers we did. Anyone can reproduce a result and argue with it on level terms.

It checks its own work, and the checks are not for show. The repo re-runs the model against saved results, re-derives every figure quoted in the write-ups, and plants a deliberate bug to confirm the checker would catch one. A checker that never fails is useless, so this one is built to fail when something is wrong.

And it is small. The whole thing is a few Python files and NumPy. You can read the engine in an afternoon.

## Three ways to read the results

The same 800,000 worlds can be counted three ways, and the model reports them side by side.

**The headline.** The plain count, the number this repository leads with, treats every social and political choice as open. A world that shares the gains of AI is as common as one that hoards them. Read it as a price list: if the world makes this choice, this is what it buys. This count itself comes in two versions, for the containment leak described above: a good century runs at about 39 in 100 if containment decays and about 44 in 100 if it holds. Every other number in the repository uses the first.

**The outside view.** The same worlds, adjusted so the totals line up with published expert forecasts of things like extinction risk and AI timelines (`anchors.json`). Read it as what professional forecasters expect.

**The realistic bet.** The same worlds again, adjusted for how likely each choice actually is before powerful AI arrives (`lever-anchors.json`). Where the headline says what the century could be, this count says where it is heading. Nobody has surveyed a question like "will a major economy share the AI gains by 2035", so these are honest, written-down guesses with the reasoning next to them. Anyone who disagrees can edit the file and rerun. Because the obstacles to most of the choices are real, this count comes out below the headline.

The gap between the headline and the realistic bet is itself a finding. It says how much of a better century is sitting in choices the world is unlikely to make on its own. The estimates and the numbers they produce are in [`realistic-bet.md`](realistic-bet.md).

## Where it falls short

The model has real limits, and they are worth knowing.

The outcome buckets are coarse. "Broadly good" covers a lot of very different futures.

The ranges are judgement calls. They are anchored to today's best estimates, and today's best estimates are often wide or wrong.

It cannot model a surprise nobody has thought of. Real history is full of those.

The structure is one way of seeing the world. Someone else would wire the pieces together differently and get different numbers. That is fine. The job is to make the disagreement concrete enough to argue about.

## What to use it for

Change one policy, run it again, and see how much the outcome changes. That tells you which choices matter and which are noise. More than anything, it turns a vague argument about the future into a specific one about numbers both sides can see.
