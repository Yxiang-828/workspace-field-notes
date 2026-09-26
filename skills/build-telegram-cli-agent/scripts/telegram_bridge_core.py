"""Generic Telegram front end. Bring a worker; the transport is already written.

A built agent, whatever it is behind, reduces to one callable:

    reply(session, text) -> Reply(text, trace)

Everything else a Telegram bot needs -- long polling, update offsets, the 4096
character cap, an owner gate, per-chat sessions, surviving a bad turn -- is
identical for every agent and lives here. The scaffold in this skill already had
a pluggable `workers` registry but every worker was a subprocess; the axis that
actually generalises is the worker KIND, so `CommandWorker` and `HttpWorker` are
both just callables and a new agent is a small adapter rather than a new bot.

    from telegram_bridge_core import Bridge, HttpWorker, Reply

    def build(session, text):
        return {"message": text, "history": session.history[-12:]}

    def parse(payload):
        return Reply(payload["answer"], {"tools": payload.get("tools_used")})

    Bridge(worker=HttpWorker("http://127.0.0.1:8077/api/v1/guru", build, parse)).run()
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import httpx

MAX_TELEGRAM_CHARS = 3900          # the real cap is 4096; leave room for a footer
DEFAULT_HISTORY_TURNS = 12


@dataclass
class Reply:
    """What a worker returns. `trace` is rendered as a footer under the answer.

    The footer is not decoration. An agent's prose reads as success whether or not
    anything happened, so whatever the worker knows structurally -- which tools
    ran, whether a write landed -- belongs where the tester can see it.
    """

    text: str
    trace: dict[str, Any] = field(default_factory=dict)

    def rendered(self) -> str:
        if not self.trace:
            return self.text
        bits = [f"{k}={v}" for k, v in self.trace.items() if v not in (None, "", [], {})]
        return f"{self.text}\n\n— {' · '.join(bits)}" if bits else self.text


@dataclass
class Session:
    chat_id: int
    history: list[dict[str, str]] = field(default_factory=list)
    vars: dict[str, Any] = field(default_factory=dict)

    def remember(self, user: str, assistant: str, keep: int = DEFAULT_HISTORY_TURNS) -> None:
        self.history.append({"role": "user", "content": user})
        self.history.append({"role": "assistant", "content": assistant})
        del self.history[: max(0, len(self.history) - keep * 2)]


class Worker(Protocol):
    def reply(self, session: Session, text: str) -> Reply: ...


class HttpWorker:
    """Fronts an agent that speaks HTTP JSON -- the shape most built agents take."""

    def __init__(self, url: str,
                 build: Callable[[Session, str], dict[str, Any]],
                 parse: Callable[[dict[str, Any]], Reply],
                 timeout: float = 120.0,
                 headers: dict[str, str] | None = None) -> None:
        # Most agents worth fronting sit behind a bearer token or api key, so an
        # adapter that cannot send a header does not front "any HTTP agent".
        self.url, self.build, self.parse, self.timeout = url, build, parse, timeout
        self.headers = headers or {}

    def reply(self, session: Session, text: str) -> Reply:
        try:
            r = httpx.post(self.url, json=self.build(session, text),
                           headers=self.headers or None, timeout=self.timeout)
        except httpx.HTTPError as exc:
            # Name the fix, do not narrate the failure.
            return Reply(f"Cannot reach the agent at {self.url} ({type(exc).__name__}). "
                         f"Is it running?")
        if r.status_code != 200:
            body = r.text[:300]
            try:
                body = r.json().get("detail", body)
            except ValueError:
                pass
            return Reply(f"Agent returned HTTP {r.status_code}: {body}")
        try:
            return self.parse(r.json())
        except (ValueError, KeyError) as exc:
            return Reply(f"Could not read the agent's response: {type(exc).__name__}: {exc}")


class CommandWorker:
    """Fronts a local CLI. The original worker kind, kept so both live behind one seam."""

    def __init__(self, argv: list[str], cwd: str | None = None,
                 timeout: float = 1800.0) -> None:
        self.argv, self.cwd, self.timeout = argv, cwd, timeout

    def reply(self, session: Session, text: str) -> Reply:
        try:
            p = subprocess.run(self.argv, input=text, capture_output=True,
                               text=True, cwd=self.cwd, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return Reply(f"Worker exceeded {self.timeout:.0f}s and was stopped.")
        except OSError as exc:
            return Reply(f"Could not start {self.argv[0]!r}: {exc}")
        out = (p.stdout or "").strip() or (p.stderr or "").strip()
        return Reply(out or "(worker produced no output)", {"exit": p.returncode})


class Bridge:
    def __init__(self, worker: Worker, token: str | None = None,
                 owner_file: str = ".tg_owner.json",
                 commands: dict[str, Callable[[Session, str], str]] | None = None,
                 poll_seconds: int = 25) -> None:
        self.worker = worker
        self.token = token or os.getenv("TSUKUMO_TG_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        self.owner_file = Path(owner_file)
        self.commands = commands or {}
        self.poll = poll_seconds
        self.sessions: dict[int, Session] = {}

    # --- telegram plumbing ------------------------------------------------

    @property
    def api(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def send(self, chat_id: int, text: str) -> None:
        for i in range(0, len(text), MAX_TELEGRAM_CHARS):
            httpx.post(f"{self.api}/sendMessage",
                       json={"chat_id": chat_id, "text": text[i:i + MAX_TELEGRAM_CHARS]},
                       timeout=20)

    def _owner(self) -> int | None:
        try:
            return int(json.loads(self.owner_file.read_text())["owner_id"])
        except (OSError, ValueError, KeyError):
            return None

    def _bind(self, chat_id: int) -> None:
        self.owner_file.write_text(json.dumps({"owner_id": chat_id}), encoding="utf-8")
        print(f"[bridge] owner bound to chat {chat_id}", flush=True)

    def session(self, chat_id: int) -> Session:
        return self.sessions.setdefault(chat_id, Session(chat_id=chat_id))

    # --- dispatch ---------------------------------------------------------

    def handle(self, chat_id: int, text: str) -> str:
        s = self.session(chat_id)
        word = text.strip().split()[0].lower() if text.strip() else ""
        if word == "/whoami":
            return f"chat id {chat_id}"
        if word == "/reset":
            s.history.clear()
            return "History cleared."
        if word in self.commands:
            return self.commands[word](s, text)
        if word.startswith("/"):
            known = " ".join(sorted({"/whoami", "/reset", *self.commands}))
            return f"Commands: {known}"
        reply = self.worker.reply(s, text)
        s.remember(text, reply.text)
        return reply.rendered()

    def run(self) -> int:
        if not self.token:
            print("No bot token. Set TSUKUMO_TG_BOT_TOKEN or TELEGRAM_BOT_TOKEN, or pass "
                  "token=... to Bridge().", file=sys.stderr)
            return 2
        me = httpx.get(f"{self.api}/getMe", timeout=20).json()
        if not me.get("ok"):
            print("Telegram rejected the token.", file=sys.stderr)
            return 2
        owner = self._owner()
        print(f"[bridge] @{me['result']['username']} up", flush=True)
        print(f"[bridge] owner: {owner or 'UNBOUND - first chat to message binds'}", flush=True)

        offset = None
        while True:
            try:
                r = httpx.get(f"{self.api}/getUpdates",
                              params={"timeout": self.poll, "offset": offset},
                              timeout=self.poll + 15)
                if r.status_code == 409:
                    print("[bridge] HTTP 409: another process is polling this same bot "
                          "token. Stop that process, or use a different bot.",
                          file=sys.stderr)
                    return 3
                updates = r.json().get("result", [])
            except httpx.HTTPError:
                time.sleep(3)
                continue

            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg or "text" not in msg:
                    continue
                chat_id, text = msg["chat"]["id"], msg["text"]

                current = self._owner()
                if current is None:
                    self._bind(chat_id)
                    current = chat_id
                    self.send(chat_id, "Bound to you. Nobody else can use this bridge now.")
                if chat_id != current:
                    self.send(chat_id, "This bridge is bound to another user.")
                    continue

                print(f"[bridge] <- {text[:70]}", flush=True)
                try:
                    self.send(chat_id, self.handle(chat_id, text))
                except Exception as exc:      # one bad turn must not kill the bridge
                    print(f"[bridge] handler error: {exc!r}", file=sys.stderr, flush=True)
                    self.send(chat_id, f"Bridge error: {type(exc).__name__}: {exc}")
