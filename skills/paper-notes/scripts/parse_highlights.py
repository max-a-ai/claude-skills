"""Turn an Obsidian PDF-highlight note into concise bullet notes.

Reads the `## Notes` section of a reading note, strips the `[!PDF|…]`
callout scaffolding, and produces two sections:

    ## Open            red highlights -- terms that were not understood
    ## Notes concise   every highlight as a bullet, nested under the
                       section headings that were highlighted

    python3 parse_highlights.py <note.md> [--figures]
    python3 parse_highlights.py <note.md> --write [--excerpt excerpt.md]

Without `--write` the sections are printed. With `--write` they are
inserted into the note itself, immediately above `## Notes`, and
`--excerpt` replaces the `## Excerpt` section with the contents of the
given file. Writing is idempotent: previously generated `## Open` and
`## Notes concise` sections are removed before the new ones go in, so
re-running never duplicates them.

Colours carry meaning: yellow (or uncoloured) is a plain bullet, red is
prefixed with a question mark and repeated under `## Open`, blue is bold
because it states something unusually well. Obsidian's PDF++ plugin ships
blue under the name `note`, so `[!PDF|note]` is treated as blue.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

CALLOUT = re.compile(r"^\[!PDF\s*\|\s*([a-zA-Z]*)\s*\]")
LINK_COLOR = re.compile(r"[&?]color=([a-zA-Z]+)")
PAGE = re.compile(r"\bp\.\s*(\d+)\s*\]\]")
EMBED = re.compile(r"^!\[\[")
SECTION = re.compile(r"^##\s+(.+?)\s*$")
SUBSECTION = re.compile(r"^###\s+(.+?)\s*$")
# A top-level heading -- '##' but not '###'.
H2 = re.compile(r"^##(?!#)\s+(.+?)\s*$")
# "3.1 Lift: Latent Depth Distribution" -- a highlighted section title.
HEADING = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S")
HEADING_MAX = 80
RED, BLUE = "red", "blue"

# The PDF++ palette names do not all match the meaning the skill assigns
# them. Map the plugin's names onto red / blue / yellow.
COLOR_ALIASES = {"note": BLUE}

# Sections this script owns: regenerated on every --write.
GENERATED = ("Notes concise", "Open")


def normalise_color(color: str) -> str:
    color = color.lower()
    return COLOR_ALIASES.get(color, color)


@dataclass
class Highlight:
    text: str
    color: str
    page: str

    @property
    def is_heading(self) -> bool:
        return (
            bool(HEADING.match(self.text))
            and len(self.text) <= HEADING_MAX
            and not self.text.endswith(".")
        )

    def render(self, indent: str = "") -> str:
        body = f"**{self.text}**" if self.color == BLUE else self.text
        mark = "❓ " if self.color == RED else ""
        return f"{indent}- {mark}{body}"


@dataclass
class Section:
    title: str
    items: list[Highlight] = field(default_factory=list)


def strip_quotes(line: str) -> str:
    """Remove the blockquote markers Obsidian nests the callouts in."""
    out = line
    while out.startswith(">"):
        out = out[1:].lstrip(" ")
    return out.strip()


def parse(note: str, keep_figures: bool) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    pending: tuple[str, str] | None = None
    buffer: list[str] = []
    in_notes = False

    def flush() -> None:
        nonlocal pending, buffer
        if pending and buffer:
            color, page = pending
            text = " ".join(buffer).strip()
            if text and current is not None:
                current.items.append(Highlight(text, color, page))
        pending, buffer = None, []

    for raw in note.splitlines():
        heading = SECTION.match(raw)
        if heading:
            flush()
            name = heading.group(1).strip().lower()
            in_notes = name == "notes"
            if in_notes and current is None:
                current = Section("")
                sections.append(current)
            continue
        if not in_notes:
            continue

        sub = SUBSECTION.match(raw)
        if sub:
            flush()
            current = Section(sub.group(1).strip())
            sections.append(current)
            continue

        content = strip_quotes(raw)
        if not content:
            flush()
            continue

        callout = CALLOUT.match(content)
        if callout:
            flush()
            color = callout.group(1)
            if not color:
                link = LINK_COLOR.search(content)
                color = link.group(1) if link else "yellow"
            page_match = PAGE.search(content)
            pending = (
                normalise_color(color),
                page_match.group(1) if page_match else "",
            )
            continue

        if EMBED.match(content):
            flush()
            if keep_figures and current is not None:
                page_match = PAGE.search(content)
                page = page_match.group(1) if page_match else "?"
                current.items.append(
                    Highlight(f"(figure, p.{page})", "yellow", page)
                )
            continue

        if pending:
            buffer.append(content)

    flush()
    return [s for s in sections if s.items]


def render_concise(sections: list[Section]) -> str:
    lines = ["## Notes concise", ""]
    for section in sections:
        if section.title:
            lines.append(f"### {section.title}")
        nested = False
        for item in section.items:
            if item.is_heading:
                lines.append(item.render())
                nested = True
            else:
                lines.append(item.render("    " if nested else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_open(sections: list[Section]) -> str:
    reds = [
        (section.title, item)
        for section in sections
        for item in section.items
        if item.color == RED
    ]
    if not reds:
        return ""
    lines = ["## Open", ""]
    for title, item in reds:
        # No em dash separator here: the house style forbids it, and this
        # string is written straight into the vault.
        bits = [b for b in (f"p.{item.page}" if item.page else "", title) if b]
        where = f" ({', '.join(bits)})" if bits else ""
        lines.append(f"- {item.text}{where}")
    return "\n".join(lines) + "\n"


def find_h2(lines: list[str], name: str) -> tuple[int, int] | None:
    """Span of the `## name` section, heading included, or None."""
    target = name.strip().lower()
    start: int | None = None
    for i, line in enumerate(lines):
        match = H2.match(line)
        if not match:
            continue
        if start is None:
            if match.group(1).strip().lower() == target:
                start = i
        else:
            return (start, i)
    return (start, len(lines)) if start is not None else None


def apply(note: str, concise: str, opens: str, excerpt: str | None) -> str:
    """Insert the generated sections into the note, replacing any prior run."""
    lines = note.splitlines()

    for name in GENERATED:
        while (span := find_h2(lines, name)) is not None:
            del lines[span[0] : span[1]]

    if excerpt is not None:
        span = find_h2(lines, "Excerpt")
        if span is None:
            raise ValueError("no '## Excerpt' section to replace")
        lines[span[0] : span[1]] = excerpt.rstrip().splitlines() + [""]

    span = find_h2(lines, "Notes")
    if span is None:
        raise ValueError("no '## Notes' section to insert above")

    block: list[str] = []
    if opens:
        block += opens.rstrip().splitlines() + [""]
    block += concise.rstrip().splitlines() + [""]
    lines[span[0] : span[0]] = block

    # splitlines()/join round-trips exactly, so the note's own trailing
    # blank lines survive -- everything below `## Notes` stays byte-identical.
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, text: str) -> None:
    handle, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", type=Path)
    parser.add_argument(
        "--figures",
        action="store_true",
        help="also emit a bullet where a figure was clipped",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="insert the sections into the note instead of printing them",
    )
    parser.add_argument(
        "--excerpt",
        type=Path,
        help="file whose contents replace the '## Excerpt' section",
    )
    args = parser.parse_args()

    if not args.note.is_file():
        print(f"error: {args.note} not found", file=sys.stderr)
        return 1
    if args.excerpt and not args.write:
        print("error: --excerpt requires --write", file=sys.stderr)
        return 1
    if args.excerpt and not args.excerpt.is_file():
        print(f"error: {args.excerpt} not found", file=sys.stderr)
        return 1

    note = args.note.read_text(encoding="utf-8")
    sections = parse(note, args.figures)
    if not sections:
        print(
            "error: no highlights found -- is there a '## Notes' section "
            "with [!PDF|…] callouts?",
            file=sys.stderr,
        )
        return 1

    opens = render_open(sections)
    concise = render_concise(sections)

    if not args.write:
        if opens:
            print(opens)
        print(concise)
        return 0

    excerpt = (
        args.excerpt.read_text(encoding="utf-8") if args.excerpt else None
    )
    try:
        updated = apply(note, concise, opens, excerpt)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    write_atomic(args.note, updated)

    reds = sum(
        1 for s in sections for i in s.items if i.color == RED
    )
    blues = sum(
        1 for s in sections for i in s.items if i.color == BLUE
    )
    total = sum(len(s.items) for s in sections)
    print(
        f"wrote {args.note.name}: {total} highlights "
        f"({reds} red, {blues} blue) across {len(sections)} sections"
        + ("; excerpt replaced" if excerpt else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
