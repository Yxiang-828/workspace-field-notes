# Customizable Feature Matrix

Use this checklist to decide what to include. Prefer simple defaults, then add features the user actually needs.

## Pipeline

- Default `codex` worker preset for "you/the agent/Codex".
- Alternate `claude`, `agy-flash-high`, and `agy-pro-high` presets copied from `telegram-assistant/config/settings.json`.
- Owner-only `/worker` command to list and switch active workers.
- Custom command as argv array only when the user asks for a nonstandard CLI pipeline.
- Working directory.
- Stdin input, argv placeholders, input file, metadata file, or result file.
- Timeout and cancellation behavior.
- Environment variables inherited from `.env`, shared keys, and process env.
- Output chunk limit for Telegram messages.
- Full stdout/stderr archive path.

## Access And Authority

- Owner id via `OWNER_TELEGRAM_ID`.
- Owner username for readable mentions.
- User allowlist for private chats.
- Chat allowlist for groups.
- Owner-only commands for `/allow_user`, `/allow_chat`, `/sleep`, `/wake`, and config changes.
- Optional non-owner scope rules if the bot can work in shared groups.

## Telegram Behavior

- Private chat mode: every text message can trigger the pipeline.
- Group mode: require bot mention or reply by default.
- BotFather privacy disabled only when the bot must observe group context.
- `/whoami` to discover numeric ids.
- `/status` for queue and pipeline state.
- `/help` with terse operational commands.
- Busy message when queue is full.

## Context And Memory

- Store per-task metadata under `state/tasks/<task-id>/`.
- Optionally keep rolling group transcripts only if privacy is disabled and the user asked for context.
- Do not store secrets, raw tokens, or unrelated private messages.
- Summarize prior context before injecting it into a CLI prompt.

## Reporting

- Send a short status header plus output body.
- Chunk long Telegram messages below Telegram limits.
- Save full output on disk and mention the path.
- Redact token/key/secret values before any Telegram send or log write.
- Support structured result JSON when the CLI can produce it.

## Operations

- Long polling for local machines.
- Webhook only for hosted deployments with HTTPS.
- PowerShell run script for Windows.
- Optional detached runner, Task Scheduler task, or NSSM service for persistent use.
- Logs in `logs/`, mutable state in `state/`, static defaults in `config/`.

## Attachments

Add attachment support only when requested. For files/photos/documents:

- Download to the per-task directory.
- Pass paths through metadata JSON.
- Enforce file size limits.
- Avoid sending downloaded private files to unrelated CLIs unless the user asked.
