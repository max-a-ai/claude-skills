---
name: paper-notes
description: >
  Turn an Obsidian reading note full of PDF highlights into an Excerpt and
  concise bullet notes. Use when asked to summarise or write up a paper that
  has been highlighted, fill in a note's Excerpt, condense PDF highlights
  into bullets, or surface which terms in a paper went unexplained.
---

# paper-notes

Input is one Obsidian reading note whose `## Notes` section holds
`> [!PDF|<color>]` highlight callouts. The skill **writes back into that
note**: it fills the `## Excerpt` stub and inserts `## Open` and
`## Notes concise` above `## Notes`. `## Notes` itself is never touched.

## Highlight colours carry meaning

The colour was chosen while reading and is the most useful signal in the note:

| Colour | Means | Becomes |
|---|---|---|
| yellow, or no colour | worth keeping | a plain bullet |
| **red** | not understood while reading | `❓` inline **and** a `## Open` entry |
| **blue**, written `note` by PDF++ | states something unusually well | a **bold** bullet, and first-choice material for the Excerpt |

`[!PDF|note]` **is blue.** The PDF++ plugin ships the blue highlight under
the name `note`; `scripts/parse_highlights.py` maps it via `COLOR_ALIASES`.
A palette with further renamed colours needs a line added there, not a
hand-parse.

## Steps

1. **Locate the note and the PDF.** The `## PDF` section links the paper
   vault-relative (`10-readings/20-pdf/<name>.pdf`). Resolve it against the
   vault root, the nearest ancestor directory containing `.obsidian/`.

2. **Parse the highlights.** No flags, so nothing is written yet:
   ```bash
   python3 scripts/parse_highlights.py <note.md>
   ```
   It prints `## Open` and `## Notes concise`, already nested: a highlight
   like `3.1 Lift: Latent Depth Distribution` is recognised as a section
   title and the highlights after it nest beneath. Add `--figures` to keep a
   bullet where a figure was clipped. Read this output, since the bold (blue)
   bullets are what the Excerpt gets built from, but never retype it: step 5
   re-derives it, and hand-copying introduces drift.

3. **Read the PDF.** Always, even when the highlights look complete: the
   Excerpt states the research question, which is often a thing the
   highlights circle without saying. Papers run past the 10-page limit, so
   read in chunks of up to 20 pages.

4. **Write the Excerpt to a scratch file.** Include the `## Excerpt`
   heading; the whole section is replaced by this file.

   ```markdown
   ## Excerpt
   - Main Question: <the one question the paper exists to answer>
       - Answer: <one sentence>
   - Question: <a secondary thread the highlights keep returning to>
       - Answer: <one sentence>

   **Contributions**
   - <one short noun phrase per claim>
   ```

   **The Excerpt is a one minute read, and that is a hard ceiling.** In
   practice: one main question, two or three secondary ones, three or four
   contributions. Whoever opens this note in six months wants the gist in a
   glance, not the paper again in miniature.

   - One sentence per answer. No semicolon splicing a second sentence on.
   - Contributions are terse bullets, a line each, no sub-clauses. Numbers
     earn their place (`2x faster training`), adjectives do not.
   - Cut a secondary question before letting any answer sprawl. Three sharp
     ones beat five limp ones.

   Draw the secondary questions from what was actually highlighted, not from
   what the paper advertises. The note records what this reader cared about.
   Blue highlights are the best raw material; quote them where they fit, and
   prefer the paper's own terms.

5. **Apply it:**
   ```bash
   python3 scripts/parse_highlights.py <note.md> --write --excerpt <excerpt.md>
   ```
   This replaces `## Excerpt`, and inserts `## Open` and `## Notes concise`
   immediately above `## Notes`. The write is atomic and idempotent: it
   deletes any `## Open` / `## Notes concise` from a previous run first, so
   re-running the skill never duplicates sections. Report the one-line
   summary it prints.

6. **Offer to resolve the red items.** The PDF is read by now, so each
   `## Open` entry can usually be answered in one line. Offer once; add the
   answers only if asked.

## Done when

- The note contains `## Excerpt`, `## Open` and `## Notes concise`, in that
  order, with `## Notes` unchanged below them
- Every `###` subsection holding highlights appears under `## Notes concise`
- Every red highlight appears twice, `❓` inline and under `## Open`
- Every blue (`note`) highlight is a bold bullet
- The Excerpt reads in under a minute: one main question, two or three
  secondary ones, three or four terse contributions, one sentence per answer
- Nothing written anywhere contains an em dash

## When the note fights back

- **No highlights found.** The script needs a `## Notes` section containing
  `[!PDF|…]` callouts. A note using a different annotation plugin needs the
  regexes in `scripts/parse_highlights.py` adjusted, not a hand-parse.
- **`no '## Excerpt' section to replace` / `no '## Notes' section to insert
  above`.** The note is missing a heading the script anchors on. Add the
  empty heading to the note, then re-run; do not paste the sections by hand.
- **A section title was missed or over-detected.** Detection keys on a
  leading `3.1`-style number, under 80 characters, with no closing period.
  Fix the bullet in the note afterwards and say so.
- **A colour renders with the wrong meaning.** Add it to `COLOR_ALIASES`
  in the script rather than correcting the output.
- **Highlights are too sparse for an Excerpt.** Write it from the PDF and
  flag which parts had no highlight behind them.
