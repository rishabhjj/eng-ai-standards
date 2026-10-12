#!/usr/bin/env python3
"""Monthly kit metrics from exported PR data. Stdlib only.

  metrics.py DATA.json [--min-precision 0.7] [--min-votes 10] [--json]

DATA.json is {"prs": [{number, body, labels, changes_requested, findings: [{lens, up, down}]}]},
produced by scripts/export-pr-data.py. The thresholds are placeholders until we have real data.
"""
import argparse
import json
import re
import sys
from collections import defaultdict

AGENT_BOX = re.compile(r"\[[xX]\]\s*Authored or substantially drafted by an AI agent")


def summarize(prs, min_precision=0.7, min_votes=10):
    agent = [p for p in prs if AGENT_BOX.search(p.get("body") or "")]
    human = [p for p in prs if p not in agent]

    def rework(group):
        return sum(1 for p in group if p.get("changes_requested", 0) > 0) / len(group) if group else None

    lenses = defaultdict(lambda: [0, 0])
    for p in prs:
        for f in p.get("findings", []):
            lenses[f["lens"]][0] += f.get("up", 0)
            lenses[f["lens"]][1] += f.get("down", 0)
    precision = {}
    for lens, (up, down) in sorted(lenses.items()):
        votes = up + down
        value = up / votes if votes else None
        if votes < min_votes:
            verdict = "insufficient data"
        else:
            verdict = "keep" if value >= min_precision else "disable or tighten"
        precision[lens] = {"up": up, "down": down, "precision": value, "verdict": verdict}

    breaks = sum(1 for p in prs if "break-glass" in p.get("labels", []))
    return {
        "prs": len(prs),
        "agent_authored": len(agent),
        "agent_share": len(agent) / len(prs) if prs else None,
        "rework_rate_agent": rework(agent),
        "rework_rate_human": rework(human),
        "break_glass": breaks,
        "break_glass_rate": breaks / len(prs) if prs else None,
        "lens_precision": precision,
    }


def pct(value):
    return "n/a" if value is None else f"{value:.0%}"


def render(s):
    lines = [
        f"PRs: {s['prs']}   agent-authored: {s['agent_authored']} ({pct(s['agent_share'])})",
        f"Rework (changes requested): agent {pct(s['rework_rate_agent'])}   human {pct(s['rework_rate_human'])}",
        f"Break-glass: {s['break_glass']} ({pct(s['break_glass_rate'])})",
        "Review precision per lens:",
    ]
    if not s["lens_precision"]:
        lines.append("  no reacted findings yet")
    for lens, v in s["lens_precision"].items():
        lines.append(f"  {lens:14} {pct(v['precision']):>5}  ({v['up']} up, {v['down']} down)  {v['verdict']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--min-precision", type=float, default=0.7)
    ap.add_argument("--min-votes", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    with open(args.data) as f:
        prs = json.load(f)["prs"]
    result = summarize(prs, args.min_precision, args.min_votes)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
