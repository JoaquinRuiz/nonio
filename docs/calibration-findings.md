# Calibration findings

Article III requires that a calibration gap be **documented and left visible** in
published results, and explicitly forbids covering it up by adjusting the corpus,
the threshold, or the report. This file exists to comply with that.

**Status: no default threshold is published.** The FR-030 gate does not pass, and
more importantly, at the current sample size it cannot be evaluated at all.

## Measurement conditions

| | |
|---|---|
| Profile | `qwen2.5-0.5b` (Qwen2.5-0.5B + Qwen2.5-0.5B-Instruct) |
| Language | Spanish |
| Hardware | Apple Silicon, CPU only, float32 |
| Sample | 450 cases per category (`generado`: 18) |
| Minimum length | 250 words |

## Result: inconclusive

At threshold 0.9167 (targeting 5 % FPR on the reference category):

| Category | n | FPR | TPR |
|---|--:|--:|--:|
| `humano_pre2022` | 414 | 5.3 % | — |
| `espanol_no_nativo` | 347 | 6.9 % | — |
| `tecnica_estructurada` | 392 | 2.3 % | — |
| `generado` | 18 | — | 61.1 % |
| `mixto` | **0** | — | — |

**Bias ratio: 1.30×, 95 % CI [0.78 – 2.53].**

The point estimate sits below the 2.0× ceiling. The interval crosses it. The
verdict is therefore **inconclusive** — not "passes" — and inconclusive does not
authorise publishing a default threshold.

### The first measurement was noise

An earlier run with n=60 produced a ratio of **2.50×, CI [0.89 – 11.00]**, and
was reported here as though it demonstrated bias. It did not. Multiplying the
sample by 7.5 halved the ratio: what changed was not the instrument but the
precision of the instrument measuring it.

That episode is why **FR-031** exists — no bias figure may be published without
its confidence interval and the number of cases behind it — and why the gate now
returns three states instead of two.

### An unexpected result worth following up

`tecnica_estructurada` has the **lowest** false-positive rate of all human
categories (2.3 % against 5.3 % for general prose). Article III names highly
structured technical writing as a category at risk of false positives, so this is
the opposite of what the design assumed.

Two candidate explanations, neither verified: Wikipedia's technical prose may be
less predictable than assumed, or Binoculars' normalisation by intrinsic
difficulty may be doing exactly what FR-002 asks of it. Worth investigating before
claiming either.

### Sample size

To distinguish a 2.0× bias from 1.0× at 80 % power, α = 0.05, roughly 434 cases
per category are needed at the FPR levels Nonio operates at. The reference corpus
was expanded from 60 to 450 to reach that.

It was still not enough to reach a conclusion: at a 5 % base rate the ratio rests
on 21 and 24 flagged cases respectively, and a ratio of small counts stays wide.
Reaching a verdict needs either more cases or a higher base rate — and raising
the base rate means a worse instrument, so more cases it is.

## Finding: FR-030 can be satisfied by degrading the instrument uniformly

The threshold sweep is **not monotonic**, and that exposes a flaw in the project's
own safeguard:

| Threshold | FPR general | FPR non-native | Ratio | Gate |
|---:|---:|---:|---:|:--|
| 0.85 | 18.3 % | 18.3 % | **1.00×** | passes |
| 0.90 | 6.7 % | 16.7 % | 2.50× | blocks |
| 0.97 | 1.7 % | 3.3 % | 2.00× | passes |

At threshold 0.85 the gate passes **perfectly** — a ratio of exactly 1.00, total
equity — while the instrument falsely flags **one person in five**, native and
non-native alike.

FR-030 constrains only the *ratio*, not the absolute false-positive rate. A
detector that accuses everybody is perfectly fair and perfectly useless.

**Recommendation:** FR-030 needs a companion absolute ceiling — something of the
form *"and the false-positive rate on general human text must not exceed X %"*.
Amending it is a spec decision, not one to be made inside an implementation task,
so the gate is left as specified and this gap is recorded here instead.

## What was deliberately not done

Raising the minimum length to 250 words makes the gate pass (1.69×). **This was
rejected.** The ratio improves not because the instrument becomes fairer to
non-native speakers — their FPR actually rises, 16.7 % → 17.8 % — but because the
reference category's FPR rises faster, 6.7 % → 10.5 %. The gap closes by making
things worse for everyone, and at 300 words only 10 % of the non-native category
survives, biased toward its longest and most fluent writers.

That is exactly what Article III means by covering up a gap by adjusting the
corpus. The measurement stands as it is.

## Legitimate paths forward

1. **Expand the reference corpus** to n ≈ 400 so the gate becomes evaluable. In
   progress; this is cheap, only download time.
2. **Harden the threshold and accept more abstention.** Article II endorses this
   explicitly: abstaining is never worse than risking a measurement that does not
   hold up. It costs usefulness, not honesty.
3. **Publish without a default threshold**, requiring an informed choice.
4. **Try the `salamandra-2b` profile.** Thresholds belong to a profile, so it
   would need measuring from scratch.

## Caveats on every figure above

- `generado` has n=18. Its TPR is provisional; do not lean on it.
- The `mixto` category is entirely absent. Any calibration is incomplete while it
  is, and the evaluation report declares it missing rather than omitting it.
- 60 cases per category is enough to notice a problem, not to publish a figure.
