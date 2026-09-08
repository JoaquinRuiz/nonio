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
| Sample | 60 cases per category (`generado`: 18) |
| Minimum length | 150 words |

## Result: the gate blocks, but the reason is insufficient sample

At the design threshold (0.90, targeting 5 % FPR):

| Category | n | FPR | TPR |
|---|--:|--:|--:|
| `humano_pre2022` | 60 | 6.7 % | — |
| `espanol_no_nativo` | 60 | **16.7 %** | — |
| `tecnica_estructurada` | 60 | 6.7 % | — |
| `generado` | 18 | — | 66.7 % |
| `mixto` | **0** | — | — |

Bias ratio: **2.50×**, above the 2.0× ceiling FR-030 imposes.

**But that number does not stand on its own.** Bootstrap over 2,000 resamples:

| Threshold | Ratio | 95 % CI | Cases behind it |
|---:|---:|:---|:---|
| 0.90 | 2.50× | **[0.89 – 11.00]** | 4/60 vs 10/60 |
| 0.97 | 2.00× | [0.00 – 5.00] | 1/60 vs 2/60 |

The interval at the design threshold spans from "no bias" to "eleven-fold". The
honest conclusion is not *"the instrument is biased 2.5×"* — it is **"with n=60
the gate cannot be evaluated"**.

### Sample size actually required

To distinguish a 2.0× bias from 1.0× at 80 % power, α = 0.05:

| Scenario | n per category |
|---|--:|
| FPR 5 % vs 10 % | **434** |
| FPR 10 % vs 20 % | 199 |
| FPR 15 % vs 30 % | 121 |

The bottleneck is **not** the non-native category — that one has 4,251 cases
available. It is `humano_pre2022`, which has 60.

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
