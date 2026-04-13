#!/usr/bin/env python3
"""Generate chart images from JSON data for embedding in Obsidian wiki articles.

Usage:
    echo '{"type": "bar", "title": "Example", "labels": ["A","B"], "values": [10,20]}' | \
        python generate_chart.py --output /path/to/chart.png

Supported chart types: bar, barh, line, pie, scatter
"""

import argparse
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Clean style for Obsidian rendering
COLORS = ["#4a9eff", "#ff6b6b", "#4ecdc4", "#ffa726", "#ab47bc", "#66bb6a", "#ef5350", "#42a5f5"]


def make_bar(data: dict, ax: plt.Axes) -> None:
    labels = data["labels"]
    values = data["values"]
    colors = data.get("colors", COLORS[: len(labels)])
    ax.bar(labels, values, color=colors)
    ax.set_xlabel(data.get("xlabel", ""))
    ax.set_ylabel(data.get("ylabel", ""))


def make_barh(data: dict, ax: plt.Axes) -> None:
    labels = data["labels"]
    values = data["values"]
    colors = data.get("colors", COLORS[: len(labels)])
    ax.barh(labels, values, color=colors)
    ax.set_xlabel(data.get("xlabel", ""))
    ax.set_ylabel(data.get("ylabel", ""))


def make_line(data: dict, ax: plt.Axes) -> None:
    x = data.get("x", list(range(len(data["series"][0]["values"]))))
    for i, series in enumerate(data["series"]):
        color = COLORS[i % len(COLORS)]
        ax.plot(x, series["values"], label=series["label"], color=color, marker="o", linewidth=2)
    ax.set_xlabel(data.get("xlabel", ""))
    ax.set_ylabel(data.get("ylabel", ""))
    ax.legend()


def make_pie(data: dict, ax: plt.Axes) -> None:
    labels = data["labels"]
    values = data["values"]
    colors = data.get("colors", COLORS[: len(labels)])
    ax.pie(values, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")


def make_scatter(data: dict, ax: plt.Axes) -> None:
    for i, series in enumerate(data["series"]):
        color = COLORS[i % len(COLORS)]
        ax.scatter(series["x"], series["y"], label=series["label"], color=color, s=60)
    ax.set_xlabel(data.get("xlabel", ""))
    ax.set_ylabel(data.get("ylabel", ""))
    ax.legend()


CHART_TYPES = {
    "bar": make_bar,
    "barh": make_barh,
    "line": make_line,
    "pie": make_pie,
    "scatter": make_scatter,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate chart images from JSON data")
    parser.add_argument("--output", required=True, help="Output PNG file path")
    parser.add_argument("--width", type=float, default=10, help="Figure width in inches")
    parser.add_argument("--height", type=float, default=6, help="Figure height in inches")
    parser.add_argument("--dpi", type=int, default=150, help="Output resolution")
    args = parser.parse_args()

    data = json.load(sys.stdin)

    chart_type = data.get("type", "bar")
    if chart_type not in CHART_TYPES:
        print(f"Error: unsupported chart type '{chart_type}'. Use: {', '.join(CHART_TYPES)}", file=sys.stderr)
        sys.exit(1)

    fig, ax = plt.subplots(figsize=(args.width, args.height))
    ax.set_title(data.get("title", ""), fontsize=14, fontweight="bold")

    CHART_TYPES[chart_type](data, ax)

    plt.tight_layout()
    fig.savefig(args.output, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Chart saved to {args.output}")


if __name__ == "__main__":
    main()
