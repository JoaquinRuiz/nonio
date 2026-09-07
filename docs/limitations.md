# Known limitations

Required by FR-025. This list includes limitations the measurement itself
revealed and that have **not** been fixed. Hiding them would defeat the purpose
of the instrument.

## Machine translation is indistinguishable from generation

Automatic translation flattens the same signals that machine generation does.
Nonio does not attempt to tell them apart, and does not abstain on suspicion of
translation either: abstaining would require detecting translation with a
reliability the project cannot demonstrate.

**Consequence:** a text written by a person in one language and machine-translated
into Spanish may show a high signal. This is a false positive, and it is a known
one. It is not a defect to be reported — it is a documented boundary.

## Selection bias in the length minimum

The minimum word count is not a neutral technical parameter. Measured on
COWS-L2H, the only redistributable source for the non-native Spanish category:

| Minimum | Cases retained | Median length of those retained |
|--------:|---------------:|--------------------------------:|
| 250 words | 77 % | 261 words |
| 300 words | **10 %** | 334 words |

The essays that survive a higher minimum are the longest ones, and length is a
direct proxy for command of the language. Calibrating the false-positive rate for
non-native speakers on their most advanced writers would **understate** the bias —
precisely the harm Article III exists to prevent.

Nonio therefore reports the selection bias introduced by whatever minimum is
chosen. Raising the minimum makes the published figures look better; that is the
reason to distrust it, not to do it.

## Register bias in the public corpus

The public corpus mixes public-domain and freely licensed sources. Those skew
toward encyclopedic and literary prose, with little everyday or student writing —
which is the actual use case. The private corpus exists to cover that gap, and its
figures are published alongside the public ones but marked as not reproducible by
third parties (SC-003).

## Blocks are measured in document context

Each block is scored within the context of the full document, not in isolation.
This is the right behaviour for mixed text, but it means a block's score is not
identical to what that same block would yield analysed on its own.

## Quotation detection in plain text is heuristic

Without markup there is no AST. In plain text, quotation detection falls back to
heuristics (lines beginning with `>`, long runs between quotation marks) and is
marked as `detection: "heuristic"` in the output. The reported `excluded_ratio`
lets you see that exclusion was partial.

## Thresholds belong to a profile

A threshold calibrated on `qwen2.5-0.5b` is not valid on `salamandra-2b`. The
loader refuses to apply one profile's calibration to another. This is the same
error Article VIII forbids across languages.

## Behaviour against "humanizer" tools

To be measured and documented, not avoided. Pending: no figures yet.

## Missing corpus category

The `mixto` category — a person editing model output by hand — is **not yet
populated**. It cannot be fabricated: text generated and then edited by a model is
not a human editing model output, and using it would corrupt the calibration in an
unknown direction. This category needs human contributors working to a documented
protocol.

Until it exists, any published calibration is incomplete, and the evaluation
report declares the category as missing rather than omitting it silently.
