# The AI Video Factory — architecture (so the AI stops forgetting)

A human editor runs on intuition + memory: *"this drags… drop a meme here… beat lands there."* An AI
forgets — prompt it "make it more engaging" and it collapses, because those decisions only ever lived
in the editor's head. So we don't build an *editor*; we build a **factory**: every invisible decision
is converted into an **explicit, persistent artifact** that later passes can read and write.

> Assets → Decision Layers → Decision Memory → Timeline State → Assembly → Validation → Decision Log → Video

## The split that makes it AI-native
- **Tools = the deterministic spine.** `registry.py` (index/ffprobe), `beatmap.py` (beats/drops),
  `sequence.py`/`montage.py`/`render.py`/`storyboard.py` (assemble), `factory.py` (gate/validate/report).
- **The model (me) = the judgment**, written *into* the artifacts: semantic asset tags, story
  skeleton, attention/retention prediction, viewer simulation, every decision + its reason.
- Judgment that an LLM does (not a faked ML score) is recorded as text in the artifacts, so it
  survives the next pass. The factory is the memory.

## The 3 persistent artifacts (the external brain)
1. **Source Truth Panel** — `registry.py <dir> registry.json`. What exists: every asset with
   ffprobe facts (type/dur/res/orientation/audio) + model tags (role, energy, emotion, movement,
   face, humor, quality, topic, **hero_moments**, **use_for**). Re-running **merges** — tags persist.
2. **Layered Timeline State** — the `sequence`/`montage` spec, viewed as multi-track per-beat state:
   `factory.py timeline spec.json registry.json` prints, per beat, the V/CAP/FX/OVL/SFX/RISK tracks
   (V resolves to the registry role). The timeline *is* working memory — what happens at every second.
3. **Decision Log** — `decisions.json` (+ `factory.py log` → markdown). Why each choice was made,
   **including rejected candidates and why**. Next time = *"do what worked,"* not start from zero.

## The production line (gate order) — `factory.py layers`
intake · objective(+weights) · story · asset_analysis · music_beat · pacing · **attention** ·
allocation · transitions · effects · overlays · color · sound · captions · memes · comedy ·
voiceover · **simulation** · credits · validation · export_log.

Each layer **passes** only with `applies` (true/false) + a non-empty `reason` (a SKIP must be
justified) + a `decision` when it applies. `intake` also requires the registry artifact to exist;
`objective` requires ≥1 priority weight. `attention` (per-beat retention risk + fix) and `simulation`
(3–4 viewer personas → predicted drop-off) are where I role-play the audience and record it.

## Bounded optimization (don't loop forever, don't quit early)
Only revisit **flagged** regions, with caps: high drop-off → retry hook (≤3); boredom spike → retry
meme/pacing (≤2); beat mismatch → retry transition (≤1). The gate prevents quitting early
(unresolved layers block the render); the caps prevent infinite loops. `pass` counts iterations.

## The gate is enforced
`vstudio render` runs `factory._validate` and **refuses** until the sheet is APPROVED
(`--force` bypasses for throwaways). The persistent product cannot ship un-reasoned.

## Commands
```
registry.py <dir> [registry.json] [--beats]      # artifact #1 (merges/preserves tags)
factory.py layers                                # the production line
factory.py new   decisions.json                  # scaffold (objective weights + artifact slots + layers)
factory.py check decisions.json                  # the gate (exit 1 until APPROVED)
factory.py timeline spec.json [registry.json]    # artifact #2 (layered per-beat state)
factory.py log   decisions.json [out.md]         # artifact #3 (decision log, with rejections)
factory.py report decisions.json                 # quick pass summary
```

## Render modes (chosen at `story`/`allocation`)
edit (`render.py`) · story (`storyboard.py`+Qwen3-TTS) · montage (`montage.py`, beat-grid pool) ·
sequence (`sequence.py`, hand-authored timeline w/ drop-align + per-beat crop/speed/caption/fx/overlay/sfx).

## Asset fetchers (use every API on purpose)
`asset-library/scripts/`: `fetch-music.sh` (Jamendo+archive.org beds) · `fetch-fx.sh` (Freesound SFX
+ Pixabay overlays) · `fetch-media.sh` (Pexels/Pixabay stock + Giphy reactions).

## Prioritization & emphasis (the lesson that's easy to forget)
**Beats are NOT equal — and the default failure mode is treating them as if they are.** Every video
has 1-2 **hero features** (the reason it exists; e.g. *the demo*). The edit must show *focus*:
- The hero gets **disproportionate screen time** and **emphasis**; connective/secondary beats get
  compressed. Equal time to everything = no emphasis = flat.
- **Emphasis tools:** slow-mo, a **hold**, a **punch-in**, and crucially — **drop to REAL-TIME
  inside a fast section** on its single most important moment. A demo can fast-forward the boring
  bulk *and still slow to real-time on the actual payoff* (the type→respond, the click that works).
- A uniform speed (all-fast OR all-slow) is almost always wrong for a hero feature. Fast = "here's
  the gist"; the real-time/slow beat = "watch *this* specifically." You need both, on purpose.
- Rule of thumb: if you can't point to the 3-6 seconds the whole video is *for*, and confirm they're
  the slowest/most-held moment, you haven't prioritized yet.

This is enforced as the `prioritize` gate layer: name the hero, confirm it gets the most time +
an emphasis moment, confirm the rest is compressed.

## Principle
Decide on purpose; skip on purpose; record why. Three artifacts survive between passes, so the AI
behaves less like a chatbot and more like a post-production studio. **And: focus beats fairness —
spend the time where the value is.**
