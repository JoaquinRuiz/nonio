# Contributing to Nonio

Thank you for considering it. Before anything else, please read the
[constitution summary in the README](README.md#principles) — this project has
constraints that are unusual, deliberate, and non-negotiable, and a technically
excellent contribution that violates one of them cannot be merged.

---

## The most useful thing you can do does not involve code

### Write for the `mixto` corpus category

This is the **single biggest blocker** in the project right now.

Nonio's calibration needs five categories of text. Four of them exist. The fifth
is `mixto`: **text where a person took model output and rewrote it by hand.**

It cannot be faked. If a model generates text and a model edits it, that is a
model editing a model — not a person editing model output. The two behave
differently, and using the wrong one would corrupt every published figure in a
direction nobody could measure. So this category needs actual humans.

**What we need from you:**

1. Ask any language model to write ~500 words in Spanish on a topic of your
   choice.
2. Rewrite it by hand the way you actually would if you were going to submit it —
   fix what sounds wrong, cut what is padding, add what is missing, change what
   you disagree with. Anything from light editing to heavy rewriting is useful;
   what matters is that a **person** did it.
3. Send us: the original model output, your edited version, which model you used,
   and roughly how heavily you edited (light / moderate / heavy).

Open an issue with the `corpus` label, or a PR adding files under
`corpus/public/mixto/`. You keep authorship; contributions are licensed
Apache-2.0 along with the rest of the corpus, so please only submit text you
wrote or edited yourself.

**Especially wanted:** contributors whose first language is not Spanish. That
group is the one this whole project is trying to protect from false accusation,
and they are the hardest to represent fairly in a corpus.

### Expand the reference corpus

`humano_pre2022` needs to reach ~450 cases for the bias gate to be statistically
evaluable at all — see [calibration findings](docs/calibration-findings.md).
Sources must be **freely redistributable** (public domain, CC BY-SA, Apache-2.0)
and verifiably written before 2022.

### Try to break it

Genuinely useful:

- Feed it text that should abstain and see if it produces a reading instead
- Feed it your own writing and see if it flags you
- Try a "humanizer" tool and tell us what happens — we want that documented, not
  avoided
- Find a way to make an output assert authorship

Report what you find, especially the uncomfortable results. A finding that makes
Nonio look bad is worth more than one that makes it look good.

---

## If you do want to write code

### Setup

```bash
git clone https://github.com/JoaquinRuiz/nonio
cd nonio
pip install -e ".[dev]"
nonio download qwen2.5-0.5b
pytest tests/ -v
```

### Before you open a PR

```bash
ruff check .
black --check .
pytest tests/
nonio eval --corpus public      # required to pass: it is a merge condition
```

### Things that will get a PR rejected, no matter how good the code is

These come from the constitution, not from taste:

| Don't | Why |
|---|---|
| Add any field that asserts authorship — `is_ai`, `verdict`, `probability_ai` | Article I. A contract test walks the whole output tree and will fail. |
| Treat abstention as an error, or raise it as an exception | Article II. It is a complete result. |
| Publish a reading without `applied_threshold` and `measured_fpr` | Article III. The type system won't let you construct one. |
| Return a document-level score without the per-block breakdown | Article IV. |
| Make `analyze()` touch the network | Article V. A test makes any outbound connection raise. |
| Add a capability to the CLI only | Article VI. A parity test reads the command registry. |
| Reuse one profile's thresholds on another, or one language's on another | Article VIII. The loader rejects it. |
| Add batch comparison across people, or an export designed for a disciplinary file | Article IX. |
| Improve a metric by raising the length minimum | It makes the numbers look better by dropping the writers most at risk. See [calibration findings](docs/calibration-findings.md). |

### Things that are actively welcome

- **Reducing abstention** — but you must show, on the corpus, that the
  abstentions that disappear were avoidable and not lucky guesses. Lowering the
  abstention rate is never a goal in itself.
- **A new signal**, if it is independent of the existing two and you can say what
  it measures.
- **Calibrating a new language** — measured on that language, never extrapolated.
- **Making it faster**, as long as determinism survives.
- **Better quotation detection in plain text**, which is currently heuristic.

### Changing a requirement

If your change needs a rule to bend, the rule gets amended explicitly, in its own
commit, with the reason — never quietly inside a feature. That applies to the
constitution and to the spec's requirements alike. If you think a principle is
wrong, say so in an issue; that is a legitimate conversation.

---

## Reporting a problem

Useful bug reports include: the input (or something that reproduces it), the
profile used, the full `--json` output, and what you expected instead.

If you found a way to make Nonio assert authorship, or to make it systematically
unfair to a group of people, **that is the highest-priority category of bug in
this project.** Please say so in the title.

## Code of conduct

Be decent. This project exists because tools in this space have been used to
accuse people, often wrongly and often the same kinds of people. Keep that in
mind in how you treat the humans here too.
