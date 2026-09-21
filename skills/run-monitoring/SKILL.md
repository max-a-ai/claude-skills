---
name: run-monitoring
description: Watch long-running jobs you do not control (Slurm/cluster trainings, sweeps, evals) and report them as an HTML scoreboard artifact. Composes the `tick-it` skill (one hourly pass and its report layout) with `general-codebase` (the engineering rules any script you write must pass). Use when asked to monitor or babysit runs, resume monitoring from a handoff file, set up a recurring status tick, or report how training is progressing.
---

# run-monitoring

Watch jobs you do not control, and publish what they are doing as **one HTML
page** that is republished in place. Chat is for the one-line verdict; the
page is the deliverable.

## Three parts

| part | what it owns |
|---|---|
| this skill | the setup: handoff file, scoreboard layout, what counts as an action |
| **`tick-it`** | one pass and its report layout — load it for every tick |
| **`general-codebase`** | the engineering rules the generator script must pass before you call the work done |

The scoreboard generator is ordinary repo code: ruff-clean, typed, audited
through `general-codebase` like anything else. Monitoring is not an excuse
for a throwaway script — it runs every hour for weeks.

## The handoff file is the source of truth

Every monitored project keeps a handoff file in its repo (`monitor_handoff.md`
or whatever it is called there): what is running, which script drives each
watch, what to do when a run finishes, and the artifact URL. Read it before
acting and follow it literally — the user maintains it deliberately.

Any change to the routine (a new run to watch, a new column, a new rule you
discovered) goes into that file **in the same turn** you make it. A routine
that lives only in a transcript is lost at the session boundary.

No handoff file yet? Create one as you go, and say so.

## The scoreboard: one HTML artifact

Generate the page from a **script in the repo**, never by hand-editing HTML.
The script is the single source of truth; hand edits are lost on the next
tick and silently clobber whatever the user curated. When the page needs a
new state (a greyed-out row, a new column), add it to the script.

Section order, top to bottom:

1. **Currently running** — the live table, first, because it is the only part
   that changes every tick.
2. **Headline / main results** — the runs that matter, against whatever
   baselines the project compares to.
3. **Ablations** — one table per axis, each ending with the main run as the
   reference row.
4. **Schedule and notes** — what runs next, and the protocol caveats.

Publish with the Artifact tool, passing `url` so it updates in place. Read
the live version first; on a refused publish, read it again and merge onto
it. Never `force` — that discards whatever someone else published.

### The running table

One row per job actually in the queue. Columns: step, target (name which
bound it is — an early-stop floor and a hard maximum are different claims),
percent, projected time left, then one column per metric.

Derive the projection from measured rate (seconds/step from the run's own
logs) plus per-evaluation overhead. Call it a projection, not a promise.

Put a **trend arrow** and the percentage beside each metric, comparing the
latest evaluation with the previous one:

| arrow | meaning | change |
|---|---|---|
| `⇘` | strongly improving | ≤ −3 % |
| `↘` | slightly improving | −3 % … −0.5 % |
| `→` | stale | within ±0.5 % |
| `↗` | slightly worsening | +0.5 % … +3 % |
| `⇗` | strongly worsening | ≥ +3 % |

Set the two thresholds from the run's **own noise**: measure how much the
metric swings between consecutive evaluations, put the stale band inside
that, and the strong band outside it. The table above is calibrated for
±4 % eval-to-eval noise. State which direction is good — for an error
metric, down is good.

One pair of evaluations is noisy, so treat a lone arrow as weather, not
climate: offer a smoothed comparison (average N evaluations per side) when
the arrows flap.

## Driving the tick

A **tick** is one pass of the routine: collect, regenerate, republish,
report. Two mechanisms, and they are not interchangeable:

- **Monitor** streams events and is right for "tell me the moment a run
  finishes or crashes". It expires after **30 minutes** whatever
  `timeout_ms` says, so it cannot drive any loop longer than that — a
  watcher that sleeps an hour between passes dies before its second pass.
  Re-arm it on each expiry notice.
- **CronCreate** drives the recurring tick. It enqueues a prompt into the
  running session, so the routine keeps the local repo, venv and SSH it
  needs. Schedule it on the hour (`0 * * * *`) so the ticks read as a clean
  hourly series, and label each report with the full hour whatever minute
  it fired at. See `tick-it` for the pass itself.

Tell the user CronCreate's limits when you set one up: **session-only**
(gone when the session ends, nothing on disk) and **auto-expires after 7
days**.

Reach for the `schedule` skill only for work that needs nothing local — it
creates cloud agents, which have no repo, no venv and no cluster access.

### Replay

A re-armed Monitor starts with an empty dedup cache, so its first event
**replays** every completion it can see. A replayed `DONE` is not a new
completion. Act idempotently: check whether the follow-up work already
exists (the eval JSON is on disk, the job is in the queue) before
submitting anything, or you will resubmit finished jobs every half hour.

## Report only what the handoff file asks for

Per tick: the queue and one sentence — new completions, failures, or
"nothing to act on" — in the layout `tick-it` fixes (clock headline, the
raw queue dump with no words attached, sub-headings naming the repository
and tracker project, the link, then the interpretation). Routine progress
lines need no push notification; a completion or a crash does.

**Confirm before reporting success.** Cite the evidence: the hash that now
matches, the `step` field in the eval output, the file that now exists. A
command whose output you did not read is not a result.

Finished runs carry a trap: an evaluation written at the wrong step looks
like a valid row. Check the step against the run's final step before
trusting it.

## A monitoring session monitors

The user may run several sessions against one repo at once. When a session
was set up to monitor and the request is something else — write a config,
submit a training, refactor — ask first, in one line:

> Monitoring: are you sure you want to use this session for something else?

and wait. Mixing two streams of work into one transcript is how two
sessions start colliding in the same working tree. Running the tick,
submitting an evaluation for a finished run and editing the handoff file
are monitoring; they need no question.

## Leave the jobs alone

Launch, cancel, resubmit and requeue need the user's explicit word every
time — including when a run looks stuck, misconfigured or wasteful. Report
what you see and what you would do; let them decide.
