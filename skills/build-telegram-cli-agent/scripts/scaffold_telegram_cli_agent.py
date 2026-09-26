#!/usr/bin/env python3
"""Scaffold a Telegram bot that fronts a configurable local CLI pipeline."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import textwrap
from pathlib import Path


def parse_cmd(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        raise ValueError("pipeline command is empty")
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
            raise ValueError("--pipeline JSON must be a list of strings")
        return parsed
    return shlex.split(raw, posix=(os.name != "nt"))


def write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8", newline="\n")


AGENT_INPUT_TEMPLATE = """You are running as a Telegram-controlled local CLI agent.

Request:
{message}

Metadata file: {metadata_file}
Task directory: {task_dir}
Result file: {result_file}

Do the work requested. When finished, write UTF-8 JSON to the result file:
{
  "status": "success" | "needs_input" | "issue",
  "summary": "one concise line",
  "body": "Telegram-safe response body with evidence and no secrets"
}

If the request is ambiguous, ask one specific question with status "needs_input".
Never print, echo, or write secret values from environment variables.
"""


def preset_workers(cwd: str) -> dict[str, dict]:
    """Worker presets copied from the local telegram-assistant pattern."""
    return {
        "codex": {
            "label": "codex - gpt-5.5 xhigh",
            "cmd": [
                "codex",
                "exec",
                "-c",
                "model=gpt-5.5",
                "-c",
                "model_reasoning_effort=xhigh",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "-",
            ],
            "stdin": True,
            "input_template": AGENT_INPUT_TEMPLATE,
            "cwd": cwd,
            "timeout_seconds": 1800,
        },
        "claude": {
            "label": "claude - Opus high",
            "cmd": [
                "claude",
                "--model",
                "opus",
                "--effort",
                "high",
                "-p",
                "--dangerously-skip-permissions",
            ],
            "stdin": True,
            "input_template": AGENT_INPUT_TEMPLATE,
            "cwd": cwd,
            "timeout_seconds": 1800,
        },
        "agy-flash-high": {
            "label": "agy - Gemini Flash high",
            "cmd": [
                "agy",
                "--dangerously-skip-permissions",
                "--print-timeout",
                "30m",
                "--model",
                "gemini-3.5-flash",
                "-p",
                "{prompt}",
            ],
            "stdin": False,
            "input_template": AGENT_INPUT_TEMPLATE,
            "cwd": cwd,
            "timeout_seconds": 1800,
        },
        "agy-pro-high": {
            "label": "agy - Gemini Pro high",
            "cmd": [
                "agy",
                "--dangerously-skip-permissions",
                "--print-timeout",
                "30m",
                "--model",
                "gemini-3.1-pro",
                "-p",
                "{prompt}",
            ],
            "stdin": False,
            "input_template": AGENT_INPUT_TEMPLATE,
            "cwd": cwd,
            "timeout_seconds": 1800,
        },
    }


CONFIG_PY = r'''
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
STATE_DIR = ROOT / "state"
LOG_DIR = ROOT / "logs"


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _load_env() -> dict[str, str]:
    merged: dict[str, str] = {}
    candidates = [
        Path.home() / ".alibaba" / "keys.env",
        Path("C:/Users/xiang/.alibaba/keys.env"),
        ROOT / ".env",
    ]
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        merged.update(_parse_env_file(path))
    merged.update({k: v for k, v in os.environ.items() if isinstance(v, str)})
    return merged


def load_settings() -> dict:
    return json.loads((CONFIG_DIR / "settings.json").read_text(encoding="utf-8"))


def save_settings(settings: dict) -> None:
    (CONFIG_DIR / "settings.json").write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_allowed() -> dict:
    path = CONFIG_DIR / "allowed.json"
    if not path.exists():
        return {"users": {}, "chats": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("users", {})
    data.setdefault("chats", {})
    return data


def save_allowed(data: dict) -> None:
    data.setdefault("users", {})
    data.setdefault("chats", {})
    (CONFIG_DIR / "allowed.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


SETTINGS = load_settings()
ENV = _load_env()


def env_value(*names: str) -> str:
    for name in names:
        value = (ENV.get(name) or "").strip()
        if value:
            return value
    return ""


TOKEN_ENV = SETTINGS.get("token_env", "TELEGRAM_BOT_TOKEN")
OWNER_ENV = SETTINGS.get("owner_env", "OWNER_TELEGRAM_ID")
BOT_TOKEN = env_value(
    TOKEN_ENV,
    "TELEGRAM_BOT_TOKEN",
    "TSUKUMO_TG_BOT_TOKEN",
    "AIKO_TELEGRAM_PRIMARY_BOT_TOKEN",
)
OWNER_ID_RAW = env_value(OWNER_ENV, "OWNER_TELEGRAM_ID", "AIKO_TELEGRAM_PRIMARY_USER_ID")
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW.lstrip("-").isdigit() else 0
OWNER_USERNAME = env_value("OWNER_USERNAME").lstrip("@")


def _secret_values() -> list[str]:
    values: list[str] = []
    for key, value in ENV.items():
        marker = key.upper()
        if value and len(value) >= 8 and any(x in marker for x in ("TOKEN", "KEY", "SECRET", "PASSWORD", "PAT")):
            values.append(value)
    return values


def redact(text: str) -> str:
    out = text or ""
    for value in _secret_values():
        out = out.replace(value, "[REDACTED]")
    out = re.sub(r"bot[0-9]{6,}:[A-Za-z0-9_-]{20,}", "bot[REDACTED]", out)
    return out


def validate_config() -> list[str]:
    problems: list[str] = []
    workers = SETTINGS.get("workers") or {}
    active_worker = SETTINGS.get("active_worker") or ""
    pipeline = workers.get(active_worker) or SETTINGS.get("pipeline") or {}
    if not BOT_TOKEN:
        problems.append(
            f"{TOKEN_ENV} is missing. Create a bot in Telegram with @BotFather, then put the token in .env "
            "or C:/Users/xiang/.alibaba/keys.env. Do not paste the token in chat."
        )
    if SETTINGS.get("owner_required", True) and not OWNER_ID:
        problems.append(
            f"{OWNER_ENV} is missing. Start the bot, DM it /whoami, then put that numeric id in .env."
        )
    if workers and active_worker not in workers:
        problems.append(f"active_worker '{active_worker}' is not in config/settings.json workers.")
    if not pipeline.get("cmd"):
        problems.append("config/settings.json has no runnable pipeline command.")
    cwd = pipeline.get("cwd")
    if cwd:
        p = Path(cwd)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        if not p.exists():
            problems.append(f"pipeline cwd does not exist: {p}")
    return problems
'''


PIPELINE_PY = r'''
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from . import config, store


def _render(value: str, message: str, paths: dict[str, Path], meta: dict, prompt: str | None = None) -> str:
    rendered = value
    replacements = {
        "{input}": message,
        "{message}": message,
        "{prompt}": prompt if prompt is not None else message,
        "{PROMPT}": prompt if prompt is not None else message,
        "{task_id}": str(meta.get("task_id", "")),
        "{task_dir}": str(paths["task_dir"]),
        "{input_file}": str(paths["input_file"]),
        "{metadata_file}": str(paths["metadata_file"]),
        "{result_file}": str(paths["result_file"]),
    }
    for key, replacement in replacements.items():
        rendered = rendered.replace(key, replacement)
    return rendered


def _chunk(text: str, limit: int) -> str:
    text = config.redact(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 80)].rstrip() + "\n...[truncated; full output is in state/tasks]"


def _pipeline_cwd(raw: str | None) -> str:
    if not raw:
        return str(config.ROOT)
    p = Path(raw)
    if not p.is_absolute():
        p = (config.ROOT / p).resolve()
    return str(p)


def run(message: str, meta: dict) -> dict:
    settings = config.load_settings()
    workers = settings.get("workers") or {}
    active_worker = settings.get("active_worker") or ""
    pipe = workers.get(active_worker) or settings.get("pipeline") or {}
    task_id = meta.get("task_id") or time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    task_dir = config.STATE_DIR / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "task_dir": task_dir,
        "input_file": task_dir / "input.txt",
        "metadata_file": task_dir / "metadata.json",
        "result_file": task_dir / "result.json",
    }
    paths["input_file"].write_text(message, encoding="utf-8")
    paths["metadata_file"].write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    render_meta = {"task_id": task_id, **meta}
    template = pipe.get("input_template", "{message}")
    prompt_text = _render(template, message, paths, render_meta, prompt=message)
    argv = [_render(str(part), message, paths, render_meta, prompt=prompt_text) for part in pipe["cmd"]]
    stdin_data = None
    if pipe.get("stdin", True):
        stdin_data = prompt_text

    env = os.environ.copy()
    env.update(config.ENV)
    env.update({
        "TELEGRAM_AGENT_TASK_ID": task_id,
        "TELEGRAM_AGENT_TASK_DIR": str(task_dir),
        "TELEGRAM_AGENT_INPUT_FILE": str(paths["input_file"]),
        "TELEGRAM_AGENT_METADATA_FILE": str(paths["metadata_file"]),
        "TELEGRAM_AGENT_RESULT_FILE": str(paths["result_file"]),
    })

    started = time.time()
    store.event("pipeline_start", {"task_id": task_id, "argv": argv, "cwd": pipe.get("cwd")})
    try:
        proc = subprocess.run(
            argv,
            cwd=_pipeline_cwd(pipe.get("cwd")),
            input=stdin_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(pipe.get("timeout_seconds", 600)),
            shell=False,
            env=env,
        )
        elapsed = round(time.time() - started, 1)
        raw = {
            "returncode": proc.returncode,
            "stdout": config.redact(proc.stdout or ""),
            "stderr": config.redact(proc.stderr or ""),
            "elapsed_seconds": elapsed,
        }
        (task_dir / "process.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.time() - started, 1)
        raw = {
            "returncode": None,
            "stdout": config.redact(exc.stdout or ""),
            "stderr": config.redact(exc.stderr or ""),
            "elapsed_seconds": elapsed,
            "timeout": True,
        }
        (task_dir / "process.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        store.event("pipeline_timeout", {"task_id": task_id, "elapsed_seconds": elapsed})
        return {
            "status": "issue",
            "summary": f"Pipeline timed out after {elapsed}s.",
            "body": _chunk((raw["stdout"] + "\n" + raw["stderr"]).strip(), settings["output_chunk_chars"]),
            "task_id": task_id,
        }

    result_file = paths["result_file"]
    if result_file.exists():
        try:
            result = json.loads(result_file.read_text(encoding="utf-8-sig"))
            if isinstance(result, dict):
                result.setdefault("task_id", task_id)
                result.setdefault("status", "success" if raw["returncode"] == 0 else "issue")
                result.setdefault("summary", "Pipeline wrote result.json.")
                result.setdefault("body", "")
                store.event("pipeline_result_file", {"task_id": task_id, "status": result.get("status")})
                return result
        except json.JSONDecodeError:
            pass

    combined = "\n".join(x for x in (raw["stdout"], raw["stderr"]) if x).strip()
    status = "success" if raw["returncode"] == 0 else "issue"
    summary = f"Pipeline exited {raw['returncode']} in {raw['elapsed_seconds']}s."
    store.event("pipeline_done", {"task_id": task_id, "status": status, "returncode": raw["returncode"]})
    return {
        "status": status,
        "summary": summary,
        "body": _chunk(combined or "(no output)", settings["output_chunk_chars"]),
        "task_id": task_id,
    }
'''


STORE_PY = r'''
from __future__ import annotations

import json
import time
from pathlib import Path

from . import config

config.STATE_DIR.mkdir(parents=True, exist_ok=True)
config.LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = config.STATE_DIR / "state.json"
EVENTS_FILE = config.LOG_DIR / "events.jsonl"


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_state(data: dict) -> None:
    STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get(key: str, default=None):
    return _read_state().get(key, default)


def set_value(key: str, value) -> None:
    data = _read_state()
    data[key] = value
    _write_state(data)


def event(kind: str, data: dict | None = None) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "data": data or {},
    }
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
'''


APP_PY = r'''
from __future__ import annotations

import asyncio
import re
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from . import config, pipeline, store

QUEUE: asyncio.Queue[dict] = asyncio.Queue()
BUSY = False


def _is_owner(user_id: int | None) -> bool:
    return bool(user_id and config.OWNER_ID and user_id == config.OWNER_ID)


def _allowed(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if _is_owner(getattr(user, "id", None)):
        return True
    if not config.OWNER_ID:
        return False
    allowed = config.load_allowed()
    if chat and chat.type in ("group", "supergroup", "channel"):
        return str(chat.id) in allowed.get("chats", {})
    return bool(user and str(user.id) in allowed.get("users", {}))


def _requires_ping(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in ("group", "supergroup", "channel") and config.SETTINGS.get("require_mention", True))


def _triggered(update: Update, bot_username: str) -> bool:
    msg = update.effective_message
    if not msg:
        return False
    if not _requires_ping(update):
        return True
    text = msg.text or ""
    if bot_username and re.search(rf"@{re.escape(bot_username)}\b", text, flags=re.IGNORECASE):
        return True
    reply = msg.reply_to_message
    return bool(reply and reply.from_user and reply.from_user.username and reply.from_user.username.lower() == bot_username.lower())


def _clean_message(text: str, bot_username: str) -> str:
    if bot_username:
        text = re.sub(rf"@{re.escape(bot_username)}\b", "", text, flags=re.IGNORECASE)
    return text.strip()


async def _send_chunks(bot, chat_id: int, text: str) -> None:
    limit = int(config.SETTINGS.get("output_chunk_chars", 3500))
    text = text or "(empty)"
    while text:
        chunk = text[:limit]
        if len(text) > limit:
            cut = max(chunk.rfind("\n"), chunk.rfind(" "))
            if cut > limit // 2:
                chunk = text[:cut]
        await bot.send_message(chat_id, chunk, disable_web_page_preview=True)
        text = text[len(chunk):].lstrip()


async def _worker(app: Application) -> None:
    global BUSY
    while True:
        task = await QUEUE.get()
        BUSY = True
        try:
            await app.bot.send_chat_action(task["chat_id"], ChatAction.TYPING)
            result = await asyncio.to_thread(pipeline.run, task["text"], task["meta"])
            status = result.get("status", "success")
            header = f"{status}: {result.get('summary', 'done')}\ntask: {result.get('task_id', task['meta']['task_id'])}"
            body = result.get("body") or ""
            await _send_chunks(app.bot, task["chat_id"], header + ("\n\n" + body if body else ""))
        except Exception as exc:
            store.event("worker_error", {"error": str(exc), "task": task.get("meta", {}).get("task_id")})
            await app.bot.send_message(task["chat_id"], f"issue: internal worker error: {config.redact(str(exc))}")
        finally:
            BUSY = False
            QUEUE.task_done()


async def post_init(app: Application) -> None:
    me = await app.bot.get_me()
    app.bot_data["bot_username"] = me.username or ""
    app.create_task(_worker(app))
    store.event("bot_online", {"username": me.username, "bot_id": me.id})


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_help(update, context)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Telegram CLI agent online.\n"
        "Commands: /whoami, /status, /worker [name], /allow_user <id>, /allow_chat <id>, /sleep, /wake.\n"
        "In groups, mention the bot or reply to it to run the configured pipeline."
    )


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    await update.effective_message.reply_text(
        f"user id: {user.id if user else '(unknown)'}\n"
        f"username: @{user.username if user and user.username else '(none)'}\n"
        f"chat id: {chat.id if chat else '(unknown)'}\n"
        f"{'configured owner' if _is_owner(getattr(user, 'id', None)) else 'put your user id in OWNER_TELEGRAM_ID'}"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    settings = config.load_settings()
    active = settings.get("active_worker", "")
    worker = (settings.get("workers") or {}).get(active, {})
    await update.effective_message.reply_text(
        f"queue: {QUEUE.qsize()} waiting, {'busy' if BUSY else 'idle'}\n"
        f"owner configured: {'yes' if config.OWNER_ID else 'no'}\n"
        f"worker: {worker.get('label') or active or 'custom'}\n"
        f"pipeline cwd: {worker.get('cwd') or settings.get('pipeline', {}).get('cwd') or '.'}"
    )


async def _owner_only(update: Update) -> bool:
    if _is_owner(getattr(update.effective_user, "id", None)):
        return True
    await update.effective_message.reply_text("owner only")
    return False


async def cmd_allow_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _owner_only(update):
        return
    if not context.args:
        await update.effective_message.reply_text("usage: /allow_user <telegram_user_id> [label]")
        return
    allowed = config.load_allowed()
    label = " ".join(context.args[1:]).strip()
    allowed.setdefault("users", {})[str(context.args[0])] = {"label": label, "added": time.strftime("%Y-%m-%d %H:%M:%S")}
    config.save_allowed(allowed)
    await update.effective_message.reply_text(f"allowed user {context.args[0]}")


async def cmd_worker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _owner_only(update):
        return
    settings = config.load_settings()
    workers = settings.get("workers") or {}
    if not workers:
        await update.effective_message.reply_text("no workers configured")
        return
    if not context.args:
        active = settings.get("active_worker", "")
        lines = [
            f"{'* ' if name == active else '- '}{name}: {worker.get('label', name)}"
            for name, worker in workers.items()
        ]
        await update.effective_message.reply_text("workers:\n" + "\n".join(lines) + "\n\nusage: /worker <name>")
        return
    name = context.args[0]
    if name not in workers:
        await update.effective_message.reply_text("unknown worker. use /worker to list options.")
        return
    settings["active_worker"] = name
    config.save_settings(settings)
    await update.effective_message.reply_text(f"worker set to {workers[name].get('label', name)}")


async def cmd_allow_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _owner_only(update):
        return
    chat_id = context.args[0] if context.args else str(update.effective_chat.id)
    allowed = config.load_allowed()
    label = " ".join(context.args[1:]).strip()
    allowed.setdefault("chats", {})[str(chat_id)] = {"label": label, "added": time.strftime("%Y-%m-%d %H:%M:%S")}
    config.save_allowed(allowed)
    await update.effective_message.reply_text(f"allowed chat {chat_id}")


async def cmd_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _owner_only(update):
        return
    store.set_value("sleeping", True)
    await update.effective_message.reply_text("sleeping; /wake to resume")


async def cmd_wake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _owner_only(update):
        return
    store.set_value("sleeping", False)
    await update.effective_message.reply_text("awake")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return
    if not config.OWNER_ID:
        if update.effective_chat and update.effective_chat.type == "private":
            await msg.reply_text("Owner id is not configured. Run /whoami, then set OWNER_TELEGRAM_ID in .env.")
        return
    if not _allowed(update):
        return
    bot_username = context.application.bot_data.get("bot_username", "")
    if not _triggered(update, bot_username):
        return
    if store.get("sleeping", False):
        await msg.reply_text("sleeping; owner can /wake me")
        return
    if QUEUE.qsize() >= int(config.SETTINGS.get("queue_limit", 3)):
        await msg.reply_text(config.SETTINGS.get("busy_message", "busy; try again shortly"))
        return
    text = _clean_message(msg.text, bot_username)
    task_id = time.strftime("%Y%m%d-%H%M%S")
    await QUEUE.put({
        "chat_id": update.effective_chat.id,
        "text": text,
        "meta": {
            "task_id": task_id,
            "chat_id": update.effective_chat.id,
            "chat_title": getattr(update.effective_chat, "title", "") or "",
            "user_id": update.effective_user.id if update.effective_user else 0,
            "username": update.effective_user.username if update.effective_user else "",
            "message_id": msg.message_id,
        },
    })
    if config.SETTINGS.get("ack_on_ping", True):
        await msg.reply_text(f"queued {task_id}")


def main() -> None:
    problems = config.validate_config()
    if config.BOT_TOKEN:
        problems = [p for p in problems if not p.startswith(config.TOKEN_ENV)]
    if not config.BOT_TOKEN:
        raise SystemExit("\n".join(problems))
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("worker", cmd_worker))
    app.add_handler(CommandHandler("allow_user", cmd_allow_user))
    app.add_handler(CommandHandler("allow_chat", cmd_allow_chat))
    app.add_handler(CommandHandler("sleep", cmd_sleep))
    app.add_handler(CommandHandler("wake", cmd_wake))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
'''


MAIN_PY = r'''
from __future__ import annotations

import sys

from . import config


def main() -> None:
    if "--check" in sys.argv:
        problems = config.validate_config()
        if problems:
            for problem in problems:
                print(problem)
            raise SystemExit(1)
        print("configuration OK")
        return
    from .app import main as run
    run()


if __name__ == "__main__":
    main()
'''


def build_files(args: argparse.Namespace) -> dict[str, str]:
    cwd = args.cwd or str(Path.cwd())
    workers = preset_workers(cwd)
    active_worker = args.preset
    if args.pipeline:
        active_worker = "custom"
        workers[active_worker] = {
            "label": "custom CLI pipeline",
            "cmd": parse_cmd(args.pipeline),
            "stdin": args.stdin,
            "input_template": "{message}",
            "cwd": cwd,
            "timeout_seconds": args.timeout,
        }
    if active_worker not in workers:
        raise ValueError(f"unknown preset '{active_worker}'. Options: {', '.join(workers)}")
    settings = {
        "name": args.name,
        "token_env": args.token_env,
        "owner_env": args.owner_env,
        "owner_required": True,
        "require_mention": True,
        "ack_on_ping": True,
        "queue_limit": args.queue_limit,
        "busy_message": "busy; try again shortly",
        "output_chunk_chars": 3500,
        "active_worker": active_worker,
        "workers": workers,
        "pipeline": workers[active_worker],
    }
    env_example = f'''
    # Telegram bot token from @BotFather. Do not paste real tokens in chat.
    # If C:/Users/xiang/.alibaba/keys.env already has TSUKUMO_TG_BOT_TOKEN,
    # the generated bot can use that as a fallback.
    {args.token_env}=

    # Numeric Telegram user id. Start the bot, DM it /whoami, then set this.
    {args.owner_env}=
    OWNER_USERNAME=
    '''
    run_ps1 = '''
    $ErrorActionPreference = "Stop"
    Set-Location $PSScriptRoot
    py -m pip install --user -r requirements.txt
    py -m bot
    '''
    return {
        "bot/__init__.py": "",
        "bot/__main__.py": MAIN_PY,
        "bot/config.py": CONFIG_PY,
        "bot/pipeline.py": PIPELINE_PY,
        "bot/store.py": STORE_PY,
        "bot/app.py": APP_PY,
        "config/settings.json": json.dumps(settings, indent=2),
        "config/allowed.json": json.dumps({"users": {}, "chats": {}}, indent=2),
        "logs/.gitkeep": "",
        "state/.gitkeep": "",
        ".env.example": env_example,
        ".gitignore": ".env\n__pycache__/\n*.pyc\nstate/tasks/\nlogs/*.jsonl\nlogs/*.log\n",
        "requirements.txt": "python-telegram-bot>=22,<23\n",
        "run.ps1": run_ps1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Human name for the bot project.")
    parser.add_argument("--output", required=True, help="Output directory for the generated bot project.")
    parser.add_argument("--pipeline", help="Optional custom CLI command as a shell-like string or JSON argv list. If omitted, --preset is used.")
    parser.add_argument("--preset", default="codex", help="Worker preset when --pipeline is omitted: codex, claude, agy-flash-high, agy-pro-high.")
    parser.add_argument("--cwd", help="Working directory for the worker. Defaults to the current directory where the scaffold command is run.")
    parser.add_argument("--timeout", type=int, default=600, help="Pipeline timeout in seconds.")
    parser.add_argument("--queue-limit", type=int, default=3, help="Maximum queued requests before the bot replies busy.")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN", help="Primary env var for the Telegram bot token.")
    parser.add_argument("--owner-env", default="OWNER_TELEGRAM_ID", help="Env var for the owner's numeric Telegram id.")
    parser.add_argument("--stdin", dest="stdin", action="store_true", default=True, help="Send message text to pipeline stdin.")
    parser.add_argument("--no-stdin", dest="stdin", action="store_false", help="Do not send message text to stdin; use placeholders in argv.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated files if they already exist.")
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = build_files(args)
    for rel, content in files.items():
        write(output / rel, content, args.force)
    print(f"created Telegram CLI agent scaffold at {output}")
    print("next: copy .env.example to .env, set token/user id env vars, then run .\\run.ps1")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
