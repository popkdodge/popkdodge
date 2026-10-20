"""Render data/contributions.json as an animated calendar heatmap SVG (STATIC=1 for no animation)."""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

W = 860
CELL, GAP = 12, 3
STEP = CELL + GAP
TITLE_H = 30
LABEL_W = 30  # weekday label column
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def colour(count):
    for i, top in enumerate((0, 5, 15, 30, 50)):
        if count <= top:
            return PALETTE[i]
    return PALETTE[5]


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def render(data, static=False):
    days = data["days"]
    first = date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # Sunday = row 0; leading empty cells in week one
    cells = [(divmod(i + lead, 7), d) for i, d in enumerate(days)]  # ((col, row), day)
    ncols = cells[-1][0][0] + 1

    grid_w = ncols * STEP - GAP
    x0 = (W - LABEL_W - grid_w) // 2 + LABEL_W  # grid left edge, content centred
    month_y = TITLE_H + 28
    gy = month_y + 10  # grid top
    grid_bottom = gy + 7 * STEP - GAP
    legend_y = grid_bottom + 10  # legend boxes top
    footer_y = legend_y + CELL + 26  # footer baseline
    H = footer_y + 18

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{escape(data["username"])} GitHub contributions heatmap">',
    ]
    if not static:
        out.append(
            "<style>"
            ".c{opacity:0;transform-box:fill-box;animation:drop .42s ease-out;animation-fill-mode:forwards}"
            "@keyframes drop{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}"
            "@media (prefers-reduced-motion: reduce){.c{opacity:1;animation:none}}"
            "</style>"
        )
    out += [
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="#0d1117" stroke="#30363d"/>',
        f'<line x1="1" y1="{TITLE_H}" x2="{W - 1}" y2="{TITLE_H}" stroke="#30363d"/>',
        '<circle cx="20" cy="15" r="6" fill="#ff5f56"/><circle cx="40" cy="15" r="6" fill="#ffbd2e"/>'
        '<circle cx="60" cy="15" r="6" fill="#27c93f"/>',
        f'<text x="{W // 2}" y="19" text-anchor="middle" font-family="{FONT}" font-size="12" fill="#7d8590">'
        "peter@github: ~$ ./contributions.sh</text>",
        f'<g font-family="{FONT}" font-size="10" fill="#7d8590">',
    ]

    # month labels on the first week where the month changes; a label too close to the next one is dropped
    labels = []
    for (col, row), d in cells:
        if not labels or d["date"][:7] != labels[-1][1]:
            labels.append((col, d["date"][:7]))
    for i, (col, m) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - col < 2:
            continue
        out.append(f'<text x="{x0 + col * STEP}" y="{month_y}">{MONTHS[int(m[5:]) - 1]}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{x0 - 6}" y="{gy + row * STEP + 9}" text-anchor="end">{name}</text>')
    out.append("</g>")

    out.append("<g>")
    for (col, row), d in cells:
        attrs = f'x="{x0 + col * STEP}" y="{gy + row * STEP}" width="{CELL}" height="{CELL}" rx="2" fill="{colour(d["count"])}"'
        if static:
            out.append(f"<rect {attrs}><title>{d['date']}: {d['count']}</title></rect>")
        else:
            delay = col * 0.018 + row * 0.045
            out.append(f'<rect class="c" style="animation-delay:{delay:.3f}s" {attrs}>'
                       f"<title>{d['date']}: {d['count']}</title></rect>")
    out.append("</g>")

    # legend, right-aligned under the grid
    right = x0 + grid_w
    lx = right - 30 - len(PALETTE) * STEP
    out.append(f'<g font-family="{FONT}" font-size="10" fill="#7d8590">')
    out.append(f'<text x="{lx - 6}" y="{legend_y + 10}" text-anchor="end">Less</text>')
    for i, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx + i * STEP}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>')
    out.append(f'<text x="{right}" y="{legend_y + 10}" text-anchor="end">More</text></g>')

    # stats footer, left-aligned under the grid
    cur, lon, best = data["current_streak"], data["longest_streak"], data["best_day"]
    total = f"{data['total_contributions']:,}"
    v = lambda s: f'<tspan fill="#c9d1d9">{escape(str(s))}</tspan>'
    footer = (f"{total} contributions in the last year · current streak {plural(cur['length'], 'day')} · "
              f"longest {plural(lon['length'], 'day')} · best day {best['count']} on {best['date']}")
    room = W - x0 - 16
    # shortcut: 0.63em is the widest monospace advance measured (Quick Look); shrink only if the line would hit the frame
    size = min(12, int(room / (len(footer) * 0.63) * 10) / 10)
    out.append(
        f'<text x="{x0}" y="{footer_y}" font-family="{FONT}" font-size="{size:g}" fill="#7d8590">'
        f'{v(total)} contributions in the last year · '
        f'current streak {v(plural(cur["length"], "day"))} · longest {v(plural(lon["length"], "day"))} · '
        f'best day {v(best["count"])} on {v(best["date"])}</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    static = os.environ.get("STATIC") == "1"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    data = json.loads(SRC.read_text())
    out.write_text(render(data, static), encoding="utf-8")
    print(f"wrote {out} ({'static' if static else 'animated'})")


if __name__ == "__main__":
    main()
