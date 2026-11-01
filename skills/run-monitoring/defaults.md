# Scoreboard defaults

These apply to **every** monitored project, every tick, without being
repeated anywhere. A project's setting file
(`~/.claude-skills/monitoring-settings/<project>.md`) holds only the
**custom** half: where things are, what is measured, how the tables are
built, the job history. When a setting wants a default changed for its
project it says so in one line ("plots: off"), and that line wins for that
project only. The user's own words in the chat win over both.

## 1. Default vs custom

| default (this file, all projects) | custom (the project's setting) |
|---|---|
| page behaviour: queue on top, folding, sticky headers, width, confirmation boxes, plots, settings section | sites, paths, queue and submit commands, tracker project, artifact URL |
| the tick procedure and its order | the metrics: names, which direction is better, thresholds / IoUs |
| what is routine (evals) and what needs the user's word (trainings) | table structure: tables, titles, groups, rows, pinned baselines, comparisons |
| storage: every setting reproducible from the repo | the eval command and its checks, the job history, project-specific traps |

## 2. Page defaults

1. **Dated header**, then the list of results not yet confirmed (see 4),
   then the queue, then the result tables, then the settings section last.
2. **Queue on top**: every site's raw queue (`squeue -u $USER -h -o
   "%i|%j|%T|%M|%l|%D|%b|%R|%E"`), all sites in one table, sorted by
   longest elapsed first. One short line per job: job id, name, site,
   state, elapsed, reason / node, epoch and the last per-epoch readings.
   A held job reads just its reason ("Dependency", "Priority"); a click
   opens the rest: time limit, nodes, resources, and the jobs a dependency
   waits on, by name.
3. **Every table folds closed** under its title (the paper tables and every
   table below them); a click opens it.
4. **Confirmation boxes**: every result the user has not confirmed carries
   a red "new" box in its row and in the list on top. A table holding an
   unconfirmed result is outlined red until all its boxes are ticked.
   Ticks are written to the artifact's store (`acks/<id> = {run, at}`).
5. **Frozen headers and page width**: while a table's own header has
   scrolled above the window and the table is still in view, a copy of its
   header rows (title, column names, plot boxes) is pinned at the window
   top, with the table's column widths and its sideways scroll; clicks on
   the copy reach the real header. It works at any window width (CSS
   `position: sticky` does not: a table box that scrolls sideways traps it).
   **One line per row**: no data row wraps. The row label takes the width
   left over and is cut with an ellipsis (full text in its tooltip), so a
   table fits the page; only the column names may break onto a second line.
   A window narrower than the numbers need (about 1100 px for a 17-column
   table) scrolls the table sideways inside its box.
5a. **Type and IDs**: ID and row cells share one small mono face (11 px);
   numbers mono 11 px; the delta line under a value 9.5 px. The ID is the
   series only (`s34b`, `s15-09`), the full run name in its tooltip and in
   the row's detail. A confirmation box sits in front of the row label, so a
   cut label never hides it. Cells align on the text baseline.
6. **Trend arrows**: left of every value with a per-epoch series, in the
   text colour, the direction of its last five epoch-to-epoch changes:
   ↗ rising (4 or 5 up), ↘ falling (4 or 5 down), → even (anything else);
   the tooltip gives the count.
7. **Plots for every training row**: a click opens one rectangle with
   three panels under each other (3 rows, 1 column): x = epoch, y = the
   metric. Each panel draws the per-epoch curve and the full-set value as a
   red dot at the checkpoint epoch it came from. The run's own curve is
   always #244d53; behind it, in translucent grey, the curve of the best run
   of the same table for that column (highest full-set value among the
   table's runs with a per-epoch series; "best in this table" when it is
   the run itself). An eval-only row shows its
   full-set value alone. Pointing into the plot marks the nearest epoch in all
   three panels (guide line, ringed points, one label: the run's value, at
   the checkpoint epoch also its full-set value, then the best run's value
   in grey).
8. **Picking what is plotted**: a row of checkboxes under each table's
   column names, at most three ticked (the rest grey out). The **settings
   section** at the bottom of the page holds the same choice for every
   table at once, as levels: Global, then groups (e.g. "Paper tables"),
   then each table; the queue is its own top level (its three columns). A level without its own choice inherits the level above,
   down to the default: **the first three metric columns**. A level has an
   "inherit" button to drop its own choice. Choices go to the artifact's
   store (`plots/<scope>`) and so survive reloads.
9. **Theme-aware and phone-safe**, per the artifact page contract.

## 3. Storage: everything reproducible from the repo

The page is generated by a script in the project repo, never hand-edited.
Everything the page shows other than the collected numbers lives in
committed files: the generator and its template, published baselines, the
confirmed-results list (`.docs/scoreboard-acked.json`) and the plot
choices (`.docs/scoreboard-plots.json`). The collected numbers come from
the sites each tick; snapshots and queue dumps are scratch. Check: a
render from the committed files and the same snapshots equals the
published page except for the header's time and commit.

## 4. The tick, in order

1. Read the artifact's store: `acks` and `plots`. Fold them into the repo
   files (`ack <run ...>`; `plots SCOPE=a,b,c ...` with every scope that
   has its own choice, so the file equals the store).
2. Collect every site (sentinel per probe, retries), fetch with `ssh cat`.
3. Dump every site's queue in the format of 2.2.
4. Check finished runs: a training without its full-set eval gets one
   (section 5); read the newest logs for tracebacks.
5. Render from the repo script, publish in place (no `force`; on a
   conflict read the live version and merge).
6. Report in the `tick-it` layout; append changed readings to the
   project's progress log and commit one line `docs: ...`. Never push.

## 5. What is routine and what is not

- **Routine**: the full-set evaluation of a finished training under the
  run's own name, after checking that no job of the same spec runs; record
  it only once its log names the run's own checkpoint epoch. A chain that
  carries its own eval jobs gets none added.
- **Needs the user's word every time**: launching, cancelling,
  resubmitting or requeueing a training, however stuck it looks. Report
  what you see and what you would do.
- **Notify** on a finished or failed run.

## 6. Setting up a new project

When `tick-it` finds no setting for the repo, or the user asks for a new
scoreboard, interview first, then write the setting (custom half only),
show it, and ask before the first tick. Ask in rounds of at most four
questions (AskUserQuestion), recommended answer first; take what the repo
already answers (remote, tracker, configs, cluster aliases) from the repo
and only confirm it.

1. **Goal**: what is the project's claim, and which single number decides
   it (the headline metric)?
2. **Metrics**: which evaluation parameters to measure and show, which
   direction is better for each, at which thresholds (IoUs, ranges); is
   there a per-epoch series for them (needed for plots)?
3. **Plots**: plots when a training row opens (default yes); which three
   columns by default (default: the first three metric columns)?
4. **Tables**: one table per dataset or a paper layout (tables, groups,
   rows)? Which baselines are pinned, and what does each of our rows
   compare against (the baseline row, or the best competitor of its block)?
5. **Runs**: which runs are mains and which ablations? Is there a naming
   scheme for short IDs?
6. **Sites**: which clusters or machines, their paths, queue commands and
   how to submit (login shell, partitions, time limits)?
7. **Evaluation**: what is a full-set evaluation here (command, which
   checkpoint), and is it routine?
8. **Tracker and report**: wandb (or other) project; time zone of the
   page; tick cadence (default hourly on the hour); notify on finish and
   failure (default yes)?
9. **Scoreboard**: a new artifact, or an existing one (URL)? Confirmation
   boxes (default yes)?

The setting file then holds: front matter (`project`, `repo`, `local`,
`sites`, `updated`), where things are, the metrics, the table structure,
the eval command, and from then on the job history. Nothing of this file
is copied into it.
