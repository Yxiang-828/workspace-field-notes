---
name: video-editor
description: >
  Edit a screen-recording demo into a polished video. Understands the recording
  cheaply (ffprobe + timecoded contact sheets + scene-change frames + Whisper
  transcript — not 100 raw frames), proposes a per-recording Edit Decision List
  (cuts, section markers with title cards + "awakening" SFX, music, transitions),
  then renders with ffmpeg. Use when the user sends a demo/recording to cut, add
  section markers/sound effects, trim dead air, or produce a final video.
license: MIT
---

# video-editor

## Scoped creative contract

This contract applies only to video work: honor the video factory, search the
local asset library and suitable stock before generating media, use image
generation for genuinely envisioned or unavailable art, inspect the rendered
cut, and hand off the useful video outputs and project recipe. It is
intentionally not an always-on workspace prompt.

## The AI Video Factory — run it for every cut (see PLAYBOOK.md)
An AI forgets; the factory makes every editorial decision an explicit, persistent artifact. **Three
artifacts** survive between passes: **1) Source Truth Panel** (`registry.py <dir>` — assets + ffprobe
facts + model tags role/energy/hero_moments/use_for; re-run merges), **2) Layered Timeline State**
(the spec; `factory.py timeline spec.json registry.json` = per-beat V/CAP/FX/OVL/SFX/RISK tracks),
**3) Decision Log** (`decisions.json` + `factory.py log` = why + rejected candidates).
**Gate:** `factory.py layers` lists ~21 compulsory layers (intake→objective→story→asset_analysis→
music_beat→pacing→attention→allocation→transitions→effects→overlays→color→sound→captions→memes→
comedy→voiceover→simulation→credits→validation→export_log). Scaffold `factory.py new decisions.json`,
fill **decision + reason per layer (justify skips)** + objective weights, `factory.py check`.
`vstudio render` is **blocked** until APPROVED (`--force` bypasses). Bounded retry loops (hook≤3,
meme/pacing≤2, transition≤1) avoid both early-quit and infinite loops. Tools = deterministic spine;
the model = judgment (tags, attention, simulation) written into the artifacts.

## Workspace — multi-project handling (input/output folders)
Projects are managed by `scripts/vstudio.py`; media lives in a local, visible store at
the user's video studio folder (override with `$VSTUDIO_ROOT`), while skill source stays tracked here.
Each project = `input/` (source), `work/` (ingest + intermediates), `output/` (renders),
a spec (`edit.json`/`story.json`), and `project.json` (status). Use it instead of dumping
files loose in Downloads:
```
py scripts/vstudio.py new <name> --source C:/path/rec.mp4   # scaffold + import source (edit)
py scripts/vstudio.py new <name> --kind montage --source song.mp3  # beat-synced montage
py scripts/vstudio.py list                                  # all projects + status
py scripts/vstudio.py ingest <name>                         # analyze (ingest.sh) -> work/
py scripts/vstudio.py render <name>                         # spec -> output/  (auto-dispatch)
py scripts/vstudio.py register <name> --output ... --edit ..# adopt existing files in place
```
Three project kinds → three renderers: **`edit`** (demo cleanup → `render.py`), **`story`**
(narrated multi-source → `storyboard.py`), **`montage`** (music-driven beat-synced edit →
`montage.py`). `new` writes the spec from `templates/{edit,story,montage}.template.json`
with absolute paths, so the renderer runs unchanged. See the studio folder's `README.md`.

## Which mode? (pick the lane first)
- **edit** — a screen recording / single take to clean up: trim dead air, section cards, light SFX/music. Source = the recording. → `render.py`
- **story** — explain something from many assets with a narration track (TTS). Source = a script + per-beat visuals. → `storyboard.py`
- **montage** — a *music-first* hype/highlight edit: cut a pool of clips ONTO a song's beats, effects on the drops. Source = the **song** + a folder of clips. The "edit" style (gaming/sports/AMV/reels). → `montage.py`
- **sequence** — a *hand-authored story cut*: an explicit ordered beat list (specific clips/images, each trimmed + placed + captioned + effected), music whose **drop aligns to a chosen beat**. Use when you know the narrative and which shot goes where (reveals, before/after, explainers with footage not TTS). → `sequence.py`

## How to understand a recording without drowning in frames
`bash ingest.sh <video>` → `<video>_ingest/`:
- `meta.txt` — ffprobe (duration/res/fps).
- `sheet_NN.png` — timecoded contact sheets (~40 thumbs each). **Read these, not raw frames** — one image = the whole visual arc.
- `scenes/` + `scenes.txt` — frames + timestamps where the screen actually changes.
- `audio.wav` — 16 kHz mono, ready for Whisper.
Then transcribe (Whisper, `--output_format all` → srt/vtt/txt/tsv/**json word-timings**) for a timestamped narration → richest signal for section starts and dead-air/fumble cuts. Read only a few full-res frames at decision points.
- `scenes.txt` is now `time<TAB>scene_score` (score `1.0`=hard cut, `0.1–0.3`=soft dissolve). The threshold auto-steps 0.4→0.25→0.12; if it still finds <3 cuts it writes a note: the source is a **continuous-animation / crossfade promo**, so derive sections from the **sheet + transcript**, not scene cuts. (Two prior gotchas are fixed: `-loglevel error` was suppressing `showinfo` → empty `scenes.txt`; and a Windows path inside `metadata=print:file=` breaks the filter parser.)
- **Read `ESSENCE.md` before any edit** — distilled extraction gotchas, a content-class triage (screen-recording vs motion-graphics promo vs montage), and the studied anatomy of a product-pitch promo (reusable VO-driven 8-beat skeleton). Append a dated entry whenever a real recording teaches something.
- **Read `FILMCRAFT.md` before authoring a spec — and storyboard first.** The actual craft (script the *meat* not fluff; Murch's Rule of Six; Eisenstein montage *collision*; shot-size ladder + camera-move/angle meaning; the anime 脚本→絵コンテ→layout pipeline; purposeful transition vocabulary). The non-negotiable: author a numbered **ekonte shot-list** (cut # · shot size · camera move · duration · VO · text · SFX · transition+why), budgeted to runtime and confirmed with the user, BEFORE rendering. Putting aesthetic slides under a voiceover is not editing.

## Edit model — the EDL (per recording)
Draft a readable `edit.json` from the analysis; user tweaks; one render applies it.
```json
{
  "source": "demo.mp4",
  "output": { "w": 1920, "h": 1080, "fps": 30, "file": "demo_final.mp4" },
  "music": "assets/music/bed-soft.mp3",
  "cuts":   [ { "from": "1:10.5", "to": "1:18.0", "why": "dead air" } ],
  "markers":[ { "at": "0:32", "title": "Live Log Wall", "kind": "feature", "sfx": "awaken" } ],
  "inserts":[ { "at": "0:00", "card": "intro", "title": "Matrix 4 Ops", "dur": 3 } ],
  "transitions": "xfade:0.4"
}
```
- **markers** = section starts: a title card (rendered via the `html-deck` engine for on-brand look) overlays ~2s + an "awakening" SFX plays at `at`.
- **cuts** are removed and segments concatenated; **inserts** add cards; **music** is mixed under at low gain; **transitions** crossfade segments.

## Media kit ("F1 tire" — prepared once, slapped on)
`assets/sfx/` (awaken/whoosh/click/success), `assets/music/`, `assets/cards/` (title-card templates via html-deck), intro/outro. The renderer composes these per the EDL.

## Render (built + verified)
`py scripts/render.py edit.json` (run **sandbox OFF** — cards load fonts) — ffmpeg pipeline: **cuts** (trim+concat) → **full-screen section cards** (rendered via `make-cards.mjs` in the html-deck aesthetic, faded in/out + SFX, auto time-remapped across cuts) → **music bed** (mixed low) → **1080p export**. Marker `sfx` is a name (looked up in `assets/sfx/`) or a path; times are SOURCE-time. Verified end-to-end (cut + section cards + sfx + music → correct duration, full-screen card overlay on screen).

`make-cards.mjs cards.json` renders `[{title,file}]` → 1920×1080 PNG section cards (Fraunces gradient, aurora, "SECTION" eyebrow). Swap the lower-third for cards is the default; needs `node_modules/puppeteer-core` (shared with html-deck pattern).

## Narrated story assembly (multi-source) — built + verified
`py scripts/storyboard.py story.json` — build a narrated story/explainer from **per-beat assets**: each beat = a visual (stock video/gif/image, cover-scaled to frame) sized to its narration length + caption + SFX, concatenated → 1080p. `story.json`: `{output, beats:[{vo,visual,text?,sfx?,pad?}]}`. Assets via the APIs (Pexels/Pixabay/Giphy/Freesound — search *specific* terms, not categories). Verified: 6-beat "Monday" story.
- **Narration = Qwen3-TTS** (one reference voice), via the baked docker image:
  `echo "line" | MSYS_NO_PATHCONV=1 docker run --rm -i -v "<winOutDir>:/out" qwen-tts:baked --model /bundle/models/qwen-talker-0.6b-base-Q4_K_M.gguf --codec /bundle/models/qwen-tokenizer-12hz-Q4_K_M.gguf --lang english --ref-wav /bundle/voice_actors/english/<voice>.wav --ref-text …/<voice>.txt --seed 281 --format wav16 -o /out/x.wav`
  (`MSYS_NO_PATHCONV=1` stops Git-Bash mangling `/bundle/…`). Voices: 0_intro…7_juilliard. Runs CPU (~6× realtime); Vulkan/AMD-GPU only if the GPU is exposed (Docker-on-Windows doesn't pass AMD through → CPU).

## Beat-synced montage / "edit" mode (music-driven) — built + verified
The pro workflow is **music-first**: scan the song → cut clips ONTO its beats → pace by
section → stack the "hit" combo on the drops. Two scripts implement it.

**1. `py scripts/beatmap.py <song.mp3|clip.mp4> [out.beats.json]`** — scan the song's rhythm.
Emits `{bpm, beat_period, beats[], downbeats[], onsets[], drops[], beat_energy[], sections[]}`.
Engine = **librosa** (`pip install librosa soundfile`; installed, works on Py3.13/numpy2);
falls back to an **ffmpeg `astats` energy timeline** if librosa is missing (onsets+drops+guessed
grid, no true BPM). `beats` = the cut grid; `downbeats` = bar starts (hero cuts); `onsets` =
transients to snap hits to; `drops` = energy surges (chorus/drop — stack effects here);
`sections` = low/mid/high energy spans that drive pacing. Verified on a real track (95.7 BPM).

**2. `py scripts/montage.py montage.json`** (run **sandbox OFF**) — render the montage.
Pulls clips from `clips[]`/`clips_dir`, builds cut points from the beat grid (`grid`:
`beat`|`downbeat`|`half`), **paces** (holds 2 beats/cut in `low` sections, cuts every beat in
`high`), assigns a random in-point of a clip per slot ("cut to the essence"), applies effects,
concatenates, then a final pass adds **grade + vignette + captions + the music as master audio**
(clip audio dropped; music faded out). Verified end-to-end (25 cuts over a drop section, cinematic
grade, DROP caption, ~23 s render).

### Effects vocabulary (montage.json `effects`, each `"all"|"drop"|"none"` or bool)
| Effect | What it does | ffmpeg under the hood |
|---|---|---|
| `zoom_punch` | quick push-in easing back on each cut (bigger on drops) | `zoompan` z-ease `1.14→1` (`1.30→1` on drops) |
| `flash` | white flash-in at the cut | `fade=t=in:color=white:d=0.07` |
| `shake` | rhythmic camera shake | `crop` sine-offset x/y → `scale` back |
| `rgb` | chromatic/RGB split (glitch energy) | `rgbashift=rh=5:bh=-5` |
| `slowmo` (part of `hit`) | hero shot slowed to fill a drop slot, kept in sync | shorter source snippet × `setpts=1.5*PTS` |
| `hit` | the signature drop combo = shake + rgb + big punch + slow-mo on one beat | the above, gated to `drops` |
| `grade` | global color look: `cinematic`/`warm`/`cold`/`vivid`/`noir`/`vintage` | `eq`+`curves`+`colorbalance` (final pass) |
| `vignette`, `grain` | darkened corners / film grain | `vignette`, `noise=allf=t` |
Pacing rules baked in: ~1 cut/beat in hype, 1 cut/2-beats in calm, the drop gets a slow-mo hero
shot + the hit. `min_cut` caps cut speed; `grid:"half"` = double-time hype.

### Music for edits — what works + how an AI gets it
Best edit genres: **phonk / drift-phonk, trap, hardstyle/hardwave, EDM/future-bass, hip-hop
instrumentals, lo-fi** — anything with a clear beat + a build→drop. Sourcing reality for an AI
(no GUI apps): **Jamendo API** (real search w/ genre+tempo filters + CC license + download URL;
free `JAMENDO_CLIENT_ID` from devportal.jamendo.com) and **archive.org via yt-dlp** (CC/netlabel,
no key) are the scriptable lanes — `bash asset-library/scripts/fetch-music.sh` pulls both into
`~/.claude/asset-library/music/`. Pixabay has **no** music API (key is images/video only) and its
CDN is hotlink-blocked; FreePD shut down 2025; Epidemic/Artlist/Uppbeat are subscription/GUI only.
**License:** stock music is mostly CC-BY (credit the artist) — fine for personal edits; check per
track before publishing/monetizing. Viral edits often use copyrighted songs (claimed/muted if exported).

## Scripted story cut (`sequence.py`) — built + verified
`py scripts/sequence.py story.json` (run **sandbox OFF**) — render a hand-authored ordered cut.
⚠️ **Set `output.file` to a Temp/scratch dir, NOT inside the OneDrive-synced workspace** — the Qwen
TTS `docker run -v` mount of a OneDrive path silently writes 0-byte wavs and the audio mux dies.
Render to Temp, then copy the final mp4 into `decks/`. (see memory `video-render-onedrive-docker`)
Each **beat** is one of:
- **media** `{src, in, dur, crop, speed, text, fx, sfx, overlay}` — video trimmed in→in+dur×speed, or image.
  `"full":true` = **fast-forward the ENTIRE remaining clip into the beat's `dur`** (speed auto-computed) — show a long demo in full, sped up, instead of slicing it.
  `"native_audio":1.2` (or `true`=1.3) = **keep THIS clip's own audio** (a UI/voice sample) and mix it into the final at that volume. Give the beat **no `vo`** so the sample dominates (narration pauses there); use speed 1.0 so the sample isn't pitch-bent.
- **title** `{card, sub, dur}` / **credits** `{credits:[lines], dur}`.
- **split** `{split:[A,B], ins:[a,b], layout:"v"|"h", crops:[..], text}` — **side-by-side** of two
  sources (e.g. PC avatar over phone chat); `v`=stacked top/bottom, `h`=left/right.
- **narration** — add `"vo":"spoken line"` to ANY beat → **Qwen3-TTS** (voice-clone, baked docker
  `qwen-tts:baked`) synthesizes it and the **beat duration is driven by the VO length** (+`pad`).
  Top-level `"voice"` (e.g. `3_warm`) picks the reference voice; music auto-**ducks** to `"duck"`
  (default 0.26) under narration. VO is the master audio; SFX at 0.6; all resampled + mixed.

Final pass: grade + vignette + music (drop-aligned) + VO + SFX. **Music drop alignment:**
`music_drop` (drop time from `beatmap.py`) + `align_beat` (index) shifts the song so the drop lands
on that beat (the reveal). `crop`: `left|center|right`. `fx`: `kenburns` (images), `punch`, `flash`,
`shake`, `slowmo`. `overlay`: `{src, mode:"screen"|"add"|"alpha", opacity}` composites particles/
light-leak/sparkle (from `~/.claude/asset-library/fx-overlays/`). `sfx`: name (globbed across
`assets/sfx`, `fx-sfx`, `sfx-freesound`) or path.
Verified: Aiko **"A New Form"** — a **narrated** ~69 s vertical piece (18 beats, Qwen3-TTS voice,
drop on the VRM reveal, side-by-side phone+desktop demo, spell overlay, credits). Workflow:
`ingest.sh` → `registry.py` (Source Truth) → annotate → author beats + VO → align drop → render.

## More editing levers (for richer cuts on raw footage)
A finished, single-take VO demo needs light editing (trim + section cards). For raw material, also available: **captions/subtitles** from the Whisper transcript, **B-roll inserts** from the asset library, **zoom/punch-in** on key moments, **music-driven pacing**, **reaction GIFs/memes** overlay. Add as EDL fields / future render passes.

## Notes
- ffmpeg at `C:\ffmpeg\bin`. drawtext font: `C\:/Windows/Fonts/consola.ttf`.
- Markers can be auto-detected (transcript phrase + scene change) or explicitly called out by the user; always confirm the proposed EDL before rendering.
