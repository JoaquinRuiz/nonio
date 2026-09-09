# Roadmap

Ordered by one rule, which comes from Article III of the project's constitution:
**nothing gets published until it can state its own error rate.** Every milestone
below is a measurement that has to come back with a number, not a feature that has
to be built.

## Where we are — 0.1.0

The instrument is built and works end to end. What it measures is not yet good
enough to use on anyone.

| | Measured |
|---|---|
| False positives on human prose | **5.3 %** |
| Machine-generated text caught | **47 %** — CI [36 %, 58 %], n=72 |
| Bias against non-native Spanish | 1.30× — CI [0.78, 2.53] → **inconclusive** |
| Speed | 1,000 words in 12 s median, CPU only |
| Corpus | 4 of 5 categories, ~1,400 balanced cases |

`analyze()` abstains by default because no calibration table ships. That is not an
unfinished state — it is the gate working.

Full detail: [calibration findings](docs/calibration-findings.md).

---

## 0.2 — Is it useful at all?

**Question:** can sensitivity reach a number worth defending?

47 % at a 5 % false-positive rate is slightly under half of what it is looking
for. Everything so far runs on a 0.5B-parameter model chosen for speed. The
obvious first move is a larger, Spanish-first one.

- **[#2](../../issues/2) Measure the `salamandra-2b` profile** — 2B parameters,
  BSC, Spanish-prioritised pretraining, already defined and never measured

**Ships when:** both profiles have published figures, side by side, whichever way
they come out.

**This milestone can fail**, and that matters more than the rest of this document.
See *When to stop* below.

---

## 0.3 — Is it fair? (currently unknown)

**Question:** can the bias gate reach a verdict instead of a shrug?

The gate returns *inconclusive* because the confidence interval crosses the 2.0×
ceiling, not because unfairness was demonstrated. This is a sample size problem.

- **[#3](../../issues/3) Expand the reference corpus** so the interval narrows.
  The bottleneck is `humano_pre2022` (450 cases, all Spanish Wikipedia), not the
  non-native category (4,251 available).
- **[#4](../../issues/4) Decide whether FR-030 needs an absolute ceiling** — the
  gate constrains the *ratio* only, and measurement showed it can be satisfied by
  making the instrument uniformly bad. A threshold that flags one person in five
  scores a perfect 1.00× ratio. This is a product decision, not an implementation
  one.

**Ships when:** the gate returns `pasa` or `bloquea` with the whole interval on
one side. Either is progress; *inconclusive* is not.

---

## 0.4 — Is the corpus honest?

**Question:** does the corpus cover what the constitution says it must?

- **[#1](../../issues/1) Populate the `mixto` category** — text a person rewrote
  by hand from model output. **This one needs people, not code.** It cannot be
  faked: a model editing a model is a different thing and would shift every
  published figure unpredictably.
- **[#5](../../issues/5) Explain the technical-prose anomaly** — structured
  technical writing has the *lowest* false-positive rate (2.3 %), the opposite of
  what Article III assumes. Either the corpus has a blind spot in a category the
  constitution specifically names, or a design goal was met. The two have opposite
  implications and neither should be claimed yet.

**Ships when:** all five categories exist, and the anomaly has an explanation
backed by measurement rather than a guess.

---

## 1.0 — Publishable

A 1.0 says *ready to use*. It requires all of:

- [ ] Bias gate returning `pasa` — the entire confidence interval below 2.0×, not
      just the point estimate ([#3](../../issues/3), [#4](../../issues/4))
- [ ] `mixto` category populated ([#1](../../issues/1))
- [ ] A default calibration table shipped, so `analyze()` produces readings
      without one being passed in
- [ ] Sensitivity high enough to be worth someone's time, with a stated figure

Publishing a 1.0 while the instrument cannot state its own error rate would
contradict Article III in the version number itself.

Release mechanics: [docs/releasing.md](docs/releasing.md) and
[#6](../../issues/6).

---

## When to stop

A roadmap that cannot fail is marketing. This one can, and it is worth naming the
conditions in advance, before there is any sunk cost to defend.

**Nonio should be abandoned, or narrowed to a research artefact, if:**

- Sensitivity stays below roughly 60 % at a ≤5 % false-positive rate across both
  profiles. A tool that misses half of what it looks for, while wrongly flagging
  one human in twenty, does more harm than good — the harm lands on the people
  falsely flagged, and the benefit is a coin flip.
- The bias gate settles on `bloquea` and no threshold satisfies it without
  degrading the instrument for everyone. Article III would then have been right
  and the honest conclusion is that this approach is unfair to non-native writers
  and should not exist as a product.
- The `mixto` category turns out to be indistinguishable from human text at any
  useful threshold. Mixed authorship is the most common real case; being blind to
  it would make the tool answer a question nobody asks.

Reaching any of those is a legitimate outcome and gets published like any other
result. The project's value is the measurement, not the product.

---

## Not on the roadmap

Out of scope by decision, not by omission:

- Image, audio, or video detection
- Plagiarism detection or fact-checking
- Watermark reading (SynthID and similar)
- Attributing text to a specific model
- LMS integrations
- Any batch mode that compares people to each other

The last one is forbidden by Article IX, not merely deprioritised. Nonio does not
offer features whose main purpose is to support an accusation against an
individual.

## How to help

The most valuable contribution right now is [#1](../../issues/1), and it does not
involve writing code. See [CONTRIBUTING.md](CONTRIBUTING.md).
