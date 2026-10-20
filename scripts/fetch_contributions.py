"""Scrape the public contribution calendar and write data/contributions.json."""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"


def fetch_days(user):
    resp = requests.get(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (profile-art; +https://github.com/popkdodge)"},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        if not td.get("data-date"):
            continue
        m = re.match(r"\s*([\d,]+) contributions?", tips.get(td.get("id"), ""))
        days.append({
            "date": td["data-date"],
            "count": int(m.group(1).replace(",", "")) if m else 0,  # "No contributions on ..." -> 0
            "level": int(td.get("data-level", 0)),
        })
    return sorted(days, key=lambda d: d["date"])


def streaks(days):
    """Return (current, longest) as {length,start,end}."""
    longest = {"length": 0, "start": None, "end": None}
    run_start, run_len = None, 0
    for d in days:
        if d["count"] > 0:
            run_start = run_start if run_len else d["date"]
            run_len += 1
            if run_len > longest["length"]:
                longest = {"length": run_len, "start": run_start, "end": d["date"]}
        else:
            run_len = 0
    # current streak: walk back from the last day; a zero today does not break it yet
    tail = days[:-1] if days and days[-1]["count"] == 0 else days
    current = {"length": 0, "start": None, "end": None}
    for d in reversed(tail):
        if d["count"] == 0:
            break
        current = {"length": current["length"] + 1, "start": d["date"], "end": current["end"] or d["date"]}
    return current, longest


def main():
    user = os.environ.get("GH_PROFILE_USER", "popkdodge")
    days = fetch_days(user)
    if not days:
        print(f"error: no td.ContributionCalendar-day cells found for {user}; GitHub markup may have changed",
              file=sys.stderr)
        sys.exit(1)
    assert len(days) >= 360, f"expected >= 360 days, got {len(days)}"

    current, longest = streaks(days)
    best = max(days, key=lambda d: d["count"])
    monthly = {}
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]

    data = {
        "username": user,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": sum(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"] > 0),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": [{"month": k, "total": v} for k, v in sorted(monthly.items())],
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"{user}: {data['total_contributions']} contributions, {data['active_days']} active days, "
          f"{len(days)} days {data['range']['start']}..{data['range']['end']}, "
          f"current streak {current['length']}, longest {longest['length']}, "
          f"best {best['count']} on {best['date']} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
