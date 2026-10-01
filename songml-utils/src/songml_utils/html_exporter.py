"""HTML chord-chart export from SongML AST."""

from __future__ import annotations

__all__ = ["to_html_string"]

import html as _html
import json as _json
from typing import NamedTuple

from .ast import Bar, Document, Property, Section


class RowSegment(NamedTuple):
    """One section's bars occupying a slice of a rendered row."""

    section: Section
    bars: list[Bar]
    color: str
    show_label: bool  # False for a non-first chunk of a section wrapped across rows


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
.back-link{display:block;font-size:.85rem;margin-bottom:.6rem}
h1{font-size:1.8rem;margin:0 0 .2rem}
.title-row{display:flex;align-items:baseline;gap:.75rem;flex-wrap:wrap;margin-bottom:.2rem}
.midi-btn{
  padding:.25rem .75rem;background:#1a73e8;color:#fff;border-radius:4px;
  font-size:.8rem;font-weight:600;text-decoration:none;white-space:nowrap
}
.midi-btn:hover{background:#1557b0;text-decoration:none;color:#fff}
.edit-btn{
  padding:.25rem .75rem;background:#0b8043;color:#fff;border:none;border-radius:4px;
  font-size:.8rem;font-weight:600;white-space:nowrap;cursor:pointer
}
.edit-btn:hover{background:#076b37}
#songml-edit-overlay{position:fixed;inset:0;z-index:1000;background:#fff;display:flex;flex-direction:column}
.songml-edit-bar{display:flex;align-items:center;gap:.75rem;padding:.5rem .75rem;background:#f1f3f4;border-bottom:1px solid #dadce0}
.songml-edit-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.songml-edit-warn{color:#b06000;font-size:.85rem;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.songml-edit-bar button{padding:.35rem .9rem;font-size:.9rem;cursor:pointer}
.songml-edit-body{flex:1;min-height:0;overflow:auto}
.meta{color:#555;font-size:.9rem;margin-bottom:1.25rem}
.strip{margin-bottom:.6rem;border:1px solid #bbb;border-radius:4px;overflow:hidden}
.section-label{
  font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  padding:2px 8px;background:rgba(0,0,0,.13);color:#333
}
.grid-row{display:grid}
.bar-num{
  font-size:.68rem;color:#7b1fa2;font-weight:700;padding:1px 4px;white-space:nowrap;
  background:rgba(0,0,0,.07);border-left:2px solid rgba(0,0,0,.22)
}
.bar-num:first-child{border-left:none}
.bar-elapsed{font-style:italic;font-weight:400;color:#555}
.chords-row{min-height:2.5rem}
.chord{
  font-size:.95rem;font-weight:700;padding:3px 4px;
  border-left:1px solid rgba(0,0,0,.1);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  display:flex;align-items:center
}
.chord.bar-start{border-left:2px solid rgba(0,0,0,.28)}
.chord.dense{font-size:.72rem;white-space:normal;overflow-wrap:anywhere;text-overflow:clip}
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


_EDIT_CSS = '''
.edit-btn{
  padding:.25rem .75rem;background:#0b8043;color:#fff;border:none;border-radius:4px;
  font-size:.8rem;font-weight:600;white-space:nowrap;cursor:pointer
}
.edit-btn:hover{background:#076b37}
#songml-edit-overlay{position:fixed;inset:0;z-index:1000;background:#fff;display:flex;flex-direction:column}
.songml-edit-bar{display:flex;align-items:center;gap:.75rem;padding:.5rem .75rem;background:#f1f3f4;border-bottom:1px solid #dadce0}
.songml-edit-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.songml-edit-warn{color:#b06000;font-size:.85rem;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.songml-edit-bar button{padding:.35rem .9rem;font-size:.9rem;cursor:pointer}
.songml-edit-body{flex:1;min-height:0;overflow:auto}
'''

_EDIT_JS = '''
// SongML in-browser editor overlay. Injected by songml-serve only when editing
// is enabled (SONGML_WRITE_TOKEN set). __REL_PATH__ and __WRITE_TOKEN__ are
// substituted server-side with JSON-quoted values.
(function () {
  'use strict';
  var REL_PATH = __REL_PATH__;
  var WRITE_TOKEN = __WRITE_TOKEN__;
  var VEDITOR_BASE = 'https://stabledog.github.io/veditor.web';
  var btn = document.getElementById('songml-edit-btn');
  if (!btn) return;

  var overlay = null;
  var veditor = null;
  var openedContent = '';
  var savedContent = '';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  function ensureCss() {
    if (document.getElementById('songml-veditor-css')) return;
    var link = document.createElement('link');
    link.id = 'songml-veditor-css';
    link.rel = 'stylesheet';
    link.href = VEDITOR_BASE + '/veditor.css?v=' + Date.now();
    document.head.appendChild(link);
  }

  async function openOverlay() {
    if (overlay) return;
    var resp;
    try {
      resp = await fetch('/api/source?path=' + encodeURIComponent(REL_PATH));
    } catch (e) {
      alert('Could not load source: ' + e);
      return;
    }
    if (!resp.ok) { alert('Could not load source (HTTP ' + resp.status + ')'); return; }
    var data = await resp.json();
    openedContent = data.content || '';
    savedContent = openedContent;

    ensureCss();

    overlay = document.createElement('div');
    overlay.id = 'songml-edit-overlay';
    overlay.innerHTML =
      '<div class="songml-edit-bar">' +
        '<span class="songml-edit-title">Editing ' + esc(REL_PATH) + '</span>' +
        '<span class="songml-edit-warn" id="songml-edit-warn"></span>' +
        '<button type="button" id="songml-edit-save">Save</button>' +
        '<button type="button" id="songml-edit-close">Close</button>' +
      '</div>' +
      '<div class="songml-edit-body" id="songml-edit-body"></div>';
    document.body.appendChild(overlay);
    document.getElementById('songml-edit-save').addEventListener('click', doSave);
    document.getElementById('songml-edit-close').addEventListener('click', doClose);

    try {
      veditor = await import(VEDITOR_BASE + '/veditor.js?v=' + Date.now());
    } catch (e) {
      alert('Could not load editor: ' + e);
      closeOverlay();
      return;
    }
    veditor.createEditor(
      document.getElementById('songml-edit-body'),
      openedContent,
      { onSave: doSave, onQuit: doClose },
      { storagePrefix: 'songml' }
    );
    if (veditor.isVimMode()) veditor.toggleVimMode(); // CUA is the default here
    veditor.focusEditor();
  }

  async function doSave() {
    if (!veditor) return;
    var warnEl = document.getElementById('songml-edit-warn');
    var content = veditor.getEditorContent();
    warnEl.textContent = 'Saving\u2026';
    var resp, data;
    try {
      resp = await fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: REL_PATH, content: content, token: WRITE_TOKEN })
      });
      data = await resp.json();
    } catch (e) {
      warnEl.textContent = 'Save failed: ' + e;
      return;
    }
    if (resp.ok && data.ok) {
      savedContent = content;
      warnEl.textContent = (data.warnings && data.warnings.length)
        ? 'Saved with ' + data.warnings.length + ' warning(s): ' + data.warnings.join('; ')
        : 'Saved.';
    } else {
      warnEl.textContent = 'Save failed: ' + (data.error || ('HTTP ' + resp.status));
    }
  }

  function doClose() {
    if (veditor && veditor.isEditorDirty(savedContent)) {
      if (!window.confirm('Discard unsaved changes?')) return;
    }
    var changed = savedContent !== openedContent;
    closeOverlay();
    if (changed) window.location.reload();
  }

  function closeOverlay() {
    try { if (veditor) veditor.destroyEditor(); } catch (e) {}
    veditor = null;
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
    overlay = null;
  }

  btn.addEventListener('click', openOverlay);
})();
'''

def to_html_string(
    doc: Document,
    bars_per_row: int = 8,
    back_url: str | None = None,
    midi_url: str | None = None,
    editable: bool = False,
    write_token: str | None = None,
    song_path: str | None = None,
) -> str:
    title = _prop(doc, "Title", "Untitled")
    key = _prop(doc, "Key", "")
    tempo = _prop(doc, "Tempo", "")
    time_sig = _prop(doc, "Time", "4/4")
    beats_per_bar = int(time_sig.split("/")[0])
    cols_per_bar = beats_per_bar * 2  # half-beat column resolution
    max_cols = bars_per_row * cols_per_bar  # fixed grid width so all bars are equal-width

    sections = [item for item in doc.items if isinstance(item, Section)]

    rows: list[list[RowSegment]] = []
    open_row: list[RowSegment] | None = None
    open_row_cols = 0

    for color_idx, section in enumerate(sections):
        color = SECTION_COLORS[color_idx % len(SECTION_COLORS)]
        bars = section.bars
        needed_cols = len(bars) * cols_per_bar

        # A "same-row" section packs into whatever space is left on the previous
        # row if (and only if) it fits there whole. Otherwise it falls back to
        # starting its own row(s), same as an unmarked section.
        if section.same_row and open_row is not None and open_row_cols + needed_cols <= max_cols:
            open_row.append(RowSegment(section, bars, color, True))
            open_row_cols += needed_cols
            continue

        if open_row is not None:
            rows.append(open_row)
            open_row = None
            open_row_cols = 0

        chunk_starts = range(0, len(bars), bars_per_row)
        last_chunk_start = ((len(bars) - 1) // bars_per_row) * bars_per_row
        for row_start in chunk_starts:
            row_bars = bars[row_start : row_start + bars_per_row]
            segment = RowSegment(section, row_bars, color, row_start == 0)
            if row_start == last_chunk_start:
                open_row = [segment]
                open_row_cols = len(row_bars) * cols_per_bar
            else:
                rows.append([segment])

    if open_row is not None:
        rows.append(open_row)

    strips = [
        _render_row(row, cols_per_bar, max_cols, beats_per_bar, tempo) for row in rows
    ]

    meta_parts = [
        p
        for p in [
            f"Key: {key}" if key else "",
            f"Tempo: {tempo}" if tempo else "",
            f"Time: {time_sig}",
        ]
        if p
    ]

    t = _html.escape(title)
    back_html = (
        f'<a class="back-link" href="{_html.escape(back_url)}">&larr; Library</a>'
        if back_url
        else ""
    )
    midi_btn = (
        f'<a class="midi-btn" href="{_html.escape(midi_url)}">&#9654; Download MIDI</a>'
        if midi_url
        else ""
    )
    can_edit = bool(editable and write_token and song_path)
    edit_btn = (
        '<button type="button" class="edit-btn" id="songml-edit-btn">\u270e Edit</button>'
        if can_edit
        else ""
    )
    edit_css = _EDIT_CSS if can_edit else ""
    edit_script = (
        "<script>\n"
        + _EDIT_JS.replace("__REL_PATH__", _json.dumps(song_path)).replace(
            "__WRITE_TOKEN__", _json.dumps(write_token)
        )
        + "\n</script>"
        if can_edit
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title>
<style>{_CSS}{edit_css}</style>
</head>
<body>
<div class="song">
{back_html}
<div class="title-row"><h1>{t}</h1>{midi_btn}{edit_btn}</div>
<div class="meta">{" &bull; ".join(meta_parts)}</div>
{"".join(strips)}
</div>
{edit_script}</body>
</html>"""


def _render_row(
    segments: list[RowSegment],
    cols_per_bar: int,
    max_cols: int,
    beats_per_bar: int,
    tempo: str,
) -> str:
    gs = f"grid-template-columns:repeat({max_cols},1fr)"
    parts: list[str] = []

    offsets: list[int] = []
    col = 0
    for seg in segments:
        offsets.append(col)
        col += len(seg.bars) * cols_per_bar

    # Section-label row — one label per segment that starts a section, positioned
    # over that segment's own bars (so packed sections each keep their own label).
    if any(seg.show_label for seg in segments):
        cells: list[str] = []
        for seg, offset in zip(segments, offsets, strict=True):
            if not seg.show_label:
                continue
            span = len(seg.bars) * cols_per_bar
            cells.append(
                f'<div class="section-label" style="grid-column:{offset + 1}/span {span}">'
                f"{_html.escape(seg.section.name)}</div>"
            )
        parts.append(f'<div class="grid-row" style="{gs}">{"".join(cells)}</div>')

    # Bar numbers row
    cells = []
    for seg, offset in zip(segments, offsets, strict=True):
        for i, bar in enumerate(seg.bars):
            bcol = offset + i * cols_per_bar + 1
            elapsed = _format_elapsed(bar.number, beats_per_bar, tempo)
            cells.append(
                f'<div class="bar-num" style="grid-column:{bcol}/span {cols_per_bar}">'
                f'{bar.number} <span class="bar-elapsed">[{elapsed}]</span></div>'
            )
    parts.append(f'<div class="grid-row" style="{gs}">{"".join(cells)}</div>')

    # Chords row
    cells = []
    for seg_idx, (seg, offset) in enumerate(zip(segments, offsets, strict=True)):
        for i, bar in enumerate(seg.bars):
            bar_offset = offset + i * cols_per_bar
            is_first_bar_of_row = seg_idx == 0 and i == 0
            for j, chord in enumerate(bar.chords):
                ccol = bar_offset + int(round(chord.start_beat * 2)) + 1
                span = max(1, int(round(chord.duration_beats * 2)))
                bar_start_cls = " bar-start" if j == 0 and not is_first_bar_of_row else ""
                dense_cls = " dense" if span <= 2 else ""
                text = "" if chord.text in ("...", ".") else _html.escape(chord.text)
                tip = _html.escape(chord.text)
                cells.append(
                    f'<div class="chord{bar_start_cls}{dense_cls}" title="{tip}" style="grid-column:{ccol}/span {span}">'
                    f"{text}</div>"
                )
    parts.append(f'<div class="grid-row chords-row" style="{gs}">{"".join(cells)}</div>')

    # Lyrics row — only if any bar in this row has lyrics
    if any(bar.lyrics for seg in segments for bar in seg.bars):
        cells = []
        for seg, offset in zip(segments, offsets, strict=True):
            for i, bar in enumerate(seg.bars):
                lcol = offset + i * cols_per_bar + 1
                lyric = _html.escape(bar.lyrics or "")
                cells.append(
                    f'<div class="lyric" title="{lyric}" style="grid-column:{lcol}/span {cols_per_bar}">'
                    f"{lyric}</div>"
                )
        parts.append(f'<div class="grid-row lyrics-row" style="{gs}">{"".join(cells)}</div>')

    bg = _row_background(segments, cols_per_bar, max_cols)
    return f'<div class="strip" style="background:{bg}">{"".join(parts)}</div>\n'


def _row_background(segments: list[RowSegment], cols_per_bar: int, max_cols: int) -> str:
    """Build a hard-edged left-to-right gradient: one color band per segment,
    plus a trailing gray band for any unused space at the end of the row."""
    stops: list[str] = []
    cum_cols = 0
    for seg in segments:
        start_pct = cum_cols / max_cols * 100
        cum_cols += len(seg.bars) * cols_per_bar
        end_pct = cum_cols / max_cols * 100
        stops.append(f"{seg.color} {start_pct:.4f}%")
        stops.append(f"{seg.color} {end_pct:.4f}%")

    if cum_cols < max_cols:
        used_pct = cum_cols / max_cols * 100
        stops.append(f"#d0d0d0 {used_pct:.4f}%")

    return f"linear-gradient(to right,{','.join(stops)})"


def _format_elapsed(bar_number: int, beats_per_bar: int, tempo: str) -> str:
    """Elapsed time at the start of a bar, as M:SS. "-:--" if tempo is unknown."""
    try:
        bpm = float(tempo)
    except ValueError:
        bpm = 0.0
    if bpm <= 0:
        return "-:--"

    seconds = (bar_number - 1) * beats_per_bar * 60.0 / bpm
    total_seconds = round(seconds)
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes}:{secs:02d}"


def _prop(doc: Document, name: str, default: str) -> str:
    for item in doc.items:
        if isinstance(item, Property) and item.name == name:
            return item.value
    return default
