---
name: repo-absorb
description: Absorb the essence of a repository or subsystem properly — full reads with proof, not doc-skims or keyword-grep sampling. Use whenever studying, auditing, or comparing codebases (competitor analysis, "how does X implement Y", pre-build fact-checks, "read this repo"). Any comparison verdict produced without this protocol's absorption proof is untrusted.
---

# repo-absorb — read code like it matters

## The failure this kills

Agents default to: (1) reading docs instead of code, (2) grepping predicted keywords — confirmation sampling that can never surface the unpredicted, (3) sampling files instead of full reads. Root cause is economics (docs are the cheapest tokens), not ability. Field datapoint: exhaustive file exploration beats graph-shortcut retrieval on answer quality (92% vs 83%, Codebase-Memory benchmark) — full reading *wins*, it's just costlier. So: use structure to decide **where** to spend the reading budget, then actually spend it.

## Protocol

**Pass 1 — Skeleton (whole repo, cheap).** Dir tree, entry points, build/wiring files, line counts per dir → subsystem map. Grep is allowed only to find *doors*, never to answer *questions*. No conclusions may be stated in this pass.

**Pass 2 — Locate by tracing.** Start from the entry point that must touch the axis under study (the turn loop, boot sequence, scheduler) and follow imports/calls to the owning subsystem. Never navigate by keyword guesses.

**Pass 3 — Full read of the located subsystem.** Every file, *including tests*, dependency order. Subsystems are typically 1–5k lines — always feasible. Pack it into one bounded read:

```bash
cd <repo> && npx -y repomix --include "src/<subsystem>/**" -o <scratchpad>/<name>-pack.xml
# verified-live 2026-07-13: aiko-core src/memory → 6 files, 5,272 tokens, one Read call
```

Multiple subsystems or a huge one → fan out subagents, one full absorption each (each returns the Pass-4 deliverables). Context limits must never force sampling.

**Pass 4 — Forcing functions (the absorption proof, mandatory in the output):**
- **Mechanism reconstruction**: state → trigger → transform → store dataflow, `file:line` on every edge.
- **Constants table**: caps, thresholds, magic numbers. Producible only from code — a doc-reader cannot fake this.
- **Docs-vs-code discrepancy list**: ≥1 place the docs lie or omit. Docs always drift; zero findings means the code wasn't read.
- **Falsification hunt**: search for the code that would *disprove* the conclusion. Absence claims ("no producer calls this") are proven **only** by exhaustive search over the whole repo, never by a subsystem read.

**Pass 5 — Essence distillation (what the mechanism cannot say).** Mechanism is *how*; essence is *why this shape*. From the Pass-4 evidence, distill:
- **Design bets**: what this codebase believes (e.g., "the model can't be trusted to self-enforce → host owns state"; "prefix-cache economics beat context richness"). Each bet cited to the code that embodies it.
- **Invariants**: the rules the code refuses to break even at cost (never auto-delete, never block the user's reply on a side effect, never trust a doc).
- **Scars**: code shaped by a past failure (issue numbers, guard modules, "why heuristics + LLM and not heuristics alone" comments) — the paid-for lessons.
- **What to exceed, not copy**: the bet's weakness — where the design's own logic points past itself.
An absorption without this pass produced a parts list, not understanding.

**Pass 6 — Provenance ledger.** Every claim carries `file:line`; unknowns are listed as unknowns, not smoothed over.

## Tooling notes

- **repomix** (verified-live): the core tool — one-file packs with hard `<file>` boundaries and token counts; respects .gitignore; `--include`/`--ignore` globs scope it to the subsystem. Also has `--compress` (tree-sitter signatures-only) for a cheap Pass-1 on unfamiliar large repos.
- **RepoMapper / Aider repo-map** (optional, not installed): tree-sitter + PageRank ranked structural maps. Worth pulling only for very large unfamiliar repos where entry-point tracing stalls; on small/medium repos Pass 1–2 with native tools is enough.
- Docs/READMEs are read **last**, as hypotheses to diff against the code (they feed the discrepancy list) — never as the source of a verdict.

## Trust contract

A comparison or audit verdict that arrives without the Pass-4 deliverables is invalid — reject it or redo it. Same law as pixel-verify: verification pressure creates the behavior.
