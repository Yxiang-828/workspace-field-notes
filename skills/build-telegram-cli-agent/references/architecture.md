# Telegram CLI Agent Architecture

Use this architecture for local Telegram agents that run a selected command-line pipeline.

## Reference Pattern

The workspace reference is `telegram-assistant/`. Inspect it when present, especially:

- `README.md` for the receive/send lifeline, setup, queues, and owner commands.
- `.env.example` for token and owner env names.
- `bot/config.py` for `.env` plus process env loading.
- `bot/app.py` for long polling, command handlers, queueing, group mention behavior, and owner gates.
- `bot/dispatch.py` for the result-file handoff pattern and CLI subprocess execution.

Do not read or print `telegram-assistant/.env`.

## Minimal Runtime Shape

Build these layers:

1. `config`: load `.env`, `~/.alibaba/keys.env`, and process env; parse `settings.json`; expose redaction helpers.
2. `telegram app`: create a `python-telegram-bot` `Application`, register commands, run long polling.
3. `access gate`: owner id always allowed; optional user/chat allowlists; ignore untrusted group messages.
4. `trigger gate`: in groups, act only on bot mention or reply unless the user explicitly wants every message.
5. `queue`: process one request at a time by default; reject or defer overflow.
6. `pipeline runner`: run the selected CLI with `subprocess` using argv arrays, timeout, cwd, inherited env, and redacted logs.
7. `reporter`: chunk long output for Telegram; save full stdout/stderr and metadata under `state/tasks/` or `logs/`.

## Default Worker Presets

In this workspace, do not ask "which CLI pipeline?" when the user clearly means the local agent. Default to Codex:

- `codex`: `codex exec -c model=gpt-5.5 -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -`
- `claude`: `claude --model opus --effort high -p --dangerously-skip-permissions`
- `agy-flash-high`: `agy --dangerously-skip-permissions --print-timeout 30m --model gemini-3.5-flash -p {prompt}`
- `agy-pro-high`: `agy --dangerously-skip-permissions --print-timeout 30m --model gemini-3.1-pro -p {prompt}`

Copy updated command details from `telegram-assistant/config/settings.json` if that file changes.

## Telegram Setup Stop Points

Stop and ask for user action when:

- No bot token exists under `TELEGRAM_BOT_TOKEN`, `TSUKUMO_TG_BOT_TOKEN`, or a user-selected token env var.
- The bot needs group context and BotFather privacy has not been disabled.
- Owner controls are required but `OWNER_TELEGRAM_ID` is missing.
- The target working directory is unclear and cannot be safely inferred from the current project.

BotFather instructions to give:

1. Open Telegram and message `@BotFather`.
2. Send `/newbot`.
3. Choose a display name and a username ending in `bot`.
4. Put the token in `.env` or `~/.alibaba/keys.env`; never paste it in chat.
5. For groups, run `/setprivacy`, select the bot, and disable privacy if contextual group reading is needed.

Official references to consult for details:

- Telegram bot features: `https://core.telegram.org/bots/features`
- Telegram bots FAQ: `https://core.telegram.org/bots/faq`
- python-telegram-bot docs: `https://docs.python-telegram-bot.org/`

## Pipeline Handoff

Prefer stdin for natural language requests. Prefer file/result placeholders when the worker is an agent CLI, a long-running process, or returns structured output:

- `{message}` or `{input}`: raw Telegram request text.
- `{input_file}`: path containing raw request text.
- `{metadata_file}`: JSON containing chat id, user id, message id, username, and task id.
- `{result_file}`: JSON file the worker may write.
- `{task_dir}`: per-request scratch/log directory.

For agent CLIs, tell the worker to write JSON to `TELEGRAM_AGENT_RESULT_FILE` with fields like `status`, `summary`, and `body`. Parse that file first; fall back to stdout/stderr.

## Windows Defaults

Use PowerShell launchers, not Linux-only service scripts. A minimal `run.ps1` should:

1. `Set-Location $PSScriptRoot`
2. install `requirements.txt` with `py -m pip install --user -r requirements.txt`
3. run `py -m bot`

Add detached Task Scheduler or NSSM service setup only when requested.
