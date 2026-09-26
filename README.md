# Workspace field notes and working tools

This is a public export of reusable work from a long-running Windows agent workspace. It collects the methods that survived real projects and the small tools that implement them. The source workspace is much larger; this repository is the shareable slice, not a mirror of private robot, team, client, or personal material.

## Start here

| Area | What is here | Useful entry point |
| --- | --- | --- |
| Persistent agents | Backup, gated Git sync, restore, and a single durable work ledger | [agent-ops-hygiene](skills/agent-ops-hygiene/SKILL.md), [durable-work-ledger](skills/durable-work-ledger/SKILL.md) |
| Source reading | A full-read protocol with evidence for codebase audits | [repo-absorb](skills/repo-absorb/SKILL.md) |
| Telegram CLI agents | A scaffold and bridge for an owner-controlled bot around a local CLI worker | [build-telegram-cli-agent](skills/build-telegram-cli-agent/SKILL.md) |
| HTML slide decks | A themeable deck scaffold and PNG export through headless Chrome | [html-deck](skills/html-deck/SKILL.md) |
| Video editing | An explicit editorial decision log, timelines, and ffmpeg render helpers | [video-editor](skills/video-editor/SKILL.md) |
| Interface craft | A design and motion workflow with a static project checker | [motion-ui-workbench](skills/motion-ui-workbench/SKILL.md) |
| Network forensics | Distinguish a dead host from a route, link, or service failure | [host-liveness-forensics](skills/host-liveness-forensics/SKILL.md) |
| Image production | A local CLI workflow for bespoke imagery | [image-gen](skills/image-gen/SKILL.md) |
| Maps API | Small, explicit requests for geocoding, places, routes, and weather | [google-maps-platform](skills/google-maps-platform/SKILL.md) |

Each `SKILL.md` is an agent-facing operating guide. The scripts and templates beside it are ordinary source files. Read a skill's dependencies and setup before running its scripts. The video tools require ffmpeg and local source media; the Qwen voice helper additionally requires a separately supplied Docker image and voice library (`QWEN_VOICE_DIR`). The export contains no model weights, voices, recordings, credentials, runtime state, or generated media.

## Lessons behind the tools

The fuller account is in [LESSONS.md](LESSONS.md). These are the rules that recurred most often:

1. Durable behavior belongs in the host program. A reminder or backup that only exists in an agent's prompt disappears on a restart.
2. Publish only a checked state. Run the project's actual quality gate and scan staged files for secrets before any automated Git push.
3. Preserve decisions as data. Video edits, scheduled work, and audits need a record of *why* a choice was made, not only the final artifact.
4. Read the subsystem that owns a behavior in full. A search hit or README is a route into the code, not proof of how it works.
5. Verify the user's path through a tool. A passing unit test does not prove that a deck exports at the requested size or a rendered video reads well.

This repository is source to study. Some guides mention project names where the method was learned; those separate projects are not included here. No general license has been assigned to this collection.
