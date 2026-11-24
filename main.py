#!/usr/bin/env python3
"""THE DAY IN 13 STORIES - world news of Monday 23 November 2026 in one image.

Visual-digest entry for make.fun news-image-20261123 (program/v1).
Pure standard library, no network, deterministic: the same bytes on every run.

Design (board-approved layout, panel-revised v7): one main hero story
filling the top of the canvas with a large flat illustration, four
secondary hero cards beneath it (a real illustration on top of each
card, full-width text below), and eight further stories as a
colour-dotted index in two columns: headline line(s) plus a small
source line. Every story prints the names of the sources that
corroborate it, right under its headline. Every illustration is a flat
bold PNG asset baked into this repository and contains no text at
all; every word is typeset by this program. Every story was checked
against at least two independent sources dated 2026-11-23 (see
research/corroboration-log.md, including the 24 Nov second sweep and
the four fact-check resolutions). The footer prints a colour legend
for the region chips, counts computed from the story lists, the
story-lock line, and a DATE CHECK list of other-day stories
deliberately excluded.
"""

import os
import struct
import sys
import zlib

SS = 2                      # supersample factor (render at 2048, ship 1024)
SIZE = 1024                 # final image is SIZE x SIZE
RW = SIZE * SS              # render width/height in device pixels

# ---------------------------------------------------------------- PNG codec

def png_decode(path):
    """Decode an 8-bit RGB or RGBA PNG (stdlib only) -> (w, h, rgb bytes)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    pos = 8
    idat = bytearray()
    width = height = bit_depth = colour_type = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, bit_depth, colour_type = struct.unpack(
                ">IIBB", chunk[:10])
        elif tag == b"IDAT":
            idat += chunk
        pos += 12 + length
    if bit_depth != 8 or colour_type not in (2, 6):
        raise ValueError("unsupported PNG format in %s" % path)
    channels = 3 if colour_type == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(width * height * 3)
    prev = bytearray(stride)
    ppos = 0
    for y in range(height):
        filt = raw[ppos]
        ppos += 1
        line = bytearray(raw[ppos:ppos + stride])
        ppos += stride
        if filt == 1:                       # Sub
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filt == 2:                     # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:                     # Average
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif filt == 4:                     # Paeth
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        if channels == 3:
            out[y * width * 3:(y + 1) * width * 3] = line
        else:
            rgb = bytearray(width * 3)
            rgb[0::3] = line[0::4]
            rgb[1::3] = line[1::4]
            rgb[2::3] = line[2::4]
            out[y * width * 3:(y + 1) * width * 3] = rgb
        prev = line
    return width, height, bytes(out)


def _chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def png_encode(width, height, rgb):
    """Encode RGB bytes as a deterministic PNG (per-row None/Sub choice)."""
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        row = bytes(rgb[y * stride:(y + 1) * stride])
        shifted = b"\x00\x00\x00" + row[:-3]
        sub = bytes((a - b) & 0xFF for a, b in zip(row, shifted))
        score_raw = sum(b if b < 128 else 256 - b for b in row[::11])
        score_sub = sum(b if b < 128 else 256 - b for b in sub[::11])
        if score_sub < score_raw:
            raw.append(1)
            raw += sub
        else:
            raw.append(0)
            raw += row
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png

# ------------------------------------------------------------------- font
# Bold block grotesque, 6 x 9 grid, drawn as filled rectangles. One case:
# every string is normalised to upper case before drawing. Body text can
# be drawn "light" (inset cells), a thinner-weight variant of the same
# grotesque, so summaries read softer than the bold headlines.

_FONT_ROWS = {
    "A": (".####.", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##", "##..##"),
    "B": ("#####.", "##..##", "##..##", "#####.", "##..##", "##..##", "##..##", "##..##", "#####."),
    "C": (".####.", "##..##", "##....", "##....", "##....", "##....", "##....", "##..##", ".####."),
    "D": ("####..", "##.##.", "##..##", "##..##", "##..##", "##..##", "##..##", "##.##.", "####.."),
    "E": ("######", "##....", "##....", "#####.", "##....", "##....", "##....", "##....", "######"),
    "F": ("######", "##....", "##....", "#####.", "##....", "##....", "##....", "##....", "##...."),
    "G": (".####.", "##..##", "##....", "##.###", "##..##", "##..##", "##..##", "##..##", ".###.."),
    "H": ("##..##", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##", "##..##"),
    "I": ("######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "######"),
    "J": ("######", "...##.", "...##.", "...##.", "...##.", "...##.", "##.##.", "##.##.", ".###.."),
    "K": ("##..##", "##.##.", "##.#..", "###...", "##.#..", "##.##.", "##..##", "##..##", "##..##"),
    "L": ("##....", "##....", "##....", "##....", "##....", "##....", "##....", "##....", "######"),
    "M": ("##...##", "##...##", "###.###", "##.#.##", "##.#.##", "##...##", "##...##", "##...##", "##...##"),
    "N": ("##...##", "##...##", "###..##", "##.#.##", "##..###", "##...##", "##...##", "##...##", "##...##"),
    "O": (".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."),
    "P": ("#####.", "##..##", "##..##", "#####.", "##....", "##....", "##....", "##....", "##...."),
    "Q": (".####.", "##..##", "##..##", "##..##", "##..##", "##.###", "##..##", "##..##", ".###.#"),
    "R": ("#####.", "##..##", "##..##", "#####.", "##.#..", "##.##.", "##..##", "##..##", "##..##"),
    "S": (".#####", "##....", "##....", ".####.", "....##", "....##", "....##", "##..##", "#####."),
    "T": ("######", "######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."),
    "U": ("##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."),
    "V": ("##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####.", "..##.."),
    "W": ("##...##", "##...##", "##...##", "##...##", "##...##", "##.#.##", "##.#.##", "##.#.##", ".##.##."),
    "X": ("##..##", "##..##", ".####.", "..##..", "..##..", ".####.", "##..##", "##..##", "##..##"),
    "Y": ("##..##", "##..##", "##..##", ".####.", "..##..", "..##..", "..##..", "..##..", "..##.."),
    "Z": ("######", "######", "...##.", "..##..", "..##..", "..##..", ".##...", "##....", "######"),
    "0": (".####.", "##..##", "##.###", "##.###", "###.##", "###.##", "##..##", "##..##", ".####."),
    "1": ("..##..", ".###..", "####..", "..##..", "..##..", "..##..", "..##..", "..##..", "######"),
    "2": (".####.", "##..##", "....##", "...##.", "..##..", ".##...", "##....", "##....", "######"),
    "3": ("#####.", "##..##", "....##", "..###.", "....##", "....##", "....##", "##..##", "#####."),
    "4": ("...##.", "..###.", ".####.", "##.##.", "######", "...##.", "...##.", "...##.", "...##."),
    "5": ("######", "######", "##....", "#####.", "....##", "....##", "....##", "##..##", ".####."),
    "6": (".####.", "##..##", "##....", "#####.", "##..##", "##..##", "##..##", "##..##", ".####."),
    "7": ("######", "######", "....##", "...##.", "...##.", "..##..", "..##..", "..##..", "..##.."),
    "8": (".####.", "##..##", "##..##", ".####.", "##..##", "##..##", "##..##", "##..##", ".####."),
    "9": (".####.", "##..##", "##..##", "##..##", ".#####", "....##", "....##", "##..##", ".####."),
    " ": ("......", "......", "......", "......", "......", "......", "......", "......", "......"),
    ".": ("......", "......", "......", "......", "......", "......", "......", ".##...", ".##..."),
    ",": ("......", "......", "......", "......", "......", "......", ".##...", ".##...", "##...."),
    ":": ("......", "......", "##....", "##....", "......", "......", "##....", "##....", "......"),
    ";": ("......", "......", "##....", "##....", "......", "......", ".##...", ".##...", "##...."),
    "'": ("..##..", "..##..", "..##..", "......", "......", "......", "......", "......", "......"),
    "-": ("......", "......", "......", "......", "######", "######", "......", "......", "......"),
    "+": ("......", "..##..", "..##..", "######", "######", "..##..", "..##..", "......", "......"),
    "%": ("##...#", "##..##", "....##", "...##.", "..##..", ".##...", "##....", "##..##", "#...##"),
    "/": ("....##", "....##", "...##.", "...##.", "..##..", "..##..", ".##...", "##....", "##...."),
    "(": ("...###", "..##..", "..##..", ".##...", ".##...", ".##...", "..##..", "..##..", "...###"),
    ")": ("###...", "..##..", "..##..", "...##.", "...##.", "...##.", "..##..", "..##..", "###..."),
    "!": ("..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "......", "..##.."),
    "?": (".####.", "##..##", "....##", "...##.", "..##..", "..##..", "......", "......", "..##.."),
    "&": (".###..", "##.##.", "##.##.", ".###..", "####..", "##.##.", "##..##", "##..##", ".###.#"),
    "·": ("......", "......", "......", "......", ".##...", ".##...", "......", "......", "......"),
}

_ACCENTS = {
    "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "À": "A", "È": "E",
    "Ä": "A", "Ö": "O", "Ü": "U", "Ç": "C", "Ñ": "N", "—": "-", "–": "-",
    "−": "-", "’": "'", "‘": "'", "“": "", "”": "", "×": "X",
}


def normalise(text):
    out = []
    for ch in text.upper():
        out.append(_ACCENTS.get(ch, ch))
    return "".join(out)


def _advance(ch, unit):
    glyph = _FONT_ROWS.get(ch, _FONT_ROWS[" "])
    return (len(glyph[0]) + 1) * unit


def text_width(text, unit):
    """Width in final-image pixels of `text` at the given font unit."""
    text = normalise(text)
    if not text:
        return 0
    return sum(_advance(ch, unit) for ch in text) - unit


def wrap_text(text, unit, max_width):
    """Greedy word wrap; returns the list of lines (each fits max_width)."""
    words = normalise(text).split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, unit) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

# ------------------------------------------------------------ stroke font
# A second, smoother typeface for body copy: single-stroke vector
# glyphs (Hershey-simplex style) on a 15-unit em grid (cap top y=1,
# baseline y=12, descenders to y=14.5), drawn as stamped line segments.
# Panel rounds 1-4 named the chunky 6x9 block grotesque as the top
# defect: its counters fill in and the index strip collapses into
# texture at the 300px judging size. The stroke face keeps open
# counters and even grey value when downscaled. Glyph x-coordinates
# are compressed by _S2_XS so advances stay close to the block face.
# Used for summaries, source lines, the index, the legend and the
# footer; the block face stays for the masthead and the big headlines.

import math


def _arc(cx, cy, rx, ry, a0, a1, n=14):
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((round(cx + rx * math.cos(a), 2),
                    round(cy + ry * math.sin(a), 2)))
    return pts


# char -> (width in grid units, [stroke, ...]); a stroke is a list of
# (x, y) points joined by straight segments.
_STROKES = {
    "A": (9, [[(0, 12), (4.5, 1), (9, 12)], [(2.4, 8.6), (6.6, 8.6)]]),
    "B": (8.5, [[(0, 1), (0, 12)],
                [(0, 1), (3.8, 1)] + _arc(3.8, 3.9, 3.9, 2.9, -90, 90)
                + [(0, 6.8)],
                [(0, 6.8), (4.2, 6.8)] + _arc(4.2, 9.4, 4.3, 2.6, -90, 90)
                + [(0, 12)]]),
    "C": (9, [_arc(4.6, 6.5, 4.4, 5.5, -55, -305)]),
    "D": (9, [[(0, 1), (0, 12)],
              [(0, 1), (3.8, 1)] + _arc(3.8, 6.5, 4.6, 5.5, -90, 90)
              + [(0, 12)]]),
    "E": (8, [[(8, 1), (0, 1), (0, 12), (8, 12)], [(0, 6.5), (6.3, 6.5)]]),
    "F": (7.5, [[(7.5, 1), (0, 1), (0, 12)], [(0, 6.5), (5.8, 6.5)]]),
    "G": (9, [_arc(4.6, 6.5, 4.4, 5.5, -55, -305),
              [(5.2, 6.8), (8.8, 6.8), (8.8, 10)]]),
    "H": (9, [[(0, 1), (0, 12)], [(9, 1), (9, 12)], [(0, 6.5), (9, 6.5)]]),
    "I": (3, [[(1.5, 1), (1.5, 12)], [(0, 1), (3, 1)], [(0, 12), (3, 12)]]),
    "J": (6, [[(6, 1), (6, 8.6)] + _arc(3, 8.6, 3, 3.4, 0, 180),
              [(0, 8.6), (0, 6.8)]]),
    "K": (8.5, [[(0, 1), (0, 12)], [(8.3, 1), (0.6, 6.9)],
                [(2.4, 5.4), (8.5, 12)]]),
    "L": (8, [[(0, 1), (0, 12), (8, 12)]]),
    "M": (11, [[(0, 12), (0, 1), (5.5, 7.6), (11, 1), (11, 12)]]),
    "N": (9, [[(0, 12), (0, 1), (9, 12), (9, 1)]]),
    "O": (9, [_arc(4.5, 6.5, 4.4, 5.5, 0, 360)]),
    "P": (8.5, [[(0, 1), (0, 12)],
                [(0, 1), (3.9, 1)] + _arc(3.9, 3.9, 4, 2.9, -90, 90)
                + [(0, 6.8)]]),
    "Q": (9, [_arc(4.5, 6.5, 4.4, 5.5, 0, 360), [(5.9, 9.3), (9.3, 13)]]),
    "R": (8.5, [[(0, 1), (0, 12)],
                [(0, 1), (3.9, 1)] + _arc(3.9, 3.9, 4, 2.9, -90, 90)
                + [(0, 6.8)],
                [(4.3, 6.8), (8.5, 12)]]),
    "S": (9, [[(8.5, 3.1), (6.3, 1.2), (3, 1.1), (0.9, 2.6), (0.8, 4.9),
               (2.9, 6.4), (6.4, 7.9), (8.6, 9.6), (8.4, 11.2),
               (6, 12.1), (2.9, 12.1), (0.7, 10.9)]]),
    "T": (9, [[(0, 1), (9, 1)], [(4.5, 1), (4.5, 12)]]),
    "U": (9, [[(0, 1), (0, 8.2)] + _arc(4.5, 8.2, 4.5, 3.8, 180, 0)
              + [(9, 8.2), (9, 1)]]),
    "V": (9, [[(0, 1), (4.5, 12), (9, 1)]]),
    "W": (12, [[(0, 1), (2.9, 12), (6, 4.2), (9.1, 12), (12, 1)]]),
    "X": (9, [[(0, 1), (9, 12)], [(9, 1), (0, 12)]]),
    "Y": (9, [[(0, 1), (4.5, 6.6), (9, 1)], [(4.5, 6.6), (4.5, 12)]]),
    "Z": (9, [[(0, 1), (9, 1), (0, 12), (9, 12)]]),
    "0": (9, [_arc(4.5, 6.5, 4.1, 5.5, 0, 360)]),
    "1": (7, [[(2.2, 3.4), (4.6, 1), (4.6, 12)], [(1.6, 12), (6.8, 12)]]),
    "2": (9, [[(0.9, 3.4), (2.1, 1.4), (4.3, 1.0), (6.8, 1.3), (8.4, 3.0),
               (8.3, 5.4), (0.8, 12), (8.6, 12)]]),
    "3": (9, [[(0.8, 2.4), (2.9, 1.1), (5.9, 1.1), (7.9, 2.7), (7.8, 5.0),
               (6.1, 6.4), (3.4, 6.4)],
              [(6.1, 6.4), (8.1, 7.7), (8.0, 10.3), (5.9, 12.1),
               (2.7, 12.0), (0.7, 10.7)]]),
    "4": (9, [[(6.4, 12), (6.4, 1), (0.7, 9.3), (9, 9.3)]]),
    "5": (9, [[(8.2, 1), (1.3, 1), (1.1, 5.9), (3.4, 5.1), (6.3, 5.3),
               (8.3, 7.5), (8.1, 10.2), (5.9, 12.1), (2.7, 12.0),
               (0.8, 10.6)]]),
    "6": (9, [[(7.6, 2.3), (4.7, 1.1), (2.3, 2.5), (1.1, 5.6), (0.9, 8.6)],
              _arc(4.5, 8.8, 3.9, 3.2, 0, 360)]),
    "7": (9, [[(0.7, 1), (8.6, 1), (3.9, 12)]]),
    "8": (9, [_arc(4.5, 4.1, 3.3, 3.0, 0, 360),
              _arc(4.5, 9.3, 4.0, 3.1, 0, 360)]),
    "9": (9, [_arc(4.5, 4.2, 3.9, 3.2, 0, 360),
              [(8.7, 4.6), (8.1, 8.6), (6.7, 11.0), (4.4, 12.2),
               (1.7, 11.3)]]),
    " ": (5, []),
    ".": (3, [[(1.5, 11.4), (1.5, 12.3)]]),
    ",": (3, [[(1.9, 11.2), (1.1, 14.2)]]),
    ":": (3, [[(1.5, 3.7), (1.5, 4.5)], [(1.5, 11.3), (1.5, 12.2)]]),
    ";": (3, [[(1.5, 3.7), (1.5, 4.5)], [(1.9, 11.2), (1.1, 14.2)]]),
    "'": (3, [[(1.5, 1), (1.5, 3.1)]]),
    "-": (6, [[(0.5, 6.5), (5.5, 6.5)]]),
    "+": (7, [[(0.5, 6.5), (6.5, 6.5)], [(3.5, 3.5), (3.5, 9.5)]]),
    "%": (11, [_arc(2.3, 3.6, 1.9, 1.9, 0, 360),
               _arc(8.7, 9.4, 1.9, 1.9, 0, 360),
               [(8.6, 1.6), (2.4, 11.6)]]),
    "/": (6, [[(5.5, 1), (0.5, 12)]]),
    "(": (5, [_arc(4.6, 6.5, 3.4, 5.8, 55, 305)]),
    ")": (5, [_arc(0.4, 6.5, 3.4, 5.8, -55, 55)]),
    "!": (3, [[(1.5, 1), (1.5, 8.6)], [(1.5, 11.3), (1.5, 12.2)]]),
    "?": (8, [[(0.8, 3.3), (1.9, 1.4), (5.3, 1.1), (7.4, 2.5), (7.3, 4.7),
               (5.7, 6.1), (4.1, 7.1), (4.1, 9.2)],
              [(4.1, 11.3), (4.1, 12.2)]]),
    "&": (9, [_arc(3.9, 3.6, 2.5, 2.3, 0, 360),
              [(6.1, 2.0), (1.6, 8.4), (1.3, 10.9), (3.1, 12.2),
               (6.3, 11.5), (8.7, 8.7)],
              [(5.3, 7.3), (8.7, 11.9)]]),
    "·": (3, [[(1.5, 6.3), (1.5, 7.1)]]),
}
_S2_XS = 0.8             # horizontal compression of glyph coordinates
_S2_TRACK = 1.8          # letter tracking in grid units
S2_CAP = 11.0            # cap height in grid units (y 1..12)
S2_BOX = 13.0            # line-box allowance in grid units


def _s2_glyph(ch):
    return _STROKES.get(ch, _STROKES[" "])


def _s2_advance(ch, unit):
    return (_s2_glyph(ch)[0] * _S2_XS + _S2_TRACK) * unit


def text_width2(text, unit):
    """Width in final-image pixels of `text` in the stroke face."""
    text = normalise(text)
    if not text:
        return 0
    return sum(_s2_advance(ch, unit) for ch in text) - _S2_TRACK * unit


def wrap_text2(text, unit, max_width):
    """Greedy word wrap for the stroke face."""
    words = normalise(text).split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width2(trial, unit) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_unit2(text, units, max_width):
    for unit in units:
        if text_width2(text, unit) <= max_width:
            return unit
    return units[-1]

# ----------------------------------------------------------------- canvas

class Canvas:
    """RGB framebuffer at supersampled resolution; coordinates are given
    in final-image pixels and scaled by SS internally."""

    def __init__(self, colour):
        self.fb = bytearray(bytes(colour) * (RW * RW))

    def rect(self, x, y, w, h, colour):
        x0, y0 = int(round(x * SS)), int(round(y * SS))
        x1, y1 = int(round((x + w) * SS)), int(round((y + h) * SS))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            off = (yy * RW + x0) * 3
            self.fb[off:off + len(row)] = row

    def blit(self, img_rgb, img_w, img_h, x, y):
        """Copy an image whose size already matches the SS-scaled target."""
        x0, y0 = int(round(x * SS)), int(round(y * SS))
        for yy in range(img_h):
            off = ((y0 + yy) * RW + x0) * 3
            src = yy * img_w * 3
            self.fb[off:off + img_w * 3] = img_rgb[src:src + img_w * 3]

    def blit_cover(self, img_rgb, img_w, img_h, x, y, w, h,
                   focus_x=0.5, focus_y=0.5):
        """Scale an image to cover the (x, y, w, h) box, cropping the
        overflow around the focus point. Nearest neighbour; the box is
        given in final-image pixels, the image in its own pixels."""
        tw, th = int(round(w * SS)), int(round(h * SS))
        x0, y0 = int(round(x * SS)), int(round(y * SS))
        scale = max(tw / img_w, th / img_h)
        sw, sh = tw / scale, th / scale
        sx0 = min(max((img_w - sw) * focus_x, 0.0), img_w - sw)
        sy0 = min(max((img_h - sh) * focus_y, 0.0), img_h - sh)
        fb, stride = self.fb, RW * 3
        for dy in range(th):
            sy = int(sy0 + dy / scale)
            if sy >= img_h:
                sy = img_h - 1
            src_row = sy * img_w * 3
            off = (y0 + dy) * stride + x0 * 3
            for dx in range(tw):
                sx = int(sx0 + dx / scale)
                if sx >= img_w:
                    sx = img_w - 1
                s = src_row + sx * 3
                o = off + dx * 3
                fb[o] = img_rgb[s]
                fb[o + 1] = img_rgb[s + 1]
                fb[o + 2] = img_rgb[s + 2]

    def text(self, x, y, text, unit, colour, light=False):
        """Draw one line of text; (x, y) is the top-left in final pixels.
        light=True insets every filled cell, giving a thinner weight."""
        text = normalise(text)
        cursor = float(x)
        inset = unit * 0.14 if light else 0.0
        for ch in text:
            glyph = _FONT_ROWS.get(ch, _FONT_ROWS[" "])
            for row_i, row in enumerate(glyph):
                run = 0
                for col_i, cell in enumerate(row + "."):
                    if cell == "#":
                        run += 1
                    elif run:
                        gx = cursor + (col_i - run) * unit
                        gy = y + row_i * unit
                        self.rect(gx + inset, gy + inset,
                                  run * unit - 2 * inset,
                                  unit - 2 * inset, colour)
                        run = 0
            cursor += _advance(ch, unit)
        return cursor - unit

    def text_right(self, x_right, y, text, unit, colour):
        self.text(x_right - text_width(text, unit), y, text, unit, colour)

    def text_centred(self, cx, y, text, unit, colour):
        self.text(cx - text_width(text, unit) / 2.0, y, text, unit, colour)

    def _stamp(self, px, py, t, colour):
        self.rect(px - t / 2.0, py - t / 2.0, t, t, colour)

    def _seg(self, x0, y0, x1, y1, t, colour):
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(dist / (t * 0.35)))
        for i in range(steps + 1):
            f = i / steps
            self._stamp(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, t, colour)

    def text2(self, x, y, text, unit, colour):
        """Draw one line in the stroke face; (x, y) is the top-left of
        the em box in final-image pixels. Returns the end x, matching
        text_width2, like text() does for the block face."""
        text = normalise(text)
        t = max(0.95, 1.5 * unit)
        cursor = float(x)
        for ch in text:
            w, strokes = _s2_glyph(ch)
            for stroke in strokes:
                pts = [(cursor + gx * _S2_XS * unit, y + gy * unit)
                       for gx, gy in stroke]
                if len(pts) == 1:
                    self._stamp(pts[0][0], pts[0][1], t * 1.2, colour)
                for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                    self._seg(ax, ay, bx, by, t, colour)
            cursor += (w * _S2_XS + _S2_TRACK) * unit
        return cursor - _S2_TRACK * unit


def downscale(rgb, src_w, factor):
    """Box-average downscale by an integer factor."""
    dst_w = src_w // factor
    stride = src_w * 3
    out = bytearray(dst_w * dst_w * 3)
    for dy in range(dst_w):
        for dx in range(dst_w):
            r = g = b = 0
            for oy in range(factor):
                base = ((dy * factor + oy) * stride) + dx * factor * 3
                for ox in range(factor):
                    i = base + ox * 3
                    r += rgb[i]
                    g += rgb[i + 1]
                    b += rgb[i + 2]
            n = factor * factor
            o = (dy * dst_w + dx) * 3
            out[o] = r // n
            out[o + 1] = g // n
            out[o + 2] = b // n
    return bytes(out)

# ---------------------------------------------------------------- content
# Every story below carries its corroboration: the number of independent
# sources and their names, all dated 2026-11-23 (see
# research/corroboration-log.md). --test asserts names count == sources
# and sources >= 2 for every story.

BG = (11, 18, 32)
PANEL = (242, 238, 227)
INK = (18, 22, 30)
SUMMARY_INK = (62, 68, 80)
OFFWHITE = (233, 235, 240)
MUTED = (141, 151, 169)
GOLD = (255, 194, 77)
WHITE = (255, 255, 255)

# region -> (chip label, colour, dark text colour, footer label)
REGIONS = {
    "EU": ("EUROPE", (62, 123, 250), (38, 92, 205), "EUROPE"),
    "ME": ("MIDEAST", (232, 134, 46), (188, 102, 22), "MIDEAST"),
    "AP": ("ASIA-PACIFIC", (224, 82, 82), (186, 52, 52), "ASIA-PACIFIC"),
    "NA": ("N AMERICA", (139, 92, 246), (106, 62, 205), "N AMERICA"),
    "AF": ("AFRICA", (216, 178, 44), (148, 116, 16), "AFRICA"),
    "SA": ("S AMERICA", (47, 168, 79), (30, 128, 58), "S AMERICA"),
    "SCI": ("SPACE", (31, 154, 170), (20, 118, 132), "SPACE"),
}
REGION_ORDER = ["EU", "ME", "AP", "NA", "AF", "SA", "SCI"]

MAIN_HERO = {
    "img": "hero-main-cop31.png", "region": "EU", "field": "CLIMATE",
    "headline": "CLIMATE TALKS COLLAPSE IN TURKEY",
    "summary": "IN ANTALYA, FOSSIL-FUEL WORDING KILLS THE DEAL; "
               "NO AGREEMENT AFTER TWO DAYS OF OVERTIME.",
    "detail": "TALKS PRESIDENT WALKS OUT; 130 PARTIES REJECT TEXT.",
    "sources": 4,
    "srcs": "SCMP · QATAR TRIBUNE · JUST SECURITY · ONETURN",
}

SECONDARY = [
    {"img": "hero3-kyiv.png", "region": "EU", "field": "WAR",
     "headline": "STRIKE KILLS 11 NEAR KYIV",
     "summary": "RUSSIAN DRONE HIT A DYMER APARTMENT BLOCK.",
     "sources": 3, "srcs": "REUTERS · AL JAZEERA · UKRINFORM",
     "focus_y": 0.72},
    {"img": "hero2-hormuz.png", "region": "ME", "field": "CONFLICT",
     "headline": "IRAN ATTACKS INTERCEPTED",
     "summary": "BAHRAIN HALTS IRAN ATTACKS; TRUMP WARNS SHIPS.",
     "sources": 3, "srcs": "REUTERS · GULF NEWS · BREITBART",
     "focus_y": 0.40},
    {"img": "hero-us-rally.png", "region": "NA", "field": "MARKETS",
     "headline": "WALL ST'S BEST DAY SINCE APRIL",
     "summary": "NVIDIA CEO JENSEN HUANG BACK 11 DAYS AFTER "
                "RESIGNING; S&P +4.7%, NASDAQ +6.5%.",
     "sources": 4, "srcs": "WSJ · XINHUA · INVESTOPEDIA · ONETURN",
     "focus_y": 0.30},
    {"img": "hero4-markets.png", "region": "AP", "field": "MARKETS",
     "headline": "AI SELL-OFF HITS ASIA",
     "summary": "HANG SENG -1.8% AT 19-MONTH LOW; "
                "THEN WALL ST REBOUNDED.",
     "sources": 3, "srcs": "AP · SCMP · AL JAZEERA",
     "focus_y": 0.35},
]

INDEX = [
    {"place": "CONGRESS", "region": "NA", "field": "POLITICS", "text": "DEMOCRATS WIN AT LEAST 258 SEATS", "note": "LARGEST MAJORITY SINCE 1992", "sources": 3, "srcs": "SCMP · ET · ONETURN"},
    {"place": "LIBYA", "region": "AF", "field": "WAR", "text": "UKRAINE SINKS WARSHIP", "sources": 3, "srcs": "STRAITS TIMES · JAPAN TIMES · PRAGATIVADI"},
    {"place": "INDIA", "region": "AP", "field": "HEALTH", "text": "TO TEST ALL BOTTLED WATER", "sources": 2, "srcs": "STRAITS TIMES · ARCHIPELAGO EXPAT"},
    {"place": "SUDAN", "region": "AF", "field": "WAR", "text": "DRONES HIT HOMES, UN HQ", "sources": 2, "srcs": "JAPAN TIMES · ONETURN"},
    {"place": "BRAZIL", "region": "SA", "field": "WEATHER", "text": "STORM TOLL RISES TO 5", "sources": 3, "srcs": "CNA · QNA · FMT"},
    {"place": "MOTOGP", "region": "EU", "field": "SPORT", "text": "MARQUEZ SEALS 8TH TITLE", "sources": 2, "srcs": "AL JAZEERA · RTHK"},
    {"place": "CONGO", "region": "AF", "field": "HEALTH", "text": "EBOLA RESPONSE DISRUPTED", "sources": 2, "srcs": "ONETURN · DAILY DEBRIEF"},
    {"place": "BELGIUM", "region": "EU", "field": "LABOUR", "text": "AIRPORTS SHUT BY STRIKE", "sources": 2, "srcs": "ONETURN · DAILY DEBRIEF"},
]

ALL_STORIES = [MAIN_HERO] + SECONDARY + INDEX

DATE_LINE = "MONDAY 23 NOVEMBER 2026"
LOCK_LINE = ("STORY LOCK 10:10 JST TUE 24 NOV · LATEST EVENT: "
             "WALL ST CLOSE 16:00 ET MON")
DATE_CHECK = ("DATE CHECK: WALL ST FRI ROUT · NIKKEI -5% FRI · FRANCE SAT "
              "PROTESTS · APEC 18-20 NOV · BOLSONARO ICU · "
              "BEPICOLOMBO ORBIT 21 NOV")

MARGIN = 20
DATE_UNIT = 5.8
MAIN_Y, MAIN_H = 110, 336
MAIN_IMG_W = 380
MAIN_TX = MARGIN + MAIN_IMG_W + 18
MAIN_TW = SIZE - MARGIN - MAIN_TX
MAIN_HEAD_UNIT, MAIN_HEAD_STEP = 4.4, 52
MAIN_SRC2 = 1.0
MAIN_SUM2, MAIN_SUM_STEP = 1.25, 21
MAIN_DET2, MAIN_DET_STEP = 1.0, 19
SEC_Y, SEC_H, SEC_W = 458, 248, 237
SEC_GAP = 12
SEC_IMG_H = 86
SEC_TX = 12
SEC_TW = SEC_W - 2 * SEC_TX
SEC_HEAD_UNIT, SEC_HEAD_STEP = 2.0, 22
SEC_SRC2_UNITS = (0.8, 0.76, 0.72, 0.68)
SEC_SUM2, SEC_SUM_STEP = 0.95, 16
IDX_Y0 = 722
IDX_HEAD2 = 1.45
IDX_HEAD_STEP = 20
IDX_SRC2 = 0.82
IDX_NOTE2 = 0.95
NOTE_COLOUR = (178, 186, 200)
STRIP_W = 485
LEGEND2 = 0.82
LEGEND_GAP = 18
LEGEND_Y = 922
COUNTS_Y = 942
COUNTS_UNIT = 1.9
LOCK_Y = 966
DATECHECK_Y = 984

# ----------------------------------------------------------------- layout

def region_counts():
    counts = {}
    for story in ALL_STORIES:
        counts[story["region"]] = counts.get(story["region"], 0) + 1
    return counts


def counts_line():
    fields = {s["field"] for s in ALL_STORIES}
    return "%d STORIES · %d FIELDS" % (len(ALL_STORIES), len(fields))


def legend_items():
    counts = region_counts()
    return [(key, "%s %d" % (REGIONS[key][0], counts[key]))
            for key in REGION_ORDER if key in counts]


def legend_width():
    items = legend_items()
    total = sum(11 + 6 + text_width2(label, LEGEND2)
                for _, label in items)
    return total + LEGEND_GAP * (len(items) - 1)


def fit_unit(text, units, max_width):
    for unit in units:
        if text_width(text, unit) <= max_width:
            return unit
    return units[-1]


def draw_chip(cv, x, y, region, field, unit, chip_h):
    label, colour, dark, _ = REGIONS[region]
    chip_w = text_width(label, unit) + 16
    cv.rect(x, y, chip_w, chip_h, colour)
    chip_text_colour = INK if region == "AF" else WHITE
    cv.text(x + 8, y + (chip_h - 9 * unit) / 2.0, label, unit,
            chip_text_colour)
    if field:
        cv.text(x + chip_w + 10, y + (chip_h - 9 * unit) / 2.0, field,
                unit, dark)
    return chip_w


def masthead_title():
    return "THE DAY IN %d STORIES" % len(ALL_STORIES)


def draw_header(cv):
    cv.text(MARGIN, 14, masthead_title(), 2.0, GOLD)
    cv.text(MARGIN, 38, DATE_LINE, DATE_UNIT, WHITE)
    seg_w = (SIZE - 2 * MARGIN) / len(REGION_ORDER)
    for i, key in enumerate(REGION_ORDER):
        cv.rect(MARGIN + i * seg_w, 96, seg_w, 5, REGIONS[key][1])


def main_head_lines():
    return wrap_text(MAIN_HERO["headline"], MAIN_HEAD_UNIT, MAIN_TW)


def main_sum_lines():
    return wrap_text2(MAIN_HERO["summary"], MAIN_SUM2, MAIN_TW)


def main_det_lines():
    return wrap_text2(MAIN_HERO["detail"], MAIN_DET2, MAIN_TW)


def draw_main(cv, hero, assets):
    _, colour, dark, _ = REGIONS[hero["region"]]
    cv.rect(MARGIN, MAIN_Y, SIZE - 2 * MARGIN, MAIN_H, PANEL)
    img_w, img_h, img_rgb = assets[hero["img"]]
    cv.blit_cover(img_rgb, img_w, img_h, MARGIN, MAIN_Y,
                  MAIN_IMG_W, MAIN_H, focus_x=0.25)
    cv.rect(MARGIN, MAIN_Y, SIZE - 2 * MARGIN, 7, colour)
    draw_chip(cv, MAIN_TX, MAIN_Y + 18, hero["region"], hero["field"],
              1.55, 26)
    hy = MAIN_Y + 58
    lines = main_head_lines()
    for i, line in enumerate(lines):
        cv.text(MAIN_TX, hy + i * MAIN_HEAD_STEP, line,
                MAIN_HEAD_UNIT, INK)
    src_y = hy + len(lines) * MAIN_HEAD_STEP + 10
    cv.text2(MAIN_TX, src_y, hero["srcs"], MAIN_SRC2, dark)
    sy = src_y + S2_BOX * MAIN_SRC2 + 10
    slines = main_sum_lines()
    for i, line in enumerate(slines):
        cv.text2(MAIN_TX, sy + i * MAIN_SUM_STEP, line, MAIN_SUM2,
                 SUMMARY_INK)
    dy = sy + len(slines) * MAIN_SUM_STEP + 14
    cv.rect(MAIN_TX, dy, MAIN_TW, 2, (198, 190, 172))
    for i, line in enumerate(main_det_lines()):
        cv.text2(MAIN_TX, dy + 10 + i * MAIN_DET_STEP, line,
                 MAIN_DET2, SUMMARY_INK)


def sec_head_lines(hero):
    return wrap_text(hero["headline"], SEC_HEAD_UNIT, SEC_TW)


def sec_sum_lines(hero):
    return wrap_text2(hero["summary"], SEC_SUM2, SEC_TW)


def sec_src_unit(hero):
    return fit_unit2(hero["srcs"], SEC_SRC2_UNITS, SEC_TW)


def draw_secondary(cv, hero, x, assets):
    _, colour, dark, _ = REGIONS[hero["region"]]
    cv.rect(x, SEC_Y, SEC_W, SEC_H, PANEL)
    img_w, img_h, img_rgb = assets[hero["img"]]
    cv.blit_cover(img_rgb, img_w, img_h, x, SEC_Y, SEC_W, SEC_IMG_H,
                  focus_y=hero.get("focus_y", 0.5))
    cv.rect(x, SEC_Y, SEC_W, 6, colour)
    tx = x + SEC_TX
    draw_chip(cv, tx, SEC_Y + SEC_IMG_H + 8, hero["region"],
              hero["field"], 1.15, 18)
    hy = SEC_Y + SEC_IMG_H + 26
    lines = sec_head_lines(hero)
    for i, line in enumerate(lines):
        cv.text(tx, hy + i * SEC_HEAD_STEP, line, SEC_HEAD_UNIT, INK)
    src_y = hy + len(lines) * SEC_HEAD_STEP + 6
    src_unit = sec_src_unit(hero)
    cv.text2(tx, src_y, hero["srcs"], src_unit, dark)
    sy = src_y + S2_BOX * src_unit + 5
    for i, line in enumerate(sec_sum_lines(hero)):
        cv.text2(tx, sy + i * SEC_SUM_STEP, line, SEC_SUM2,
                 SUMMARY_INK)


def index_columns():
    half = (len(INDEX) + 1) // 2
    return [INDEX[:half], INDEX[half:]]


def index_item_lines(item):
    return wrap_text2(item["place"] + ": " + item["text"],
                      IDX_HEAD2, STRIP_W - 20)


def index_note_h(item):
    return S2_CAP * IDX_NOTE2 + 3.5 if item.get("note") else 0.0


def index_row_h(item):
    return len(index_item_lines(item)) * IDX_HEAD_STEP + 3.5 \
        + index_note_h(item) + S2_BOX * IDX_SRC2 + 5


def index_bottom():
    bottom = IDX_Y0
    for col_items in index_columns():
        y = IDX_Y0
        for item in col_items:
            y += index_row_h(item)
        bottom = max(bottom, y - 5)
    return bottom


def draw_index(cv):
    cv.rect(MARGIN, IDX_Y0 - 8, SIZE - 2 * MARGIN, 2, (43, 56, 79))
    for c, col_items in enumerate(index_columns()):
        x = MARGIN + c * (STRIP_W + 14)
        y = IDX_Y0
        for item in col_items:
            colour = REGIONS[item["region"]][1]
            cv.rect(x, y + 3, 11, 11, colour)
            lines = index_item_lines(item)
            place = item["place"] + ":"
            for i, line in enumerate(lines):
                ly = y + i * IDX_HEAD_STEP
                if i == 0:
                    end = cv.text2(x + 20, ly, place, IDX_HEAD2,
                                   colour)
                    rest = line[len(place):]
                    if rest:
                        cv.text2(end, ly, rest, IDX_HEAD2, OFFWHITE)
                else:
                    cv.text2(x + 20, ly, line, IDX_HEAD2, OFFWHITE)
            sub_y = y + len(lines) * IDX_HEAD_STEP + 3.5
            if item.get("note"):
                cv.text2(x + 20, sub_y, item["note"], IDX_NOTE2,
                         NOTE_COLOUR)
                sub_y += S2_CAP * IDX_NOTE2 + 3.5
            cv.text2(x + 20, sub_y, item["srcs"], IDX_SRC2, MUTED)
            y += index_row_h(item)


def draw_legend(cv, y):
    x = (SIZE - legend_width()) / 2.0
    for key, label in legend_items():
        cv.rect(x, y + 1, 11, 11, REGIONS[key][1])
        cv.text2(x + 17, y + (13 - S2_BOX * LEGEND2) / 2.0, label,
                 LEGEND2, MUTED)
        x += 11 + 6 + text_width2(label, LEGEND2) + LEGEND_GAP


def text2_centred(cv, cx, y, text, unit, colour):
    cv.text2(cx - text_width2(text, unit) / 2.0, y, text, unit, colour)


def draw_footer(cv):
    draw_legend(cv, LEGEND_Y)
    cv.text_centred(SIZE / 2, COUNTS_Y, counts_line(), COUNTS_UNIT,
                    OFFWHITE)
    unit2 = fit_unit2(LOCK_LINE, (0.95, 0.9, 0.85), SIZE - 2 * MARGIN)
    text2_centred(cv, SIZE / 2, LOCK_Y, LOCK_LINE, unit2, MUTED)
    unit3 = fit_unit2(DATE_CHECK, (0.95, 0.9, 0.85, 0.8),
                      SIZE - 2 * MARGIN)
    text2_centred(cv, SIZE / 2, DATECHECK_Y, DATE_CHECK, unit3, MUTED)


def render():
    here = os.path.dirname(os.path.abspath(__file__))
    assets = {}
    for hero in [MAIN_HERO] + SECONDARY:
        assets[hero["img"]] = png_decode(
            os.path.join(here, "assets", hero["img"]))
    cv = Canvas(BG)
    draw_header(cv)
    draw_main(cv, MAIN_HERO, assets)
    for i, hero in enumerate(SECONDARY):
        draw_secondary(cv, hero, MARGIN + i * (SEC_W + SEC_GAP), assets)
    draw_index(cv)
    draw_footer(cv)
    small = downscale(bytes(cv.fb), RW, SS)
    return png_encode(SIZE, SIZE, small)

# -------------------------------------------------------------------- test

def run_tests():
    failures = []

    def check(name, ok, detail=""):
        print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failures.append(name)

    check("structure 1+4+8", len(SECONDARY) == 4 and len(INDEX) == 8
          and len(ALL_STORIES) == 13,
          "total=%d" % len(ALL_STORIES))
    check("all stories dual-sourced",
          all(s["sources"] >= 2 for s in ALL_STORIES))
    check("source names printed for every story",
          all(s.get("srcs") for s in ALL_STORIES))
    check("source name count == source count",
          all(len(s["srcs"].split(" · ")) == s["sources"]
              for s in ALL_STORIES),
          "; ".join("%s=%d/%d" % (s.get("place", s["field"]),
                    len(s["srcs"].split(" · ")), s["sources"])
                    for s in ALL_STORIES))
    check("asia story present", region_counts().get("AP", 0) >= 1,
          str(region_counts()))
    check("asia promoted to secondary",
          any(s["region"] == "AP" for s in SECONDARY))
    check("health story present",
          any(s["field"] == "HEALTH" for s in ALL_STORIES))
    check("war/security <= 4 of 13",
          sum(1 for s in ALL_STORIES
              if s["field"] in ("WAR", "CONFLICT", "DEFENCE")) <= 4,
          str([s["field"] for s in ALL_STORIES]))
    check("democrats figure as sourced (at least 258, no 258+)",
          any("AT LEAST 258" in s.get("text", "") for s in INDEX)
          and all("258+" not in s.get("text", "") for s in INDEX))
    check("no despair wording in main detail",
          "DESPAIR" not in MAIN_HERO["detail"])
    check("every secondary has a real illustration",
          all(s.get("img") for s in SECONDARY)
          and len({s["img"] for s in SECONDARY}) == len(SECONDARY))
    for s in [MAIN_HERO] + SECONDARY:
        check("headline <=7 words: %s" % s["img"],
              len(s["headline"].split()) <= 7, s["headline"])
    check("no unverifiable superlative",
          "LONGEST" not in MAIN_HERO["summary"]
          and "LONGEST" not in MAIN_HERO["headline"])
    check("kyiv card carries dymer facts only",
          "DYMER" in SECONDARY[0]["summary"]
          and "APARTMENT" in SECONDARY[0]["summary"])
    check("no region-wide 15 anywhere in image text",
          all("15 DEAD" not in (s.get("summary", "") + s.get("detail", "")
                                + s.get("text", ""))
              for s in ALL_STORIES))
    check("nvidia headline market-led, return explained in summary",
          "BEST DAY" in SECONDARY[2]["headline"]
          and "NVIDIA CEO JENSEN HUANG BACK 11 DAYS AFTER RESIGNING"
          in SECONDARY[2]["summary"])
    _rank = {"REUTERS": 100, "AP": 100, "WSJ": 95, "SCMP": 90,
             "AL JAZEERA": 88, "JAPAN TIMES": 85, "STRAITS TIMES": 85,
             "XINHUA": 85, "UKRINFORM": 82, "GULF NEWS": 80, "CNA": 80,
             "RTHK": 78, "ET": 70, "INVESTOPEDIA": 70,
             "QATAR TRIBUNE": 65, "QNA": 65, "JUST SECURITY": 60,
             "FMT": 55, "BREITBART": 45, "PRAGATIVADI": 40,
             "ONETURN": 20, "DAILY DEBRIEF": 15, "BOTA SOT": 15,
             "ARCHIPELAGO EXPAT": 15}

    def _ordered(srcs):
        ranks = [_rank.get(name, 0) for name in srcs.split(" · ")]
        return ranks == sorted(ranks, reverse=True)

    check("sources printed strongest-first",
          all(_ordered(s["srcs"]) for s in ALL_STORIES),
          "; ".join(s["srcs"] for s in ALL_STORIES
                    if not _ordered(s["srcs"])))
    check("masthead title counts the stories, no pictures promise",
          masthead_title() == "THE DAY IN %d STORIES" % len(ALL_STORIES)
          and "PICTURES" not in masthead_title(), masthead_title())
    _body = "".join(s.get("summary", "") + s.get("detail", "")
                    + s.get("text", "") + s.get("srcs", "")
                    + s.get("note", "") for s in ALL_STORIES)
    _missing = sorted({ch for ch in normalise(_body)
                       if ch not in _STROKES})
    check("stroke face covers every body character", not _missing,
          "".join(_missing))
    check("market numbers kept, nvidia +31% dropped",
          "S&P +4.7%" in SECONDARY[2]["summary"]
          and "NASDAQ +6.5%" in SECONDARY[2]["summary"]
          and all("+31%" not in (s.get("summary", "")
                                 + s.get("detail", "")
                                 + s.get("text", ""))
                  for s in ALL_STORIES))
    check("markets connected (asia fell, wall st rebounded)",
          "REBOUNDED" in SECONDARY[3]["summary"])
    check("proper nouns explained in main detail",
          "AL JABER" not in MAIN_HERO["detail"]
          and "PRESIDENT WALKS OUT" in MAIN_HERO["detail"]
          and "130 PARTIES" in MAIN_HERO["detail"])
    check("apac breadth (AP>=2, NA==2, health stories >=2)",
          region_counts().get("AP", 0) >= 2
          and region_counts().get("NA", 0) == 2
          and sum(1 for s in ALL_STORIES
                  if s["field"] == "HEALTH") >= 2,
          str(region_counts()))
    check("india water in index, mexico out",
          any(s.get("place") == "INDIA" and s["region"] == "AP"
              for s in INDEX)
          and all(s.get("place") != "MEXICO" for s in INDEX))
    check("democrats context note (largest since 1992)",
          any(s.get("note") == "LARGEST MAJORITY SINCE 1992"
              for s in INDEX))
    check("index set in stroke face with real cap height",
          IDX_HEAD2 * S2_CAP >= 13.0,
          "cap=%.1fpx" % (IDX_HEAD2 * S2_CAP))
    check("date line exact", DATE_LINE == "MONDAY 23 NOVEMBER 2026")
    check("date line fits", text_width(DATE_LINE, DATE_UNIT)
          <= SIZE - 2 * MARGIN,
          "%.0fpx" % text_width(DATE_LINE, DATE_UNIT))
    lines = main_head_lines()
    check("main headline <=3 lines", len(lines) <= 3, " -> ".join(lines))
    slines = main_sum_lines()
    check("main summary <=3 lines", len(slines) <= 3,
          "%d lines" % len(slines))
    dlines = main_det_lines()
    src_y = 58 + len(lines) * MAIN_HEAD_STEP + 10
    sum_y = src_y + S2_BOX * MAIN_SRC2 + 10
    dy = sum_y + len(slines) * MAIN_SUM_STEP + 14
    det_bottom = dy + 10 + (len(dlines) - 1) * MAIN_DET_STEP \
        + (S2_CAP + 1) * MAIN_DET2
    check("main card fits", len(dlines) <= 2 and det_bottom <= MAIN_H - 4,
          "detail lines=%d bottom=%.0f of %d"
          % (len(dlines), det_bottom, MAIN_H))
    check("main srcs fit",
          text_width2(MAIN_HERO["srcs"], MAIN_SRC2) <= MAIN_TW,
          MAIN_HERO["srcs"])
    for hero in SECONDARY:
        hl = sec_head_lines(hero)
        check("sec headline <=2 lines: %s" % hero["img"], len(hl) <= 2,
              " -> ".join(hl))
        sl = sec_sum_lines(hero)
        src_y = SEC_IMG_H + 26 + len(hl) * SEC_HEAD_STEP + 6
        sy = src_y + S2_BOX * sec_src_unit(hero) + 5
        bottom = sy + (len(sl) - 1) * SEC_SUM_STEP \
            + (S2_CAP + 1) * SEC_SUM2
        check("sec card fits: %s" % hero["img"],
              len(sl) <= 4 and bottom <= SEC_H - 4,
              "summary lines=%d bottom=%.0f of %d"
              % (len(sl), bottom, SEC_H))
        check("sec srcs fit: %s" % hero["img"],
              text_width2(hero["srcs"], SEC_SRC2_UNITS[-1]) <= SEC_TW,
              hero["srcs"])
    for item in INDEX:
        ilines = index_item_lines(item)
        check("index headline <=2 lines: %s" % item["place"],
              len(ilines) <= 2, " -> ".join(ilines))
        check("index lines fit: %s" % item["place"],
              all(text_width2(l, IDX_HEAD2) <= STRIP_W - 20
                  for l in ilines))
        w2 = text_width2(item["srcs"], IDX_SRC2)
        check("index srcs fit: %s" % item["place"], w2 <= STRIP_W - 20,
              "%.0fpx" % w2)
        if item.get("note"):
            w3 = text_width2(item["note"], IDX_NOTE2)
            check("index note fits: %s" % item["place"],
                  w3 <= STRIP_W - 20, "%.0fpx" % w3)
    check("index ends above footer", index_bottom() <= LEGEND_Y - 4,
          "bottom=%.0f" % index_bottom())
    check("legend fits", legend_width() <= SIZE - 2 * MARGIN,
          "%.0fpx" % legend_width())
    check("counts line fits",
          text_width(counts_line(), COUNTS_UNIT) <= SIZE - 2 * MARGIN,
          counts_line())
    check("lock line fits",
          text_width2(LOCK_LINE, 0.85) <= SIZE - 2 * MARGIN, LOCK_LINE)
    check("date check names >=5 exclusions", DATE_CHECK.count("·") >= 5,
          DATE_CHECK)
    check("date check fits",
          text_width2(DATE_CHECK, 0.8) <= SIZE - 2 * MARGIN,
          "%.0fpx" % text_width2(DATE_CHECK, 0.8))
    here = os.path.dirname(os.path.abspath(__file__))
    w, h, rgb = png_decode(os.path.join(here, "assets", MAIN_HERO["img"]))
    check("main asset large", w >= 900 and h >= 900, "%dx%d" % (w, h))
    import hashlib
    check("main asset decode hash (Paeth regression)",
          hashlib.sha256(rgb).hexdigest()
          == "33bba31b026228d0755ffb48772d1314fab47259daf8642c39f17ef7474d7539")
    for hero in SECONDARY:
        path = os.path.join(here, "assets", hero["img"])
        w2, h2, _ = png_decode(path)
        check("asset decodes: %s" % hero["img"], w2 > 0 and h2 > 0,
              "%dx%d" % (w2, h2))
    png = render()
    w3, h3 = struct.unpack(">II", png[16:24])
    check("output is 1024x1024", (w3, h3) == (1024, 1024),
          "%dx%d" % (w3, h3))
    check("output <= 1 MiB", len(png) <= 1048576, "%d bytes" % len(png))
    check("deterministic", render() == png)
    print("counts:", region_counts())
    if failures:
        print("TESTS FAILED:", failures)
        return 1
    print("ALL TESTS PASS")
    return 0


def main(argv):
    if "--test" in argv:
        return run_tests()
    png = render()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
