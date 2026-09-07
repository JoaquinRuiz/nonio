# Nonio

**Nonio is a measuring instrument for text.** It estimates statistical signals associated with
machine-generated language and reports them together with their uncertainty.

**It does not decide authorship.**

---

## Notice

> Nonio's output **must not be the sole basis for any academic, employment, or editorial
> decision.**
>
> Nonio issues no verdicts. There is no output that claims a text "was written by AI" or "was
> written by a human". What it returns is the value of a set of statistical signals, the threshold
> applied, and the measured error rate of that threshold over a declared corpus. Reading that as an
> accusation is a misuse of the tool.

Nonio abstains — `insufficient_evidence` — when a text is too short for signals to rise above
noise, when the signals contradict each other, or when there is no calibration for the detected
language. Abstention is a valid, complete result, not a failure.

## Status

**Early development. It does not yet publish thresholds or calibration figures**, and until it does
it should not be used for anything beyond experimenting with the code itself.

What exists today: the output schema with its invariants enforced by tests, extraction of measurable
text (excluding code, tables, and quotations), segmentation into blocks, local language
identification, and the two measurement signals over a pair of local models.

What is missing is what decides whether this project is publishable at all: the evaluation corpus
and the calibration. In particular, a self-imposed release gate — no default threshold will be
published whose false-positive rate on Spanish written by non-native speakers exceeds that of
general human text by more than 2.0×.

## Principles

Nonio is governed by a constitution that drives every design decision. In short:

1. **An instrument, not a judge.** No output asserts authorship.
2. **Abstention is a first-class result.** Abstaining is never worse than risking a measurement
   that does not hold up.
3. **Calibration measured and published.** No threshold ships without its false-positive rate
   broken down by text category. An aggregate accuracy figure hides exactly the harm this domain
   produces: bias against non-native prose and against highly structured technical writing.
4. **Every measurement is traceable.** Per-block and per-signal breakdown, with the specific spans
   that produce the reading.
5. **Local by default.** No network, no keys, no sending the analysed text to third parties.
6. **Spanish as a first-class language**, not thresholds calibrated in English and reused.
7. **Not a tool for accusation.** No guilt score, no ranking of people, no export designed to be
   attached to a disciplinary file.

## How it is built

This project is **developed with AI assistance under a specification-first methodology**: the
constitution, specification, plan, and tasks are written and reviewed before the code.

The specification artefacts are private; the fact that they exist is not. A tool that measures the
fingerprints of automated generation cannot afford for its own method of construction to look
hidden.

## Language

Documentation and interface are in English; the measurement itself is calibrated on Spanish first.
Those are different things on purpose: a threshold measured on English text says nothing about
Spanish, so Nonio abstains for languages it has not measured rather than extrapolating.

## Documentation

- [Known limitations](docs/limitations.md) — including ones the measurement
  revealed and that have not been fixed
- [Reproducibility](docs/reproducibility.md) — what a third party can and cannot
  reproduce, and on what hardware the figures were measured

## License

Apache-2.0. See [LICENSE](LICENSE).
