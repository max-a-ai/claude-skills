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
`> [!PDF|<color>]` highlight callouts. Output is a block printed to chat for
the user to paste — **the vault is never written to.**

## Highlight colours carry meaning

The colour was chosen while reading and is the most useful signal in the note:

| Colour | Means | Becomes |
|---|---|---|
| yellow, or no colour | worth keeping | a plain bullet |
| **red** | not understood while reading | `❓` inline **and** a `## Open` entry |
| **blue** | states something unusually well | a **bold** bullet, and first-choice material for the Excerpt |

## Steps

1. **Locate the note and the PDF.** The `## PDF` section links the paper
   vault-relative (`10-readings/20-pdf/<name>.pdf`). Resolve it against the
   vault root — the nearest ancestor directory containing `.obsidian/`.

2. **Parse the highlights:**
   ```bash
   python3 scripts/parse_highlights.py <note.md>
   ```
   It prints `## Open` and `## Notes concise`, already nested: a highlight
   like `3.1 Lift: Latent Depth Distribution` is recognised as a section
   title and the highlights after it nest beneath. Add `--figures` to keep a
   bullet where a figure was clipped. Take its output verbatim — it is
   mechanical, and re-deriving it by hand introduces drift.

3. **Read the PDF.** Always, even when the highlights look complete: the
   Excerpt states the research question, which is often a thing the
   highlights circle without saying. Papers run past the 10-page limit, so
   read in chunks of up to 20 pages.

4. **Write the Excerpt** — one main question, 2–4 secondary questions, then
   contributions:

   ```markdown
   ## Excerpt
   - Main Question: <the one question the paper exists to answer>
       - Answer: <one sentence>
   - Question: <a secondary thread the highlights keep returning to>
       - Answer: <one sentence>

   **Contributions**
   - <what the paper claims to have achieved>
   ```

   Draw the secondary questions from what was actually highlighted, not from
   what the paper advertises — the note records what this reader cared about.
   Blue highlights are the best raw material; quote them where they fit.
   One sentence per answer, and prefer the paper's own terms.

5. **Print the paste block** in this order, and say where it goes:
   `## Excerpt` replaces the empty stub near the top; `## Open` and
   `## Notes concise` go in immediately **above** the existing `## Notes`.

6. **Offer to resolve the red items.** The PDF is read by now, so each `##
   Open` entry can usually be answered in one line. Offer once; add the
   answers only if asked.

## Done when

- Every `###` subsection holding highlights appears under `## Notes concise`
- Every red highlight appears twice — `❓` inline and under `## Open`
- The Excerpt names one main question, 2–4 secondary ones, and the
  contributions, with one sentence per answer
- Nothing in the vault changed

## When the note fights back

- **No highlights found** — the script needs a `## Notes` section containing
  `[!PDF|…]` callouts. A note using a different annotation plugin needs the
  regexes in `scripts/parse_highlights.py` adjusted, not a hand-parse.
- **A section title was missed or over-detected** — detection keys on a
  leading `3.1`-style number, under 80 characters, with no closing period.
  Move the bullet by hand and say so.
- **Highlights are too sparse for an Excerpt** — write it from the PDF and
  flag which parts had no highlight behind them.
