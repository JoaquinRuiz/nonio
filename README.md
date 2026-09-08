# Nonio

**Nonio is a measuring instrument for text.** It estimates statistical signals
associated with machine-generated language and reports them together with their
uncertainty.

**It does not decide authorship.**

---

## Notice

> Nonio's output **must not be the sole basis for any academic, employment, or
> editorial decision.**
>
> Nonio issues no verdicts. There is no output that claims a text "was written by
> AI" or "was written by a human". What it returns is the value of a set of
> statistical signals, the threshold applied, and the measured error rate of that
> threshold over a declared corpus. Reading that as an accusation is a misuse of
> the tool.

## Why this exists

Existing detectors output things like *"87 % AI"*. Students have been failed on
numbers like that — including students who wrote their own work. The number comes
with no error rate, no breakdown, and no way to argue with it.

A thermometer does not tell you that you are ill. It tells you 38.2 °C, and you
decide. Nonio is built to be a thermometer, and its design is constrained so that
it cannot quietly become a judge.

## Status

**Early development. No default threshold is published, and the tool should not
be used for any real decision.**

Right now `analyze()` abstains by default, because no calibration table ships
yet. That is not an unfinished state — it is Article III of the project's
constitution refusing to emit a figure without knowing its error rate.

What works today:

- Output schema with its constitutional invariants enforced by tests
- Extraction of measurable text (code, tables, and quotations excluded, with the
  excluded proportion reported)
- Segmentation into blocks, with per-block results
- Local language identification
- Two independent signals over a local model pair
- CLI and importable Python API with verified parity
- Evaluation harness and corpus builders

What is missing, and it is the part that decides whether this project is
publishable at all: **a calibration that survives scrutiny**. See
[calibration findings](docs/calibration-findings.md) — the current measurement
does not pass the project's own bias gate, and at the current sample size the
gate cannot even be evaluated.

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/JoaquinRuiz/nonio
cd nonio
pip install -e ".[dev]"
nonio download qwen2.5-0.5b     # ~1 GB, the only step that uses the network
nonio check                     # should report the profile as available
```

## Use

### Command line

```bash
nonio analyze essay.md                  # human-readable
nonio analyze essay.md --json           # structured output with schema_version
cat essay.md | nonio analyze            # reads stdin
nonio analyze essay.md --profile salamandra-2b
```

Other commands:

| Command | What it does |
|---|---|
| `nonio check` | Reports which measurement resources are present. No network. |
| `nonio download <profile>` | **The only command that uses the network.** |
| `nonio profiles` / `profiles --use ID` | List profiles, or remember one. |
| `nonio schema` | Emit the JSON Schema of the output. |
| `nonio eval --corpus public` | Evaluate over the corpus, always per category. |

### Exit codes

| Code | Meaning |
|---:|---|
| 0 | A reading was produced |
| 1 | Abstention — **the text cannot be measured.** Not a failure. |
| 2 | Usage error |
| 3 | Measurement resource missing |
| 4 | Internal error |

Code 1 is a legitimate, complete result. With `--json` it comes with a valid
result document whose `result.type` is `insufficient_evidence`.

### Python API

Every CLI capability exists as an importable function — no capability is
CLI-only.

```python
import nonio

result = nonio.analyze("essay.md")

match result.result:
    case nonio.Reading() as r:
        print(r.level, r.applied_threshold, r.measured_fpr, r.fpr_category)
    case nonio.Abstention() as a:
        print(a.cause, a.detail)

for block in result.blocks:          # always present
    ...
```

Abstention **never** arrives as an exception; it travels in `result.result`.
Exceptions are reserved for environment conditions — a missing model, an
unreadable input.

## How it measures

Two independent signal families, so that they fail for different reasons and
agreement between them means something:

- **Fast-DetectGPT** — conditional probability curvature. A sampling-free variant
  of DetectGPT, which makes it viable on CPU.
- **Binoculars** — the ratio of the observer model's perplexity to the
  cross-perplexity between two sibling models. That denominator measures the
  text's intrinsic difficulty, which is what stops naturally predictable prose —
  technical documentation, legal text — from being mistaken for generated text.

Both are computed in a **single forward pass per model**, accumulating per block.
Materialising full distributions for a 1,500-token document would cost about
900 MB; this keeps memory bounded and the whole analysis interactive: a 784-word
document takes a median of 4.7 s on a CPU with no GPU.

If the two signals contradict each other beyond a margin, Nonio abstains rather
than averaging them into a confident-looking middle.

## Principles

Nonio is governed by a constitution that drives every design decision, and the
constraints are enforced by tests rather than by good intentions:

1. **An instrument, not a judge.** No output asserts authorship. A test walks
   every path of the output JSON and fails if an authorship key appears.
2. **Abstention is a first-class result.** `insufficient_evidence` is a complete
   answer with a stated cause, not a failure.
3. **Calibration measured and published.** No threshold ships without its
   false-positive rate broken down by category. Aggregate accuracy hides exactly
   the harm this domain produces.
4. **Every measurement is traceable.** Per-block and per-signal breakdown, with
   the spans that produce the reading.
5. **Local by default.** No network, no keys, no sending analysed text anywhere.
   Verified by a test that makes any outbound connection raise.
6. **Spanish as a first-class language**, not thresholds calibrated in English
   and reused. Nonio abstains for languages it has not measured.
7. **Not a tool for accusation.** No guilt score, no ranking of people, no export
   designed to be attached to a disciplinary file.

One consequence worth stating: Nonio measures its own bias against non-native
writers, but it never tries to detect whether *you* are one. Inferring that would
mean profiling a person, which principle 7 forbids. The category exists to hold
the instrument to account, not to classify its users.

## Documentation

- [Getting started](docs/getting-started.md) — from clone to first result
- [Calibration findings](docs/calibration-findings.md) — the measured figures,
  why the gate does not pass, and what was deliberately not done to make it pass
- [Known limitations](docs/limitations.md) — including ones the measurement
  revealed and that have not been fixed
- [Reproducibility](docs/reproducibility.md) — what a third party can and cannot
  reproduce, and on what hardware

## Contributing

Help is genuinely needed, and the most valuable contribution right now **is not
code**. See [CONTRIBUTING.md](CONTRIBUTING.md).

## How it is built

This project is **developed with AI assistance under a specification-first
methodology**: the constitution, specification, plan, and tasks are written and
reviewed before the code.

The specification artefacts are private; the fact that they exist is not. A tool
that measures the fingerprints of automated generation cannot afford for its own
method of construction to look hidden.

## Language

Documentation and interface are in English; the measurement itself is calibrated
on Spanish first. Those are different things on purpose: a threshold measured on
English text says nothing about Spanish, so Nonio abstains for languages it has
not measured rather than extrapolating.

## License

Apache-2.0. See [LICENSE](LICENSE).

The evaluation corpus is mixed-licence — Apache-2.0, CC BY-SA, and public domain —
and every case records its own licence and provenance in `corpus/manifest.jsonl`.
