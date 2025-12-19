"""
DEPRECATED: This standalone validator script is deprecated.

Chord voicing validation is now integrated into the songml-validate command.
Use: songml-validate <file.songml>

This file is kept for historical reference only.
"""

# Lightweight validator for chord_voicings.tsv

import re
from pathlib import Path

FILE = Path(r"c:\Projects\songml\songml-utils\src\songml_utils\data\chord_voicings.tsv")

ENH = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}


def parse_expected(q):
    q = q.lower()
    # ordered checks
    if "dim7" in q or "dim6" in q or (q.startswith("dim") and q != "dim"):
        return {0, 3, 6, 9}
    if "dim" in q:
        return {0, 3, 6}
    if "aug" in q or ("+" in q and not q.endswith("7")):
        return {0, 4, 8}
    if "+7" in q or "aug7" in q:
        return {0, 4, 8, 10}
    if "maj9" in q:
        return {0, 4, 7, 11, 14}
    if "maj7" in q:
        return {0, 4, 7, 11}
    if q == "" or q == "maj":
        return {0, 4, 7}
    if q == "7":
        return {0, 4, 7, 10}
    # handle minor 9 and minor 13 before generic 9/13
    if "m9" in q or "min9" in q:
        return {0, 3, 7, 10, 14}
    if "m13" in q or "min13" in q:
        return {0, 3, 7, 10, 14, 21}
    if "13" in q:
        return {0, 4, 7, 10, 14, 21}
    if "9" in q:
        return {0, 4, 7, 10, 14}
    if "6" in q and "m" in q:
        return {0, 3, 7, 9}
    if q == "6":
        return {0, 4, 7, 9}
    if "m7" in q or "min7" in q:
        return {0, 3, 7, 10}
    if q in ("m", "min", "-"):
        return {0, 3, 7}
    # fallback: major triad
    return {0, 4, 7}


def chroma(root):
    return ENH.get(root)


def split_symbol(sym):
    m = re.match(r"^([A-G][#b]?)(.*)$", sym)
    return (m.group(1), m.group(2)) if m else (None, None)


bad = []
with FILE.open(encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            bad.append((i, line, "bad format"))
            continue
        sym, root_name, offsets = parts[0], parts[1], parts[2]
        root, chq = split_symbol(sym)
        if root is None:
            bad.append((i, line, "can't parse symbol"))
            continue
        root_pc = chroma(root_name)
        if root_pc is None:
            bad.append((i, line, f"unknown root '{root_name}'"))
            continue
        expected_offsets = parse_expected(chq)
        # expected pitch classes
        expected_pcs = {(root_pc + o) % 12 for o in expected_offsets}
        offs = []
        for o in re.split(r"\s*,\s*", offsets):
            try:
                offs.append(int(o))
            except ValueError:
                bad.append((i, line, f"bad offset '{o}'"))
        for o in offs:
            pc = (root_pc + o) % 12
            if pc not in expected_pcs:
                bad.append(
                    (i, line, f"offset {o} -> pc {pc} not in expected pcs {sorted(expected_pcs)}")
                )
with open("chord_voicing_validation_report.txt", "w", encoding="utf-8") as out:
    if not bad:
        out.write("No problems found.\n")
    else:
        for it in bad:
            out.write(f"Line {it[0]}: {it[1]} -> {it[2]}\n")
print("Validation complete. See chord_voicing_validation_report.txt")
