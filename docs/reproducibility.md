# Reproducibility

Required by SC-003 and R-008. Two different promises, deliberately named
differently.

## Determinism (FR-006)

**Same machine, same configuration, same input → identical output.**

Achieved by pinning float32, fixing seeds, and disabling non-deterministic
kernels. Verified by a test that runs the same analysis twice and compares.

## Reproducibility across machines (SC-003)

**Not bit-identical.** Reduction order varies with thread count and BLAS library,
so published values are rounded to a fixed number of decimals to absorb that
variation.

Promising bit-identical results across different CPUs would be false. What is
promised is agreement within a declared tolerance band.

### Reference hardware

Figures published by this project are measured on:

- Apple Silicon, CPU only, no GPU
- Python 3.12, torch 2.x, float32
- Default profile `qwen2.5-0.5b`

Measured so far: a 784-word document (1,219 tokens) completes with a median of
**4.7 s**, against the 30 s median required by SC-006.

### What a third party can reproduce

| Corpus | Ships with the package | Reproducible by a third party |
|--------|:----------------------:|:-----------------------------:|
| Public  | yes | **yes** |
| Private | no  | no — figures published and marked as such |

Every figure in the evaluation report carries a `reproducible` flag. A figure
derived from the private corpus is published next to the public one for the same
category, never in place of it.

## Reproducing the corpus

```bash
git clone https://github.com/ucdaviscl/cowsl2h /tmp/cowsl2h
python -m nonio.evaluation.build_corpus --cowsl2h /tmp/cowsl2h
python -m nonio.evaluation.build_corpus --wikipedia
python -m nonio.evaluation.generate_corpus
```

Wikipedia sources are pulled as **revisions dated before 1 January 2022**, not
current versions: a live page may have been edited later with model assistance,
which would make the "human, pre-2022" category untrue to its name.

The generated category uses `ibm-granite/granite-3.1-2b-instruct` — a different
model family from both measurement profiles. Generating the corpus with a model
from a profile's own family would inflate that profile's figures by construction,
and the code aborts if you try.
