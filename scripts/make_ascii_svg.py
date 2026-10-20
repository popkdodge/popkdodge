"""Turn source-prepped.png into an animated terminal-style ASCII portrait SVG.
Light ink on a dark terminal, so bright = dense; only the near-pure-white background prints blank.

Usage: python make_ascii_svg.py [input.png] [output.svg]
Env:   COLS (default 180), STATIC=1 for the finished frame without animation.
"""
import html
import os
import sys
import xml.dom.minidom
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "source-prepped.png"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / "peter-ascii.svg"
STATIC = os.environ.get("STATIC") == "1"

RAMP = " .`:-=+*cs#%@"  # sparse -> dense; dense = bright ink on the dark terminal
GAMMA = 1.0
WHITE_FLOOR = 0.988  # raw luminance at or above this (>= 252/255) is background and prints blank
CONTRAST = 1.15
SWEEP_S = 6.0  # whole portrait prints in this long

W, H = 840, 880
TITLE_H, STATUS_H = 30, 40
ART_X, ART_W = 20, 800
ART_TOP, ART_BOTTOM = TITLE_H + 10, H - STATUS_H
FG, BG, BORDER, DIM = "#c9d1d9", "#0d1117", "#30363d", "#8b949e"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

COLS = int(os.environ.get("COLS", 180))
ROWS = round(COLS * 8 / 15)
CW = ART_W / COLS
CH = min(CW * 15 / 8, (ART_BOTTOM - ART_TOP) / ROWS)  # shrink rows if they would not fit
Y0 = ART_TOP + ((ART_BOTTOM - ART_TOP) - ROWS * CH) / 2


def ascii_rows():
    img = Image.open(SRC).convert("L")
    # Crop to the art area's aspect (full width, from just above the head) so LANCZOS does not squash the face.
    target_h = round(img.width * (ROWS * CH) / ART_W)
    g = np.asarray(img)
    top = int(np.argmax((g < 250).any(axis=1)))  # first row with subject on it
    top = max(0, min(top - img.height // 50, img.height - target_h))
    img = img.crop((0, top, img.width, top + target_h))
    # Background share per cell from the full-res pixels; LANCZOS ringing darkens pure-background cells near the edge.
    bg = np.asarray(img.point(lambda p: 255 if p >= WHITE_FLOOR * 255 else 0).resize((COLS, ROWS), Image.BOX)) / 255
    img = img.resize((COLS, ROWS), Image.LANCZOS)
    raw = np.asarray(img, dtype=np.float32) / 255
    v = np.clip((raw - 0.5) * CONTRAST + 0.5, 0, 1) ** GAMMA
    idx = np.rint(v * (len(RAMP) - 1)).clip(1, len(RAMP) - 1).astype(int)  # subject never prints blank
    idx[bg >= 0.5] = 0
    return ["".join(RAMP[i] for i in row) for row in idx]


def svg(rows):
    fs = CW / 0.6  # monospace advance is ~0.6em
    step = SWEEP_S / ROWS
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
        f'<line x1="0.5" y1="{TITLE_H}" x2="{W - 0.5}" y2="{TITLE_H}" stroke="{BORDER}"/>',
        *(f'<circle cx="{20 + 20 * i}" cy="15" r="6" fill="{c}"/>'
          for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f"))),
        f'<text x="{W / 2}" y="19.5" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{DIM}">'
        "peter@github: ~$ ./portrait.sh</text>",
    ]
    if not STATIC:
        out.append("<defs>")
        for i in range(ROWS):
            out.append(
                f'<clipPath id="r{i}"><rect x="{ART_X}" y="{Y0 + i * CH:.2f}" width="0" height="{CH:.2f}">'
                f'<animate attributeName="width" from="0" to="{ART_W}" begin="{i * step:.3f}s" '
                f'dur="{step:.3f}s" fill="freeze"/></rect></clipPath>'
            )
        out.append("</defs>")
    out.append(f'<g font-family="{FONT}" font-size="{fs:.2f}" fill="{FG}">')
    for i, row in enumerate(rows):
        t = (f'<text x="{ART_X}" y="{Y0 + (i + 0.8) * CH:.2f}" xml:space="preserve" textLength="{ART_W}" '
             f'lengthAdjust="spacing">{html.escape(row)}</text>')
        out.append(t if STATIC else f'<g clip-path="url(#r{i})">{t}</g>')
    out.append("</g>")
    if not STATIC:
        # One cursor rides the wipe edge: x sweeps once per row, y steps down a row each sweep.
        ys = ";".join(f"{Y0 + i * CH:.2f}" for i in range(ROWS))
        out.append(
            f'<rect x="{ART_X}" y="{Y0:.2f}" width="{CW:.2f}" height="{CH:.2f}" fill="{FG}" opacity="0">'
            f'<set attributeName="opacity" to="1" begin="0s"/>'
            f'<set attributeName="opacity" to="0" begin="{SWEEP_S}s"/>'
            f'<animate attributeName="x" from="{ART_X}" to="{ART_X + ART_W}" begin="0s" dur="{step:.3f}s" '
            f'repeatCount="{ROWS}"/>'
            f'<animate attributeName="y" values="{ys}" calcMode="discrete" begin="0s" dur="{SWEEP_S}s"/></rect>'
        )
    prompt = "peter@github:~$ whoami Peter Kongjareon"
    sy = H - STATUS_H / 2 + 5
    blink = ("" if STATIC else
             '<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1s" repeatCount="indefinite"/>')
    out += [
        # textLength pins the prompt to 8.4px/char so the cursor lands one space after it in any font
        f'<text x="{ART_X}" y="{sy}" font-family="{FONT}" font-size="14" fill="{FG}" xml:space="preserve" '
        f'textLength="{len(prompt) * 8.4:.1f}" lengthAdjust="spacing">{html.escape(prompt)}</text>',
        f'<rect x="{ART_X + (len(prompt) + 1) * 8.4:.1f}" y="{sy - 12}" width="8" height="15" fill="{FG}">{blink}</rect>',
        "</svg>",
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    doc = svg(ascii_rows())
    root = xml.dom.minidom.parseString(doc).documentElement  # self-check: well-formed, right size
    assert (root.getAttribute("width"), root.getAttribute("height")) == (str(W), str(H))
    assert "<script" not in doc and len(doc.encode()) < 400_000
    OUT.write_text(doc)
    print(f"wrote {OUT} ({len(doc.encode()) / 1024:.1f} KB, {COLS}x{ROWS}, static={STATIC})")
