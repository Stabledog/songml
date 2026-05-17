"""HTML chord-chart export from SongML AST."""

from __future__ import annotations

__all__ = ["to_html_string"]

import html as _html

from .ast import Bar, Document, Property, Section

SECTION_COLORS = [
    "#fffde7",  # soft yellow
    "#e8f5e9",  # soft green
    "#e3f2fd",  # soft blue
    "#fce4ec",  # soft pink
    "#fff3e0",  # soft orange
    "#f3e5f5",  # soft purple
]

_CSS = """\
*,*::before,*::after{box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#e8e8e8;margin:0;padding:1rem;color:#111}
.song{max-width:1500px;margin:0 auto}
h1{font-size:1.8rem;margin:0 0 .2rem}
.meta{color:#555;font-size:.9rem;margin-bottom:1.25rem}
.strip{margin-bottom:.6rem;border:1px solid #bbb;border-radius:4px;overflow:hidden}
.section-label{
  font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  padding:2px 8px;background:rgba(0,0,0,.13);color:#333
}
.grid-row{display:grid}
.bar-num{
  font-size:.68rem;color:#555;padding:1px 4px;
  background:rgba(0,0,0,.07);border-left:2px solid rgba(0,0,0,.22)
}
.bar-num:first-child{border-left:none}
.chords-row{min-height:2.5rem}
.chord{
  font-size:.95rem;font-weight:700;padding:3px 4px;
  border-left:1px solid rgba(0,0,0,.1);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  display:flex;align-items:center
}
.chord.bar-start{border-left:2px solid rgba(0,0,0,.28)}
.lyrics-row{}
.lyric{
  font-size:.8rem;font-style:italic;color:#333;
  padding:1px 4px 3px;
  border-left:2px solid rgba(0,0,0,.15);
  border-top:1px solid rgba(0,0,0,.1);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis
}
.lyric:first-child{border-left:none}
a{color:#1a73e8;text-decoration:none}
a:hover{text-decoration:underline}
"""


def to_html_string(doc: Document, bars_per_row: int = 8) -> str:
    title = _prop(doc, "Title", "Untitled")
    key = _prop(doc, "Key", "")
    tempo = _prop(doc, "Tempo", "")
    time_sig = _prop(doc, "Time", "4/4")
    beats_per_bar = int(time_sig.split("/")[0])
    cols_per_bar = beats_per_bar * 2  # half-beat column resolution

    sections = [item for item in doc.items if isinstance(item, Section)]

    strips: list[str] = []
    for color_idx, section in enumerate(sections):
        color = SECTION_COLORS[color_idx % len(SECTION_COLORS)]
        bars = section.bars
        for row_start in range(0, max(len(bars), 1), bars_per_row):
            row_bars = bars[row_start : row_start + bars_per_row]
            if not row_bars:
                continue
            label = section.name if row_start == 0 else ""
            strips.append(_render_strip(row_bars, label, cols_per_bar, color))

    meta_parts = [p for p in [
        f"Key: {key}" if key else "",
        f"Tempo: {tempo}" if tempo else "",
        f"Time: {time_sig}",
    ] if p]

    t = _html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="song">
<h1>{t}</h1>
<div class="meta">{" &bull; ".join(meta_parts)}</div>
{"".join(strips)}
</div>
</body>
</html>"""


def _render_strip(bars: list[Bar], label: str, cols_per_bar: int, color: str) -> str:
    total_cols = len(bars) * cols_per_bar
    gs = f"grid-template-columns:repeat({total_cols},1fr)"
    parts: list[str] = []

    if label:
        parts.append(f'<div class="section-label">{_html.escape(label)}</div>')

    # Bar numbers row
    cells: list[str] = []
    for i, bar in enumerate(bars):
        col = i * cols_per_bar + 1
        cells.append(
            f'<div class="bar-num" style="grid-column:{col}/span {cols_per_bar}">'
            f"{bar.number}</div>"
        )
    parts.append(f'<div class="grid-row" style="{gs}">{"".join(cells)}</div>')

    # Chords row
    cells = []
    for i, bar in enumerate(bars):
        bar_offset = i * cols_per_bar
        for j, chord in enumerate(bar.chords):
            col = bar_offset + int(round(chord.start_beat * 2)) + 1
            span = max(1, int(round(chord.duration_beats * 2)))
            bar_start_cls = " bar-start" if j == 0 and i > 0 else ""
            text = "" if chord.text in ("...", ".") else _html.escape(chord.text)
            cells.append(
                f'<div class="chord{bar_start_cls}" style="grid-column:{col}/span {span}">'
                f"{text}</div>"
            )
    parts.append(f'<div class="grid-row chords-row" style="{gs}">{"".join(cells)}</div>')

    # Lyrics row — only if any bar in this strip has lyrics
    if any(bar.lyrics for bar in bars):
        cells = []
        for i, bar in enumerate(bars):
            col = i * cols_per_bar + 1
            lyric = _html.escape(bar.lyrics or "")
            cells.append(
                f'<div class="lyric" style="grid-column:{col}/span {cols_per_bar}">'
                f"{lyric}</div>"
            )
        parts.append(f'<div class="grid-row lyrics-row" style="{gs}">{"".join(cells)}</div>')

    return f'<div class="strip" style="background:{color}">{"".join(parts)}</div>\n'


def _prop(doc: Document, name: str, default: str) -> str:
    for item in doc.items:
        if isinstance(item, Property) and item.name == name:
            return item.value
    return default
