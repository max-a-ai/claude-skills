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

### 1. Clock headline

`## 13:00` — nothing else on the line.

### 2. The raw queue, with no words attached

Straight after the headline, a fenced block holding the **verbatim** output
of the queue command, exactly as the cluster printed it. The user has an
alias for it (on Slurm usually `sq` = `squeue -u $USER`); run that command
and paste what came back.

No commentary, no column you added, no rows you filtered, no "(empty)"
prose inside the block — if the queue is empty, the block holds the header
line alone. Everything you noticed about it belongs in section 5.

Aliases live in `.bash_aliases`, which a non-interactive `ssh` does not
read, so `ssh host sq` fails with `command not found`. Send the underlying
command instead.

### 3. Sub-headings: what is actually being watched

Name the concrete things, so the report is readable without the session:

- the repository and the checkout being monitored (local path, cluster path)
- the experiment tracker project (wandb project / entity), if there is one
- the job source (Slurm account, partition)

Keep it to a line each. Revise it when it changes, not every tick.

### 4. The link

The scoreboard artifact URL or the overview file, on its own, right after
the sub-headings. The reader should be one click from the detail without
scrolling past the analysis.

### 5. Interpretation

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
