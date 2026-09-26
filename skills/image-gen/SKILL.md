---
name: image-gen
description: Generate bespoke imagery by delegating to a local agentic CLI (agy/Antigravity, then codex) and reading the saved file. Use when an image CANNOT be found via stock search — envisioned/conceptual scenes, specific actions or poses, brand-specific art, "things beyond basic imageries." Reach for this AFTER trying stock fetch (Pexels/Pixabay/Openverse) for anything findable. Durable: no rented GPU, no per-image API cost — it rides the user's own flat-rate CLI subscriptions.
---

# image-gen — bespoke imagery via local CLI delegation

The durable generation rung of the visual pipeline. The CLIs render to disk via their own
image tools (they do **not** emit images on stdout), so we instruct the CLI to **save to an
exact path** and then read the file (the "call & dump" pattern, like `[[gen-via-cli]]`).

**Verified 2026-06-21:** `agy --dangerously-skip-permissions -p "<prompt> … save to <path>"`
produced a real 1024×1024 PNG. `codex` is the fallback provider.

## When to use (decision)
1. **Findable imagery** (real photos, common objects, people, places) → DON'T gen — fetch from
   **Pexels/Pixabay/Openverse** (cheaper, real, faster) and duotone to brand.
2. **Un-findable / envisioned** (a specific imagined scene, an action/pose, a metaphor, brand
   art, "no single correct button" as a render) → **gen here.**
3. Always appraise the result (resolution/relevance/on-brand) before placing it.

## Use it
```
py skills/image-gen/scripts/gen.py --prompt "<what to draw>" --out path/art.png [--provider agy|codex] [--timeout 300]
```
Prints the output path on success; non-zero + stderr if no provider produced an image.

## Notes
- Prompts: be concrete + on-brand (e.g. "dark editorial, flat vector, deep purple bg, no text").
- `agy` writes to `~/.gemini/antigravity-cli/` state too; only the `--out` file matters here.
- Part of the Slide/Video factory's **source+appraise** layer (`deck-standard/ARCHITECTURE.md`),
  shared by `[[html-deck]]` slides and the `video-editor` skill. Catalogued in `skills/CATALOG.md`.
