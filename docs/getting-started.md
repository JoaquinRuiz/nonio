# Getting started

Target: from a clean checkout to your first result in under five minutes,
excluding the model download (SC-001).

## 1. Install (~1 min)

```bash
git clone https://github.com/JoaquinRuiz/nonio
cd nonio
pip install -e ".[dev]"
```

Requires Python 3.11 or newer.

## 2. Get the measurement resources (~2–5 min, once)

```bash
nonio download qwen2.5-0.5b
```

About 1 GB. **This is the only command that touches the network.** Analysis never
does — if a model is missing it fails with a resource error telling you to run
this, rather than fetching it silently. The text you analyse is often sensitive,
and downloading is a decision that belongs to you.

```bash
nonio check
```

Should report the profile as available.

## 3. Your first analysis (~10 s)

```bash
nonio analyze README.md
```

You will get an abstention:

```
RESULTADO: insufficient_evidence  (uncalibrated_language)
  No hay tabla de calibración disponible. Nonio no publica una lectura sin la
  tasa de falsos positivos medida de su umbral (Artículo III).
```

**This is correct behaviour, not a broken install.** No calibration table ships
yet, and Nonio will not emit a reading without knowing its own error rate. See
[calibration findings](calibration-findings.md) for where that stands.

## What you can do today

Everything except get a reading:

```bash
nonio analyze essay.md --json     # structured output, schema_version included
nonio schema                      # the full JSON Schema
nonio profiles                    # available profiles and measured runtimes
nonio eval --corpus public        # evaluate over the corpus, per category
```

The `--json` output shows what Nonio extracted, which spans it excluded and why,
how it split the document into blocks, and which language it detected — all of
which work now and are worth inspecting.

## Reading the output

| Field | Means |
|---|---|
| `result.type` | `reading` or `insufficient_evidence` |
| `level` | Intensity of a **statistical signal**. Never a claim about who wrote the text. |
| `applied_threshold` | The threshold used. Mandatory. |
| `measured_fpr` | Measured false-positive rate of that threshold on the matched category. Mandatory. |
| `fpr_reproducible` | Whether a third party can reproduce that figure |
| `excluded_ratio` | Proportion of the document excluded from measurement (code, tables, quotes) |
| `blocks` | Per-block results. Always present. |

If `excluded_ratio` is high, read the result knowing most of the document was not
measured.

## Exit codes

| Code | Means |
|---:|---|
| 0 | A reading was produced |
| 1 | Abstention — the text cannot be measured. **Not a failure.** |
| 2 | Usage error |
| 3 | Measurement resource missing |

In a script, treat `1` as a legitimate answer and `2`/`3` as problems to fix.

## Performance

Measured on Apple Silicon, CPU only, no GPU, with the default profile:

| Document | Median | p95 |
|---|--:|--:|
| 1,000 words | 12.1 s | 19.1 s |

Well inside the 30 s / 60 s budget SC-006 sets. `nonio profiles` shows the
measured runtime for each profile; a profile with no measurement says so rather
than showing an invented figure.
