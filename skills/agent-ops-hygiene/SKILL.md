---
name: agent-ops-hygiene
description: >-
  The operational baseline every long-lived agent must have: daily database
  backups with a sliding-window retention, automatic git-push of only
  *functional* code, and a git-tag version ledger you can list and restore.
  Use when building or auditing any persistent agent/bot/daemon that owns a
  database or state it cannot afford to lose — especially before "is it done
  properly?" reviews. Cross-platform (Windows + Linux), stdlib-only, harness-owned.
---

# Agent ops hygiene — backup · versioned push · restore

**The law:** an agent that owns state it can lose is not done until backup,
version-control, and restore are **harness code that runs on a schedule** — never
"the agent remembers to do it." This is table stakes, not a feature. If a review
asks "can it back itself up / restore a past version / does it auto-push working
code," the answer must be a scheduled mechanism you can point at, with a passing
proof.

Provenance: distilled from `aiko-core/scripts` (aiko-backup.sh + horde-backup.sh +
aiko-restore.sh + systemd timers) and hardened in **keel2** (`keel/base/maintenance.py`
+ `keel/selfheal` actuator), which adds the git-tag **version ledger** aiko lacked.

## The three organs (build all three; each is independently useful)

### 1. Database backup with a sliding window
- **Atomic snapshots.** SQLite → the online `.backup()` API (Python:
  `src.backup(dst)`), never a raw file copy — it is consistent even while the
  agent writes. Postgres → `pg_dump`. Copy other state (jsonl ledgers, small
  json) byte-for-byte.
- **Exclude sidecars.** Never copy `*-wal` / `*-shm` / `*-journal`; they rebuild
  and copying them beside a `.backup()` yields a corrupt pair.
- **Timestamped folders + KEEP-max prune.** `dest/<YYYY-MM-DD-HHMMSS>/…`, then
  delete all but the newest `KEEP` (the "7-max sliding window"). Prune the oldest
  *before or after* writing the new one — either way the window is bounded.
- **A `latest` pointer + a `backup.log`.** On Windows write `latest.txt` (a
  file), **not a symlink** (symlinks need admin). Log every run.

### 2. Git-push of *functional* code (two gates)
- **Green gate.** Run the project's check/test harness first; if it is red,
  commit **nothing**. "Functional" = the gate passed, not "it's Tuesday."
- **Secret gate.** Before committing, scan the staged paths; refuse if a
  `.env` / `*.pem` / `*.key` / keystore is staged (aiko's hard rule). Unstage
  and abort rather than leak.
- **SSH-only, no prompts.** Force `GIT_TERMINAL_PROMPT=0`, an empty
  `GIT_ASKPASS`, and `GIT_SSH_COMMAND='ssh -i <key> -o BatchMode=yes'`. Convert
  an `https://` origin to `git@github.com:` in place. A push must never be able
  to pop a GUI credential dialog. Commit **as the owner**, never as the assistant.
- Idempotent: a clean tree is a graceful no-op, not an error.

### 3. Version ledger — named, dated, restorable
- Every promote/milestone = an **annotated git tag** `v-<stamp>-<slug>` whose
  message is the changelog line. This is what answers "restore to a documented
  past version / which version is which" — a list of tags with dates + subjects.
- `restore(tag)` must **preserve the current state first** (a `rescue/<stamp>`
  branch, or move the tree aside to `.preRestore.<ts>`) so a bad restore is
  itself reversible. Refuse an unknown tag loudly.

## Scheduling — "both Windows and Linux" without forking the logic
- **One portable core.** Put backup/push/version logic in **stdlib-only** code so
  the identical module runs on both OSes. Do NOT write a bash version and a
  PowerShell version of the *logic* — they drift.
- **In-process daily scheduler** for the common case (agent up): one daemon
  thread, each job fires at most once per local day, a job missed while down runs
  on next boot (catch-up), state persisted so a restart never double-runs.
- **OS-native installer only for the down-process case** (the ~15 lines that
  differ): Windows Task Scheduler (`Register-ScheduledTask`, daily + on-logon) and
  Linux systemd user timer (`OnCalendar=daily`, `Persistent=true`) — both invoke
  the *same* CLI entry point.

## Reference implementation (proven, copy from here)
- `keel2/keel/base/maintenance.py` — `SqliteBackup`, `GitSync`, `VersionLedger`,
  `Maintenance` (scheduler), `build_ops(repo)` (single source of truth for both
  entry points). Stdlib only; cross-platform.
- `keel2/tools/maintenance.py` — the CLI (`backup | git-sync | versions |
  snapshot | restore | status`) the OS schedulers call.
- `keel2/tools/install-maintenance.ps1` (Windows) / `install-maintenance.sh` (Linux).
- `keel2/tools/poc_maintenance.py` — **the proof**: real sqlite read-back, 7-max
  window with an oldest-pruned *negative control*, tag→list→restore+rescue-branch,
  both gates refusing bad input, daily-once + restart catch-up.
- Self-fix build-on-top: `keel2/keel/selfheal` `PatchActuator` uses the same
  `VersionLedger` so every self-applied code change is a restorable version, built
  and tested in an isolated **git worktree** before an owner-approved merge.

## Verification bar (a review must see these, not take your word)
- A negative control that the window really prunes (write KEEP+1, assert the
  oldest is gone).
- A read-back proving the backup DB is queryable (not just a file that exists).
- The green gate blocking a commit on red, and the secret gate refusing a staged key.
- A restore that reverts the tree AND leaves a rescue branch.

## Anti-patterns (all seen in the wild)
- `git pull && git add . && git commit -m "auto" && git push` — no gate, no secret
  check, wrong author, HTTPS-prompt-prone. This is aiko's crude `pushgit.sh`; do
  not ship it.
- A `latest` **symlink** on Windows (needs admin) — use a `latest.txt` file.
- Leaving a `sqlite3.connect(...)` open — Windows locks the file; always close in
  `finally`, or backup/cleanup fails with WinError 32.
- Raw-copying a live SQLite `.db` — use `.backup()`; a mid-write copy is corrupt.
- Scheduling backups only in-process — add the OS installer, or a crashed process
  means no backups exactly when you need them.
