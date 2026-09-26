# video-editor — studied references (2026-06-15)

Cloned to `claude-workspace/references/video/` (gitignored) unless noted. What each is, and what this skill takes from it.

| Ref | What it is | License | Take into our skill |
|---|---|---|---|
| **FireRedTeam/FireRed-OpenStoryline** (2.9k★) | SOTA **intention-driven video-editing agent** — NL → LLM planning → tool orchestration. Smart media search, script gen w/ few-shot style transfer, beat-synced BGM, conversational refinement, AI transition generation. | Apache-2.0 | **The north star.** Its **"Editing Skill Archiving"** (save a full edit workflow as a reusable Skill, swap media, replay the style) = exactly our EDL + per-recording-but-reusable idea. Adopt: style-as-skill, beat-sync, conversational tweak loop. |
| **GoogleCloudPlatform/genmedia-video-editor** (SKILL.md only) | A real **video-editor SKILL.md** built on ffmpeg tool primitives + Veo generation. | Apache-2.0 | Concrete **ffmpeg recipes**: overlay image-on-video, concat, 2-pass GIF (fps=15, scale 0.33), combine audio+video, get_media_info. Mirror its skill structure + recipes in `render.py`. |
| **scosman/videowright** (TS) | Coding-agent tool to **build animated explainer/demo videos from a prompt**; AI voiceovers with **auto-sync timing**, SFX/music mixing, 6 visual styles, **deterministic frame-by-frame MP4 export** (no dropped frames). | MIT | The **render-quality bar**: deterministic export, voiceover↔timing sync, multi-source audio mix. Study its sync + export approach. |
| **HKUDS/VideoAgent** (755★, 52MB) | All-in-one **agentic framework for video understanding, editing & remaking**; orchestrates vendored tools (seed-vc, CosyVoice, DiffSinger, ImageBind). | MIT | Reference for the **understanding/analysis** side (how an agent reasons over a video) and tool-orchestration patterns. Heavier/research. |
| **arnofaure/free-sfx** | A web **SFX player**; audio is **streamed from `studionora.ca/Download/s-f-x/MP3/<category>/…`** (Alert, … categories), not stored in the repo. | repo: none; audio host: unstated ("100% free") | An **index of categorized SFX URLs** I can harvest (e.g. impact/alert). **Licensing unclear → caution**; prefer Kenney CC0 for anything shipped. |

## Synthesis → what our `video-editor` becomes
FireRed's **archivable editing-skill** model + our **EDL** + videowright's **deterministic render & voiceover-sync** + the **GCP ffmpeg recipes** + **local Whisper** (done) + **CC0 SFX** (Kenney done; free-sfx/Pixabay/BVKER as extra sources). Pipeline stays: ingest (cheap read) → analyze (transcript+scenes) → propose EDL → confirm → render. The references confirm the design and supply concrete render recipes to copy rather than reinvent.
