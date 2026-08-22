"""Tests for HTML chord-chart export, especially same-row section packing."""

from __future__ import annotations

import re

from songml_utils.html_exporter import to_html_string
from songml_utils.parser import parse_songml


def _strips(html: str) -> list[str]:
    return re.findall(r'<div class="strip".*?</div>\n', html, re.S)


def _labels(strip: str) -> list[str]:
    return re.findall(r'<div class="section-label"[^>]*>([^<]*)</div>', strip)


def test_unmarked_sections_each_get_their_own_row():
    content = """
[A - 4 bars]
| 1 | 2 | 3 | 4 |
| C | F | G | C |

[B - 4 bars]
| 5 | 6 | 7 | 8 |
| C | F | G | C |
"""
    doc = parse_songml(content)
    html = to_html_string(doc, bars_per_row=8)
    strips = _strips(html)
    assert len(strips) == 2
    assert _labels(strips[0]) == ["A"]
    assert _labels(strips[1]) == ["B"]


def test_same_row_section_packs_into_leftover_space():
    content = """
[A - 4 bars]
| 1 | 2 | 3 | 4 |
| C | F | G | C |

[B - 4 bars, same-row]
| 5 | 6 | 7 | 8 |
| C | F | G | C |
"""
    doc = parse_songml(content)
    html = to_html_string(doc, bars_per_row=8)
    strips = _strips(html)
    assert len(strips) == 1
    assert _labels(strips[0]) == ["A", "B"]

    bar_nums = re.findall(r'<div class="bar-num"[^>]*>(\d+)</div>', strips[0])
    assert bar_nums == ["1", "2", "3", "4", "5", "6", "7", "8"]


def test_same_row_section_falls_back_to_own_row_when_no_room():
    """A chain of same-row sections packs greedily; anything that doesn't fit
    on the current row starts its own new (still-open) row."""
    content = """
[S1 - 4 bars]
| 1 | 2 | 3 | 4 |
| C | F | G | C |

[S2 - 4 bars, same-row]
| 5 | 6 | 7 | 8 |
| C | F | G | C |

[S3 - 4 bars, same-row]
| 9 | 10 | 11 | 12 |
| C | F | G | C |

[S4 - 4 bars, same-row]
| 13 | 14 | 15 | 16 |
| C | F | G | C |

[S5 - 4 bars, same-row]
| 17 | 18 | 19 | 20 |
| C | F | G | C |
"""
    doc = parse_songml(content)
    html = to_html_string(doc, bars_per_row=8)
    strips = _strips(html)
    assert len(strips) == 3
    assert _labels(strips[0]) == ["S1", "S2"]
    assert _labels(strips[1]) == ["S3", "S4"]
    assert _labels(strips[2]) == ["S5"]


def test_same_row_section_that_would_overflow_gets_its_own_row():
    """A same-row section that can't fit whole into the remaining space falls
    back to a normal, independent row rather than being split."""
    content = """
[A - 6 bars]
| 1 | 2 | 3 | 4 | 5 | 6 |
| C | F | G | C | F | G |

[B - 4 bars, same-row]
| 7 | 8 | 9 | 10 |
| C | F | G | C |
"""
    doc = parse_songml(content)
    html = to_html_string(doc, bars_per_row=8)
    strips = _strips(html)
    assert len(strips) == 2
    assert _labels(strips[0]) == ["A"]
    assert _labels(strips[1]) == ["B"]


def test_first_section_ignores_same_row():
    """same-row on the very first section has nothing to attach to."""
    content = """
[A - 4 bars, same-row]
| 1 | 2 | 3 | 4 |
| C | F | G | C |
"""
    doc = parse_songml(content)
    html = to_html_string(doc, bars_per_row=8)
    strips = _strips(html)
    assert len(strips) == 1
    assert _labels(strips[0]) == ["A"]
