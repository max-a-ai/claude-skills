---
name: run-monitoring
description: Watch long-running jobs you do not control (Slurm/cluster trainings, sweeps, evals) and report them as an HTML scoreboard artifact. Composes the `tick-it` skill (one hourly pass and its report layout) with `general-codebase` (the engineering rules any script you write must pass). Use when asked to monitor or babysit runs, resume monitoring from a handoff or setting file, set up a recurring status tick, or report how training is progressing.
---

# run-monitoring

Watch jobs you do not control, and publish what they are doing as **one HTML
page** that is republished in place. Chat is for the one-line verdict; the
page is the deliverable.

## Three parts

| part | what it owns |
|---|---|
| this skill | the setup: setting file, scoreboard layout, what counts as an action |
| **`tick-it`** | one pass and its report layout — load it for every tick |
| **`general-codebase`** | the engineering rules the generator script must pass before you call the work done |

The scoreboard generator is ordinary repo code: ruff-clean, typed, audited
through `general-codebase` like anything else. Monitoring is not an excuse
for a throwaway script — it runs every hour for weeks.

## The setting file is the source of truth

Every monitored project has one setting file, centrally, so it can be pulled on
any machine without the project checkout:

    ~/.claude-skills/monitoring-settings/<project>.md

Named after the project and nothing else — no date in the filename. The file is
a living setting, so a date would record when it was written when a reader wants
to know what is true now, and two dated files for one project is how the stale
one gets read. `updated:` in the front matter covers a reader who has only the
file; `git log` covers the rest, and pulls any past state back:

    git -C ~/.claude-skills log --oneline -- monitoring-settings/<project>.md
    git -C ~/.claude-skills show <sha>:monitoring-settings/<project>.md

Read it before acting and follow it literally — the user maintains it
deliberately. Any change to the routine (a new run to watch, a new column, a
rule you discovered) goes into it **in the same turn** you make it. A routine
that lives only in a transcript is lost at the session boundary.

### What the setting holds, and what it must not

It holds the **variable** half, in this order:

0. a pointer to the ground set, never a copy of it
1. where things are — repo, local path, cluster alias and path, tracker, artifact URL
2. **main trainings** — the default bucket
3. **ablation studies**
4. further buckets this project needs (debug experiments, short tests)
5. **evaluation parameters** — sources, metrics, the headline three, the submit line, thresholds
6. **specified wishes** — what this user asked for on this project
7. the routine's project-specific commands, the scoreboard options, known traps

It must not hold the **invariant** half — tick on the hour, queue first,
verbatim queue block, a sentinel on every probe, republish in place, never
launch a job unasked. That is `tick-it` and this skill. A setting that repeats
them will drift from them, and then the skill wins and the setting is wrong.

It must not hold **live state** either. A running table rewritten every hour
belongs in the project repo or the scratchpad, not in a tracked settings store
where it would churn the history. Keep a live block in the project, regenerated
between markers by the project's own script.

### Classification: mains are the default

Any run not explicitly listed in another bucket is a **main training**, and a
main training gets the project's full evaluation when it finishes. Ablations,
debug experiments and short tests have to be named. This is deliberate: the
failure mode worth avoiding is a real candidate quietly treated as a throwaway,
not the reverse.

### No setting yet: draft, show, ask

Do not invent a routine silently and do not tick. Discover first:

- the cluster queue, if the project has one
- the newest run directories and their `metrics.jsonl` / config
- the tracker project the repo configures
- any handoff, README or docs section describing runs

Then write the draft setting, with every run found as a main training, the
evaluation parameters filled from the newest run's metrics keys (each
`val/<source>/<metric>` becomes a source and a metric, the first source is the
headline), and the wishes section empty. Show it and ask before the first tick.
**No evaluation job is ever submitted from a draft** — the classification is a
guess until the user has corrected it.

Correcting a draft is cheaper for the user than dictating one from nothing, but
only if the guesses are visible. Say which runs you classified and from what.

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

## Report only what the setting file asks for

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
submitting an evaluation for a finished run and editing the setting file
are monitoring; they need no question.

## Leave the jobs alone

Launch, cancel, resubmit and requeue need the user's explicit word every
time — including when a run looks stuck, misconfigured or wasteful. Report
what you see and what you would do; let them decide.
