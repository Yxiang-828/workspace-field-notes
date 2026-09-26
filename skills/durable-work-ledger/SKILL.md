---
name: durable-work-ledger
description: >-
  One durable record for everything an agent owes: scheduled tasks, reminders,
  recurring jobs, detected issues, and the owner decisions about them. Covers the
  record schema, atomic claim-and-lease firing, occurrence history, per-item
  missed-fire policy, and ask-once decision memory. Use when building or auditing
  any agent that schedules work, reminds an owner, tracks its own defects, or asks
  for approval — especially before adding a SECOND store for time-bound work.
  Stdlib-only, single-writer, cross-platform.
---

# Durable work ledger — one record for scheduled work and decided work

**The law:** an agent must have **exactly one** record type for everything that is
time-bound or owner-decided. A reminder is a scheduled task. An issue's answer
window is a scheduled task. A recurring check-in is a scheduled task. A detected
defect is that same record with a decision attached instead of a due time. The
moment you add a second store, you own two clocks, two catch-up policies, two
missed-fire windows, and a manual stapling layer between them — and the staple is
where the work gets silently dropped.

Provenance: distilled from a full read of **aiko-core**'s scheduler (the
anti-pattern, 13 named failure modes below, several with shipped incidents) and
**keel2**'s `WakeStore`/`Autonomy` + `IssueLedger` (the partial-good: atomic
writes and retry parking, but split across two stores and one false-success bug).
Sibling skill: [`agent-ops-hygiene`](../agent-ops-hygiene/SKILL.md) — that one
keeps the state alive; this one keeps the state *correct*.

---

## Why one record (the concrete failure of two)

aiko ran **three** non-interoperating schedulers: an in-process JSON calendar, a
host `crontab` wrapper, and a second raw-shell `crontab` wrapper. Answering "what
is scheduled?" required querying three systems in two languages, and the two cron
ones were invisible to its own UI. keel2 is at **two**: `wakes.json` for scheduled
work, `issues/ledger.jsonl` for defects — plus a hand-written `Concerns` layer
that binds a 30-minute recheck wake to an open incident, which *is* the staple.

Every feature you are about to add — an answer window, a periodic reminder on
still-open items, a severity-scaled timeout, a regression check — is a due time
attached to an issue. Build them on two stores and each one needs its own
join, its own orphan-cleanup, and its own "what if the wake fired but the issue
was already closed" branch. On one store they are all just rows with a `due_at`.

---

## The record

One dict/row. Fields group into six concerns; **every field below earned its place
by a named failure in the catalogue.**

```python
{
  # ── identity ──────────────────────────────────────────────────────────────
  "id":         "w3f9a21",        # opaque, generated, never caller-supplied
  "n":          14,               # human-facing increment, for "issue #14"
  "signature":  "hindsight:dependency-down",  # DETERMINISTIC dedup key (see A2)

  # ── what ──────────────────────────────────────────────────────────────────
  "kind":       "issue",          # task | reminder | issue | recheck | ask
  "title":      "Hindsight container down",
  "note":       "...",            # the payload; for a task, what to do when woken
  "severity":   "critical",       # critical | major | minor  → scales timeouts
  "parent":     "w1a2b3",         # this reminder/recheck belongs to that issue

  # ── when ──────────────────────────────────────────────────────────────────
  "due_at":     1753160400.0,     # epoch seconds, UTC. None = not time-bound
  "every_seconds": 7200.0,        # 0 = one-shot
  "missed_policy": "latest",      # latest | catch_up | skip   (PER ITEM, see A7)
  "tz":         "Asia/Singapore", # the zone the human MEANT (see A6)

  # ── lifecycle ─────────────────────────────────────────────────────────────
  "status":     "pending",        # pending|running|done|failed|parked|wontfix
  "attempts":   0,
  "lease_until": 0.0,             # claim lease; 0 when unclaimed (see A3)
  "claimed_by": "",               # worker/process identity
  "last_error": "",

  # ── decision memory ───────────────────────────────────────────────────────
  "decision":     "",             # ""|owner-approved|owner-declined|auto-timeout|policy
  "decided_at":   0.0,
  "decided_by":   "",
  "asked_at":     0.0,            # when the owner was asked (drives the window)
  "ask_id":       "",             # the approval this is waiting on
  "version_tag":  "",             # the tag cut before acting → makes it reversible

  # ── provenance / mandate ──────────────────────────────────────────────────
  "channel": "telegram", "room_id": "...", "room_kind": "dm",
  "creator_id": "...", "creator_name": "...", "is_owner": true,
  "created":  1753150000.0,
}
```

**Occurrences live in a separate append-only log**, never collapsed into
`last_result`/`last_task_id` fields on the item (see A4):

```python
# occurrences.jsonl — one line per firing, append-only
{"item": "w3f9a21", "scheduled_for": 1753160400.0, "started": ..., "ended": ...,
 "outcome": "ok|failed|skipped", "error": "", "ref": "<task id / version tag>"}
```

`(item, scheduled_for)` is **UNIQUE**. That single constraint is your idempotency
key: a double-fire becomes a conflict you can detect instead of a duplicate you
can't.

---

## The five organs

### 1. Deterministic identity, fuzzy matching only as a *proposal*

The dedup key must be computed from structure — `component + error-class +
normalized signature` — never from a title string and never from an LLM's
judgment. An LLM may *propose* that a new detection is the same as a known one;
that proposal gets **recorded as a link and remains visible and reversible**. It
must never be able to silently suppress a detection, because the failure mode is
invisible: a genuinely new issue absorbed into an old `wontfix` disappears with
no alarm on it.

### 2. Atomic claim with a lease — not "read, then act, then write"

```sql
UPDATE items SET status='running', lease_until=?, claimed_by=?, attempts=attempts+1
 WHERE id=? AND status='pending' AND (lease_until=0 OR lease_until < ?)
```

Fire only if the claim affected a row. This replaces every in-memory
`pendingIds` set (worthless across processes and across restarts) and makes
crash-recovery a **lease reaper** — anything `running` past its lease returns to
`pending` — instead of a bespoke "sweep stale running" pass.

`attempts` increments **at claim time**, not at failure time. An item that
crashes the process mid-run must still burn an attempt, or it becomes an infinite
crash loop that the retry limit never catches.

### 3. Complete on the *outcome*, never on the dispatch

The single most dangerous bug in this whole design space (aiko A5, keel2's live
`Autonomy.fire_due`): dispatching work onto another thread/queue and then marking
the item `done` because dispatch didn't throw. The item must be concluded by the
**work's own completion callback**, carrying a real outcome. If you cannot
observe the outcome, the correct status is `running`-until-lease-expiry, not
`done`. Never infer success from the absence of an observed failure.

### 4. Occurrence history, not last-write-wins fields

`last_result` / `last_task_id` / `last_error` on a recurring item give it a
history of exactly one. You cannot answer "has this been flapping?", "did the
fix hold?", or "is this a regression or a fresh find?" — which are precisely the
questions an issue ledger exists to answer. Append occurrences; keep the item row
for *current* state only.

### 5. Decision memory — ask once, remember forever

A decision is a field on the item, not a separate approvals table that evaporates:

- `owner-approved` → act, record `version_tag` so it is reversible.
- `owner-declined` → `wontfix`. On recurrence, **stay silent**; do not re-ask.
- `auto-timeout` → acted without an answer; must carry `version_tag` (the whole
  reason the timeout path uses versioned self-fix instead of a raw edit — a
  belated "undo that" has to have something to roll back to).
- A recurrence of a `done` item is a **regression**, reported as such — never
  re-reported as a fresh discovery.

**The ask surface must be durable.** In-memory pending approvals with a live
closure as the action cannot survive a restart, which means any window longer
than the process lifetime silently loses the question. Persist the *item id* and
re-derive the action; never persist a closure.

---

## Anti-pattern catalogue (each observed in real code)

| # | Anti-pattern | Observed | Do instead |
|---|---|---|---|
| A1 | Multi-process read-modify-write on one JSON array, no lock | aiko: TS daemon + Python skill both rewrite `events.json`; a crash mid-write truncates it and `load()` swallows the parse error → **calendar silently becomes empty** | Single writer. Other processes go through it (IPC/HTTP). Atomic temp+rename. **Never** swallow a parse failure — a corrupt store is a loud alarm, not an empty list |
| A2 | Title as de-facto primary key | aiko: cancel-by-title cancels *every* event sharing it; a bolted-on title-normalizing dedup in the Python writer only, which the TS writer lacks → **135 duplicate double-firing events in production** | Deterministic `signature`; uniqueness enforced in one place both writers share |
| A3 | In-memory set as the double-fire guard | aiko `pendingIds` | Atomic claim + lease |
| A4 | History collapsed into `last_*` fields | aiko + keel2 both | Append-only occurrence log |
| A5 | Marking done on dispatch | aiko (busy-runtime drop reports `done` for work that never started); **keel2 `Autonomy.fire_due` today** | Conclude from the completion callback with a real outcome |
| A6 | Two serializations of the same instant | aiko: TS writes `Z`, Python writes `+08:00`, and list-ordering is a *lexicographic* string compare → correct firing, **wrong UI order** | One serialization (epoch or UTC ISO). Store the IANA zone the human meant, separately. Sort on the instant |
| A7 | One global missed-fire constant | aiko: a single 10-minute boot grace for everything | Per-item `missed_policy`. A pill reminder and a log-rotate want opposite answers |
| A8 | No retry policy | aiko: failed one-shot is terminal, resurrected only by an unrelated edit | `attempts` + backoff + park with a reason |
| A9 | Structured state encoded in prose and regexed back out | aiko: the calendar↔task foreign key is `/\[AIKO_CALENDAR_TASK ([^\]]+)\]/` over a *prompt*; completion is `/\bDONE\b/i` on model output | Columns. The model fills fields; code reads fields |
| A10 | Unbounded growth | aiko: "delete" only sets `cancelled`; one dir per firing forever, and `list()` parses **all** of them per lookup; full array broadcast to every client on every save | Bounded retention + an index. Broadcast deltas |
| A11 | Overloaded / lying status | aiko: `failed` means three different things; `deliveryStatus` is a hardcoded literal pretending to be an ack; declared-but-never-assigned states | One meaning per value. If you didn't observe it, don't record it |
| A12 | Head-of-line blocking as "the queue" | aiko: serial `await` per due item, behind a 6-hour idle wait, behind a global run mutex | Claim N, run concurrently, per-item timeout |
| A13 | Prose policy instead of a code bound | aiko: the self-scheduling loop is closed with prompt text ("do not duplicate") and no allowlist/rate-cap/depth-limit — it produced the 135 duplicates | Enforce caps in code. Prompts are not constraints |

---

## Bounds that must be *bounds*, not errors

A pending-item cap is good (keel2's `MAX_PENDING=25` beats aiko's unbounded
growth). But it must not be a cap that *throws* once the ledger also holds
reminders and rechecks: N open issues × a periodic reminder each + one recheck
each will hit a low cap and start refusing legitimate schedules. Cap
per-`kind`, or make system-generated items (reminder/recheck) not count against
the user-facing budget. Whatever you choose, **log what was dropped** — a silent
cap reads as "nothing was scheduled" when it means "we stopped scheduling."

## Reminders: digest, not per-item nagging

One reminder message per interval covering *all* open items, not one message per
item. Scale the interval by severity, and after N unanswered rounds move the item
to a quiet "still open, not reminding" state that stays listable. Per-item
repeating pings are how an owner learns to ignore the channel, which defeats the
purpose of the critical ones.

## When JSON is no longer enough → SQLite

Single-writer atomic JSON is defensible for one daemon process. Move to SQLite the
moment **any** of these becomes true — and treat it as a trip-wire, not a
someday:

1. A second process writes the store (a console/UI, a CLI skill, a cron job).
2. You need the claim in organ 2 to be correct across processes.
3. The occurrence log outgrows a full re-read per query.

The `(item, scheduled_for)` unique constraint and the conditional-UPDATE claim
are both one line in SQL and both hand-rolled and fragile in JSON.

## Verification (per [[poc-law]] — no PoC, not done)

A PoC must cover, each with a negative control:

1. **Claim exclusion** — two concurrent claimers, exactly one wins.
2. **Lease reaping** — kill mid-run; item returns to `pending`, `attempts` already burned.
3. **No double-fire** — same `(item, scheduled_for)` rejected.
4. **Outcome truth** — dispatch succeeds but work fails → item is `failed`, *not* `done`. (The A5 regression test.)
5. **Missed fires** — down across N occurrences → `latest` fires once, `catch_up` fires N, `skip` fires none.
6. **Ask-once** — declined item recurs → no second ask, status stays `wontfix`.
7. **Regression detection** — `done` item recurs → reported as regression, not a new find.
8. **Corrupt store** — truncated file → loud failure, never a silent empty list.
