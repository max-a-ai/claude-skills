# Monitoring settings

One file per project that is being watched. The file is the *variable* half of
a monitoring setup: where the cluster is, which runs are mains and which are
ablations, what the evaluation parameters are, what this user asked for on this
project. The *invariant* half — tick on the hour, queue first, verbatim queue
block, sentinel every probe, republish in place, never launch a job unasked —
is the `tick-it` and `run-monitoring` skills, and is never copied in here.

## Naming

    monitoring-settings/<project>.md

The file is named after the project and nothing else: `lidar-bedlam.md`. No date
in the name, because the file is a living setting rather than a snapshot — a
date would say "written on" when what a reader wants is "true now", and two
dated files for one project is how a stale one gets read by mistake.

The date lives in two better places:

- `updated:` in the front matter, for a reader who has only the file.
- git, for everything else. `git log` is the version history, so a past state
  is pulled back without any naming convention at all:

      git -C ~/.claude-skills log --oneline -- monitoring-settings/lidar-bedlam.md
      git -C ~/.claude-skills show <sha>:monitoring-settings/lidar-bedlam.md

Dates are ISO (`2026-10-15`) wherever they are written, so they sort correctly
and `10-26` never has to be guessed at.

`archive/<YYYY-MM-DD>-<project>.md` is for a project whose monitoring has
*ended* — a phase closed, the runs retired, and the setting kept for reference.
A live project never has a file there.

## Index

| project | cluster | status | setting |
|---|---|---|---|
| lidar-bedlam | helma (NHR@FAU) | active | [lidar-bedlam.md](lidar-bedlam.md) |
