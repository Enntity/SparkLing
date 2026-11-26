#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Draw first-request prefill rate and time to first token from SparkModelBench results.

    prefill_chart.py OUT.png "LABEL=result.json" ["LABEL=result.json" ...]

Each result.json is a SparkModelBench summary; the chart shows the median of
the first (cold) request at each measured depth. Needs matplotlib.
"""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORS = ["#0b6e75", "#c2571a", "#5b5f97"]
INK, MUTED, GRID = "#16242f", "#4b5b66", "#e3e7ea"


def series(path):
    lanes = json.load(open(path))["lanes"]["prefill"]
    rows = sorted((int(d), r["cold"]) for d, r in lanes.items() if "skip" not in r)
    return [d for d, _ in rows], [r["tokens_s"] for _, r in rows], [r["ttft_s"] for _, r in rows]


def label_k(depth):
    return f"{depth // 1024}K"


def main(out, *specs):
    data = [(spec.split("=", 1)[0], series(spec.split("=", 1)[1])) for spec in specs]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 6.8), sharex=True)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.79, bottom=0.17, hspace=0.42)
    fig.text(0.045, 0.94, "Ling prefill across context lengths", fontsize=21, weight="bold", color=INK)
    fig.text(0.047, 0.895, "One DGX Spark   ·   RigMark 1.3.0 by Alex Ellis, OpenFaaS Ltd",
             fontsize=11, color=MUTED)
    for ax, title, key, fmt in ((top, "Effective prefill (tokens/s)", 1, "{:,.0f}"),
                                (bottom, "Time to first token (seconds)", 2, "{:.1f}")):
        ax.set_title(title, loc="left", fontsize=13, weight="bold", pad=12)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", color=GRID)
        ax.tick_params(colors=MUTED, length=0)
        for i, (name, s) in enumerate(data):
            xs, ys = s[0], s[key]
            ax.plot(xs, ys, color=COLORS[i], lw=2.4, marker="o", ms=7, mfc="white", mew=2, label=name)
            for x, y in zip(xs, ys):
                top_here = all(y >= other[key][other[0].index(x)] for _, other in data if x in other[0])
                ax.annotate(fmt.format(y), (x, y), textcoords="offset points",
                            xytext=(0, 10 if top_here else -18), ha="center", fontsize=9.5,
                            weight="bold", color=COLORS[i])
    depths = sorted({d for _, s in data for d in s[0]})
    bottom.set_xscale("log", base=2)
    bottom.set_xticks(depths, [label_k(d) for d in depths])
    bottom.set_xlabel("Prompt length (tokens, log₂ scale)", fontsize=11)
    top.margins(y=0.35)
    bottom.margins(y=0.3)
    top.legend(loc="lower left", frameon=False, fontsize=10)
    fig.text(0.047, 0.055, "Medians of three first requests per depth. Each prompt carries a fresh random salt; "
             "SparkLing reported zero cached tokens.", fontsize=9.5, color=MUTED)
    fig.text(0.047, 0.025, "Depths beyond a model's window, with its eight-token output reserve, are not run.",
             fontsize=9.5, color=MUTED)
    fig.savefig(out, dpi=160)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
