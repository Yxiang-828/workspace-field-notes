# ESSENCE — distilled lessons for future video editing

Living notebook of what actually works when understanding + cutting video on this machine.
Append a dated entry each time a real recording teaches something. Read this before an edit.

> **GATE (2026-06-26): script + storyboard BEFORE you render.** Aesthetics ≠ a video. Before
> authoring any `sequence.json`/`edit.json`, work **`FILMCRAFT.md`** — pick a beat-frame, write
> every line as *demonstrated proof* not asserted benefit, then author a numbered **ekonte
> shot-list** (cut # · shot size · camera move · duration · VO · text · SFX · transition+why)
> budgeted to runtime, and confirm it with the user. Cut for emotion (Murch), collide shots for
> meaning (Eisenstein), vary transitions on purpose, choreograph an energy curve. The Agora-promo
> post-mortem in FILMCRAFT §6 is the cautionary tale: pretty slides under a VO is fluff, not craft.

---

## 1. Extraction / understanding pipeline (ffmpeg + Whisper)

What to pull from any source video, and the gotchas learned the hard way:

| Artifact | Command essence | Why |
|---|---|---|
| **Probe** | `ffprobe -show_entries format=duration,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels` | Lane decision (res/fps/audio?) before anything else. |
| **Voice (lossless)** | `ffmpeg -i in -vn -c:a copy voice_original.m4a` | Keep the original audio bit-for-bit for re-mux. |
| **Voice (editable)** | `ffmpeg -i in -vn -ac 2 -ar 48000 voice_48k.wav` | 48 k stereo WAV to edit/duck/mix. |
| **Whisper audio** | `ffmpeg -i in -vn -ac 1 -ar 16000 audio.wav` | 16 k mono is all Whisper needs. |
| **Captions** | `whisper audio.wav --model base --language en --output_format all` | `all` → srt+vtt+txt+tsv+**json (word timings)**. The transcript is the richest editorial signal. |
| **Contact sheet** | `fps=1/3 … drawtext pts → tile=8xN` | ~1 thumb / 3 s = the whole arc in one readable image. Read this, never 100 raw frames. |
| **Scene cuts** | `select='gt(scene,T)',metadata=print` (see gotchas) | Hard-cut timestamps + scores. |
| **Decision frames** | `fps=1/3 … drawtext pts` full-res | Only a few, at the moments the sheet/transcript flag. |

### Gotchas burned in (2026-06-26)

1. **`-loglevel error` silently kills `showinfo`.** `showinfo` logs at INFO level; with
   `-loglevel error` its output is suppressed, so the old `ingest.sh` wrote an **empty
   `scenes.txt` on every video** while still saving frames — a silent failure that looked
   like "no scene changes." **Fix:** drive scene detection with `metadata=print` at
   `-loglevel info` and capture **stderr** (`2>file`). Now fixed in `ingest.sh`.
2. **Never put a Windows path inside an ffmpeg filter arg.** `metadata=print:file=C:/…`
   breaks the parser — the `:` is the filter's own arg separator. Pipe to stderr and
   redirect in the shell instead of `file=`.
3. **Scene detection is useless on polished promos / motion-graphics.** They crossfade
   between every scene, so frame-to-frame deltas never exceed even 0.12 — `scene` returns
   ~0 hard cuts despite obviously distinct "scenes." Detect this (few/no cuts) and **derive
   section boundaries from the contact sheet + narration beats instead.** `ingest.sh` now
   steps the threshold 0.4→0.25→0.12 and writes a flag note when it finds <3 cuts.
4. **Keep the scene_score column.** `time<TAB>score` lets you tell a real cut
   (`1.000000`) from a soft dissolve (`0.12–0.24`) at a glance.

### Content-class triage (decide first — it changes everything)
- **Screen recording / single take** → scene cuts + dead-air trims are real signal → `render.py` (edit lane).
- **Motion-graphics promo / animated explainer** → scene cuts are noise; the **transcript IS
  the timeline**. Each narration sentence ≈ one section. Study it as a *reference to imitate*,
  not footage to trim.
- **Music video / montage source** → ignore transcript; `beatmap.py` is the timeline.

---

## 2. Anatomy of a strong 72 s product-pitch promo

Studied: **CareerLingo** promo (`video_2026-06-26_16-34-31.mp4`, 72 s, 1064×620@60, voiced).
A Duolingo-for-careers app with a penguin mascot "PIP". Continuous animated UI on phone
mockups, soft dissolves throughout, two hard cuts only (at the closing logo card). This is a
clean template for an app/product launch promo — reuse the *structure*, not the assets.

### The narrative spine (≈ one section per narration sentence)
1. **Relatable-pain hook, as a question** — *"If building your career felt less like guessing
   and more like learning a language on Duolingo…"* (0–5 s). Frames the problem AND the
   analogy that makes the product instantly legible. Text-on-clean-bg, no product yet.
2. **Name + reveal + mascot** — *"introducing CareerLingo. Meet PIP, your career guide."*
   (6–11 s). Logo lands on the first soft cut; mascot gives a face to trust.
3. **Restate the user's problem in their words** — *"You know the career you want… but you
   don't know where to start."* (14–19 s). Earns the "here's how" that follows.
4. **Core mechanic, as a momentum list** — *"turns your goal into daily missions. Pick a
   path, start today's mission, get instant AI feedback, earn XP, build momentum"* (21–36 s).
   Verb-led, second person, escalating — each phrase = one animated UI beat on the phone.
5. **The turn / bigger vision** — *"but CareerLingo doesn't stop at learning…"* (36 s). The
   pivot that lifts it from "another course app" to a category. Marked visually by the
   "Not just learning. Visible career action." card.
6. **Second feature cluster** — *"learn what the role needs, build proof, reach out and
   network, share milestones, get noticed."* (37–48 s). Same list cadence, outcome-oriented.
7. **The "brain" / AI payoff** — *"Your career brain learns with you, ask anything. Store
   your progress."* (49–58 s) → abstract **hero visual** (a glowing neural orb) for the
   intangible feature. Use abstract motion-graphics when there's no UI to show.
8. **Thesis + logo** — *"careers aren't built by watching lessons, they're built by taking
   visible action."* → final CareerLingo card (the only hard cuts in the piece).

### Transferable craft rules
- **Open with the pain as a question + a familiar analogy** ("like Duolingo, but for X").
  The viewer understands the product before you've shown it.
- **Narration drives length.** Each sentence is a section; the visual just illustrates the
  words. Write the VO first, storyboard to it (this is exactly the `storyboard.py`/`sequence.py`
  `vo`-driven beat model — narration length sets beat duration).
- **List cadence builds momentum.** Short verb phrases ("Pick a path, start a mission, get
  feedback, earn XP") feel like progress. Mirror the rhythm in the cuts.
- **A "but it doesn't stop there" turn** mid-video re-hooks attention right where promos sag.
- **Give intangibles a hero visual.** "AI brain" → an abstract orb/particle shot, not a UI.
- **A mascot is cheap trust + continuity** across otherwise unrelated UI shots.
- **Soft dissolves everywhere, hard cut only for the logo** = calm, premium feel. (Our
  scene-detector reads this as "no cuts" — that's the *style working*, not missing data.)
- **End on the thesis line, then the logo.** Leave the one sentence you want remembered.

### Reusing this as a generator
This maps 1:1 onto a `sequence.py`/`storyboard.py` spec: 8 `vo`-bearing beats, each beat a
phone-mockup or text card sized to its narration, soft `xfade` between beats, a mascot overlay,
an abstract orb beat for the "brain", music ducked under VO, logo card with the only hard cut.
When asked for a product/app promo, start from this skeleton.
