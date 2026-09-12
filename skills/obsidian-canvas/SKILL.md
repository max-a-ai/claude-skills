---
name: obsidian-canvas
description: >
  PLACEHOLDER, not in use. Reserved for generating an Obsidian canvas
  dashboard from a repo's .docs/progress.md.
disable-model-invocation: true
---

# obsidian-canvas

Reserved so the idea keeps a name and its one hard-won detail. Nothing is
wired up.

[[python-project-init]] used to generate an Obsidian `.canvas` dashboard in
every new project. It did not hold up in practice and was dropped from the
scaffold. It may return, driven off the gantt sections in
`.docs/progress.md` rather than maintained by hand.

[templates/canvas.json.tmpl](templates/canvas.json.tmpl) is the working
template, kept verbatim. **Every node *and* every edge must carry
`"styleAttributes": {}`** — without it Obsidian >= 1.5 renders a blank page
and reports no error.

If this is ever picked up: `.docs/progress.md` sections are the natural
nodes, its `# Todos` the natural leaves. Ask for the layout convention
rather than inventing one.
