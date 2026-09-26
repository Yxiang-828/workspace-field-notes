---
name: build-telegram-cli-agent
description: Build an end-to-end Telegram bot/agent that runs a selected local CLI pipeline such as codex, claude, agy, ffmpeg, Python scripts, shell tools, or repo-specific commands. Use when the user asks to create, scaffold, customize, harden, or debug a Telegram assistant/bot that accepts Telegram messages and dispatches them to a configurable command-line worker with env loading, owner gates, queues, logs, and setup instructions.
---

# Build Telegram CLI Agent

Build a real Telegram long-polling bot project that fronts a selected CLI pipeline. Treat it as a local automation bridge: Telegram receives the request, the bot gates it, runs the configured command, and returns a concise result with logs saved on disk.

## Core Rules

- Build the runnable project unless the user explicitly asks only for advice.
- Load runtime secrets from the target `.env`, process env, and `C:/Users/xiang/.alibaba/keys.env`; never print, echo, log, or paste secret values.
- Use the local `telegram-assistant/` project as the reference pattern when it exists, but do not read its real `.env`.
- Stop before claiming completion if the Telegram bot token or owner identity is missing.
- Prefer long polling for local Windows machines; do not require public webhooks unless the user asks for production hosting.

## Workflow

1. Scope the CLI pipeline.
   - Identify the exact command, working directory, input mode, timeout, and expected output.
   - If the user says "you", "yourself", "the agent", "Codex", or does not name a worker in this workspace, default to the `codex` preset copied from `telegram-assistant/config/settings.json`: `codex exec ... -` with stdin prompt handoff, 1800s timeout, and the current workspace as `cwd`.
   - Treat `claude`, `agy-flash-high`, and `agy-pro-high` as available alternate worker presets. Ask only if the user wants a non-Codex default or a truly custom command.
   - Ask a concise blocking question only if the trust boundary, target working directory, or custom command is unclear.
   - Default to stdin for message text; use `{input}`, `{input_file}`, `{metadata_file}`, `{result_file}`, or `{task_dir}` placeholders when argv/file handoff is better.

2. Read the right references.
   - Read `references/architecture.md` before building.
   - Read `references/features.md` when choosing custom controls, queues, logs, workspaces, attachments, or result formats.
   - Read `references/security.md` before allowing arbitrary commands, group usage, secrets, mutations, or non-owner access.
   - If `telegram-assistant/` exists in the workspace, inspect `README.md`, `.env.example`, `bot/config.py`, `bot/app.py`, and `bot/dispatch.py` for local conventions.

3. Apply the BotFather stop gate.
   - If no usable token is available by env name, target `.env`, or `C:/Users/xiang/.alibaba/keys.env`, stop and tell the user:
     1. Open Telegram and message `@BotFather`.
     2. Send `/newbot`, choose a display name, then choose a username ending in `bot`.
     3. Put the token in the target project `.env` as `TELEGRAM_BOT_TOKEN=...`, or in `C:/Users/xiang/.alibaba/keys.env` as `TSUKUMO_TG_BOT_TOKEN=...`.
     4. Do not paste the token into chat.
     5. If the bot must read group context, use `@BotFather` `/setprivacy`, select the bot, and disable privacy.
   - If `OWNER_TELEGRAM_ID` is missing, scaffold the project if useful, but tell the user to start the bot, DM it `/whoami`, put the numeric id in `.env`, and restart before using owner-only features.

4. Scaffold or adapt the project.
   - For a new project, run:
     ```powershell
     python <skill-dir>\scripts\scaffold_telegram_cli_agent.py --name "<name>" --output "<target-dir>"
     ```
   - This defaults to the `codex` worker preset and the directory where the scaffold command is run as `cwd`.
   - Use `--preset claude`, `--preset agy-flash-high`, or `--preset agy-pro-high` to choose another reference worker.
   - Use `--pipeline "<command>"` only for a custom command.
   - For a JSON argv command, pass `--pipeline '["codex","exec","-"]'` style input.
   - Use `--no-stdin` when the pipeline should receive input only through placeholders.
   - For existing projects, copy the same architecture instead of forcing the scaffold.

5. Customize intentionally.
   - Configure owner id, allowlisted users/chats, group mention behavior, queue limit, busy message, timeout, output chunking, logging, and pipeline env.
   - For agent CLIs that do not produce clean stdout, use the result-file pattern: set `TELEGRAM_AGENT_RESULT_FILE` and make the worker write JSON there.
   - Keep commands as argv arrays with `shell=False` unless the user specifically needs shell behavior.

6. Verify before handoff.
   - Run Python syntax checks on generated files.
   - Run `python -m bot --check` with non-secret test env values when real env is not available.
   - Do not start a live Telegram polling loop unless the token exists and the user is ready to interact with the bot.
   - If started, verify `/whoami`, `/status`, one allowed request, one denied request, and one timeout/error path.
   - Always do an interaction dry-run: act as a fresh agent using this skill against the user's current request, identify the first blocking stop gate, and ask the exact concise question or BotFather instruction the user would see. If the dry-run does not stop on missing pipeline/token/owner/group-privacy data, tighten the skill before final handoff.

7. Hand off the exact next action.
   - Report the project path, command to run, env variable names still needed, and Telegram-side steps still pending.
   - Mention that secrets were not printed.
   - Do not commit or push unless the user asks.

## Scaffold Script

Use `scripts/scaffold_telegram_cli_agent.py` for the standard Python implementation. It generates:

- `bot/` with config/env loading, Telegram handlers, owner gates, queueing, subprocess execution, and logging.
- `config/settings.json` for worker presets, active worker selection, and feature defaults.
- `config/allowed.json` for user/chat allowlists.
- `.env.example`, `requirements.txt`, `.gitignore`, and `run.ps1`.

The generated bot loads `C:/Users/xiang/.alibaba/keys.env` automatically and falls back to `TSUKUMO_TG_BOT_TOKEN` for the Telegram token, while still allowing project-specific `.env` overrides. It exposes owner-only `/worker` to list or switch between `codex`, `claude`, `agy-flash-high`, `agy-pro-high`, and any custom pipeline generated with `--pipeline`.
