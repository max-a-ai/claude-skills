"""Turn an Obsidian PDF-highlight note into concise bullet notes.

Reads the `## Notes` section of a reading note, strips the `[!PDF|…]`
callout scaffolding, and prints two sections ready to paste:

    ## Open            red highlights -- terms that were not understood
    ## Notes concise   every highlight as a bullet, nested under the
                       section headings that were highlighted

    python3 parse_highlights.py <note.md> [--figures]

Colours carry meaning: yellow (or uncoloured) is a plain bullet, red is
prefixed with a question mark and repeated under `## Open`, blue is bold
because it states something unusually well.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CALLOUT = re.compile(r"^\[!PDF\s*\|\s*([a-zA-Z]*)\s*\]")
LINK_COLOR = re.compile(r"[&?]color=([a-zA-Z]+)")
PAGE = re.compile(r"\bp\.\s*(\d+)\s*\]\]")
EMBED = re.compile(r"^!\[\[")
SECTION = re.compile(r"^##\s+(.+?)\s*$")
SUBSECTION = re.compile(r"^###\s+(.+?)\s*$")
# "3.1 Lift: Latent Depth Distribution" -- a highlighted section title.
HEADING = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S")
HEADING_MAX = 80
RED, BLUE = "red", "blue"


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
            color = callout.group(1).lower()
            if not color:
                link = LINK_COLOR.search(content)
                color = link.group(1).lower() if link else "yellow"
            page_match = PAGE.search(content)
            pending = (color, page_match.group(1) if page_match else "")
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
        where = f" — {title}" if title else ""
        page = f" (p.{item.page})" if item.page else ""
        lines.append(f"- {item.text}{page}{where}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", type=Path)
    parser.add_argument(
        "--figures",
        action="store_true",
        help="also emit a bullet where a figure was clipped",
    )
    args = parser.parse_args()

    if not args.note.is_file():
        print(f"error: {args.note} not found", file=sys.stderr)
        return 1

    sections = parse(args.note.read_text(encoding="utf-8"), args.figures)
    if not sections:
        print(
            "error: no highlights found -- is there a '## Notes' section "
            "with [!PDF|…] callouts?",
            file=sys.stderr,
        )
        return 1

    opens = render_open(sections)
    if opens:
        print(opens)
    print(render_concise(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
