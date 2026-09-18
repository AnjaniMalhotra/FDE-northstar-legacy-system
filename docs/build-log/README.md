# Build Log — one doc per step

This folder holds one short doc per build step, in order. This is the trail your professor or a
student follows to understand what was built, when, and why — separate from the code itself.

## Naming convention

`NN-short-name.md`, numbered in the order steps are built, starting at `01`. Several entries merge
what were originally multiple, closely-related build steps (e.g. a feature and a later bug found in
it) into one doc, told as ordered parts — see each merged entry's own intro line for what it
combines.

## Template for each doc

```markdown
# NN — [Step name]

**Status:** planned / in progress / done

## What we're building (written before the code)
[2–4 sentences: what this step does and why it's needed, in plain language]

## What we actually built (written after the code)
[What got built, where the code lives, and anything that changed from the plan and why]

## Key decisions
[Any non-obvious choice made and the reasoning — this is what makes the doc useful for teaching, not just a changelog]
```

6 entries so far (`01` through `06`). See [docs/PROJECT_SUMMARY.md](../PROJECT_SUMMARY.md) for the
full narrative these entries build up to.
