"""Write ../info-card.svg: an animated neofetch-style info card. STATIC=1 writes the finished frame only."""
import os
import textwrap
from xml.sax.saxutils import escape

W, H = 840, 880
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SIZE = 20
CHAR = SIZE * 0.6  # monospace advance width, about 12px
LINE = 42  # line height
X = 40
KEY_COLS = 12  # "Highlights: " is the widest key
VALUE_COLS = int((W - 2 * X) / CHAR) - KEY_COLS
FG, ACCENT, DIM, GREEN = "#c9d1d9", "#58a6ff", "#7d8590", "#3fb950"
SWATCHES = ["#ff5f56", "#ffbd2e", "#27c93f", "#58a6ff", "#bc8cff", "#39d353", "#f778ba", "#c9d1d9"]
ROWS = [
    ("Name", "Peter (Sasana) Kongjareon"),
    ("Now", "Digital transformation lead, KPB International"),
    ("", "Owner, Midori Rawai Hotel (Phuket)"),
    ("Prev", "Cloud Solution Architect / Data Engineer, Gump's"),
    ("", "San Francisco Bay Area, 2020-2025"),
    ("Stack", "AWS serverless (Lambda, RDS, S3, CloudFront)"),
    ("", "Terraform, Python, PostgreSQL, LINE"),
    ("Highlights", "AWS Certified Solutions Architect"),
    ("", "Cut cloud cost 30%, held 99.5% uptime"),
    ("", "E-commerce shop $60K -> $300K revenue"),
    ("Based", "Bangkok / Phuket, Thailand"),
    ("Languages", "Thai, English"),
    ("Web", "sasana.work"),
]


def text(x, y, s, fill):
    return f'<text x="{x:.1f}" y="{y}" fill="{fill}">{escape(s)}</text>'


def build(static):
    lines = []  # each entry: SVG markup for one body line, or None for a blank line
    head = "peter@popkdodge"
    lines.append(text(X, 0, head, GREEN))
    lines.append(text(X, 0, "-" * len(head), DIM))
    vx = X + KEY_COLS * CHAR
    for key, value in ROWS:
        for i, part in enumerate(textwrap.wrap(value, VALUE_COLS)):
            k = text(X, 0, key + ":", ACCENT) if key and i == 0 else ""
            # wrapped continuation lines are indented two columns past the value column
            lines.append(k + text(vx + (2 * CHAR if i else 0), 0, part, FG))
    lines.append(None)
    lines.append("".join(
        f'<rect x="{X + i * 44}" y="-20" width="32" height="24" rx="5" fill="{c}"/>'
        for i, c in enumerate(SWATCHES)))
    lines.append(None)
    prompt = "peter@github:~$ "
    blink = "" if static else (
        '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
        'dur="1s" repeatCount="indefinite"/>')
    lines.append(text(X, 0, prompt, GREEN)
                 + f'<rect x="{X + len(prompt) * CHAR:.1f}" y="-18" width="{CHAR:.1f}" height="22" fill="{FG}">{blink}</rect>')

    top = 30 + (H - 30 - LINE * (len(lines) - 1)) // 2 + 6  # centre the block below the title bar
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" font-size="{SIZE}">',
        "<title>peter@popkdodge neofetch</title>",
    ]
    if not static:
        out.append(
            "<style>@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}"
            ".l{opacity:0;animation:in .45s ease-out forwards}</style>")
    out += [
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="#0d1117" stroke="#30363d"/>',
        f'<path d="M0.5 30.5H{W - 0.5}" stroke="#30363d"/>',
        '<circle cx="20" cy="15" r="6" fill="#ff5f56"/><circle cx="40" cy="15" r="6" fill="#ffbd2e"/>'
        '<circle cx="60" cy="15" r="6" fill="#27c93f"/>',
        f'<text x="{W / 2}" y="20" fill="{DIM}" font-size="14" text-anchor="middle">peter@github: ~$ neofetch</text>',
    ]
    n = 0
    for i, markup in enumerate(lines):
        if markup is None:
            continue
        y = top + i * LINE
        anim = "" if static else f' class="l" style="animation-delay:{n * 0.12:.2f}s"'
        out.append(f'<g{anim}><g transform="translate(0 {y})">{markup}</g></g>')
        n += 1
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    svg = build(os.environ.get("STATIC") == "1")
    assert "<script" not in svg and len(svg) < 50_000
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "info-card.svg")
    with open(dest, "w") as f:
        f.write(svg)
    print("wrote", os.path.normpath(dest), len(svg), "bytes")
