---
name: tick-it
description: Run and report one monitoring tick on the full hour — collect cluster state, regenerate the overview, republish it, and report in the fixed tick layout (clock headline, raw queue dump, what is monitored, link, interpretation). Use for each recurring status pass of a long-running job watch; the run-monitoring skill owns the wider setup.
---

# tick-it

One **tick** is one pass: collect, regenerate, republish, report. This skill
owns the pass and its report layout. `run-monitoring` owns the setup around
it (handoff file, scoreboard script, what counts as an action).

## Ticks land on the full hour

Schedule on the hour: `0 * * * *`. The headline is the full clock hour
(`13:00`), even when the scheduler fires a few minutes late — jitter of up
to 10 % of the period is normal and is not worth reporting. Do not label a
tick with the minute it happened to run; the hour is the identity of the
tick, so consecutive reports line up when read back.

CronCreate is session-only and auto-expires after 7 days. Say both when you
set one up.

## The report layout, in this order

### 1. One code block: clock, what is watched, raw queue

The first three things are rows of a single fenced block, in this order —
the tick's hour, the things being watched, then the queue verbatim:

```
tick     13:00
repo     <org>/<repo> - local <path> · <cluster> <path>
tracker  <wandb project> - <how metrics get there>
jobs     <scheduler> · <partition> · <account>

<the queue command's output, exactly as the cluster printed it>
```

The clock row is the full hour, not the minute the scheduler fired.

The watched rows name the concrete things, so the report is readable
without the session: the repository and both checkouts, the experiment
tracker project, the job source. Revise them when they change, not every
tick.

The queue is **verbatim**: no commentary, no column you added, no rows you
filtered, no "(empty)" prose. An empty queue is the header line alone.
Everything you noticed about it belongs in the interpretation.

The user has an alias for the queue command (on Slurm usually `sq` =
`squeue -u $USER`). Aliases live in `.bash_aliases`, which a
non-interactive `ssh` does not read, so `ssh host sq` fails with `command
not found`. Send the underlying command instead.

### 2. The link

The scoreboard artifact URL or the overview file, on its own line, right
after the block. The reader should be one click from the detail without
scrolling past the analysis.

### 3. Interpretation

Now the words. What changed since the last tick, what finished, what
failed, what you did about it, and what it means. This is the only section
where you are allowed to be discursive — and it is still short.

State counts as deltas (`14 → 10 pending`), not absolutes alone. If nothing
changed, say so in one line rather than restating the queue in prose.

## Collect before you narrate

Run the whole collection in **one backgrounded command** and read its
output, rather than narrating between steps: pull results, sync metrics,
capture the queue, check for finished-but-unevaluated runs, grep the newest
logs for tracebacks, regenerate the page. A tick that takes ten minutes of
wall clock should take one tool call.

**Distinguish a failed probe from an empty result.** An SSH hop that dies
returns nothing, and so does a genuinely idle cluster; treating the first
as the second reports "all clear" over a dead link. Have every remote probe
print a sentinel (`PROBE-OK`) on success and test for the sentinel, not for
non-empty output. Retry a few times before believing either answer.

## Republish, never hand-edit

Regenerate the page from the repo script, then publish with the Artifact
tool passing `url`. On a refused publish, read the live version in full,
merge onto it, publish again — another session may have added a column you
would otherwise delete. Never `force`.

## Leave the jobs alone

Follow the handoff file's rules for finished runs (submitting a queued
evaluation is routine). Launching, cancelling, resubmitting or requeueing a
training needs the user's word every time, however stuck it looks.
