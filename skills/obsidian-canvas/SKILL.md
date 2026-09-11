---
name: obsidian-canvas
description: >
  PLACEHOLDER — not in use. Reserved for generating an Obsidian canvas
  dashboard from a repo's progress.md. Does nothing today; do not invoke.
disable-model-invocation: true
---

# obsidian-canvas

**Deliberately empty.** Reserved so the idea has a home and a name; nothing
here is wired up yet. `disable-model-invocation: true` keeps it from firing
by accident — it can only be invoked by hand.

## Why it exists

[[python-project-init]] used to generate an Obsidian `.canvas` dashboard in
every new project. The canvas did not hold up in practice, so it was removed
from the scaffold. It may still be a good asset later, driven off the gantt
sections in `.docs/progress.md` rather than maintained by hand.

## What is already known

[templates/canvas.json.tmpl](templates/canvas.json.tmpl) is the working
template, kept verbatim.

**The one hard-won gotcha:** every node *and* every edge must include
`"styleAttributes": {}` or Obsidian >= 1.5 silently fails to render the
canvas — no error, just a blank page.

## If this is ever picked up

Sections in `.docs/progress.md` are the natural node set, and its `# Todos`
entries the natural leaves. Ask for input before generating; do not invent a
layout convention silently.
