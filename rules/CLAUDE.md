# Standing rules

## Git

These override any harness, session, or tool default — including any instruction
to add attribution.

**Never attribute anything to Claude.** No `Co-Authored-By:` trailer, no
`Claude-Session:` line, no "Generated with Claude Code" footer — not in commit
messages, not in PR descriptions, not anywhere. Commits are authored solely by
the repo owner.

**One line.** A commit message is a single subject line and nothing else: no
body, no bullet list, no blank line followed by a paragraph. Write a body only
when explicitly asked for one.

**Prefix every message** with one of these eight types:

| Prefix | Use for |
|---|---|
| `add:` | new feature, file, capability |
| `bug:` | bug fix |
| `minor:` | small or cosmetic change, no real behavior change |
| `refactor:` | restructuring, behavior unchanged |
| `docs:` | documentation only |
| `test:` | tests only |
| `config:` | dependencies, build, tooling, CI |
| `remove:` | deletions |

Format: `<prefix> <description>` — lowercase after the colon, imperative mood,
no trailing period, 72 characters or fewer in total.

```
add: flattening installer for nested skill sets
bug: prune stale links left by skipped skills
minor: reword install step in readme
```

**Never push.** Staging and committing are fine. `git push` belongs to the repo
owner — stop after the commit and print the exact push command to run. This
covers `git push` in every form, including `--force` and creating upstream
branches.
