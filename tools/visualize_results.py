#!/usr/bin/env python3
"""
Generate benchmark visualization charts from comparison results.

Usage:
    python visualize_results.py

Outputs PNG files to ./charts/ directory.
"""

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.size"] = 11

RESULTS_DIR = Path(__file__).parent / "outputs"
CHARTS_DIR = Path(__file__).parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

SOURCES = {
    "Source A\n(DDE, 126K)": "mc_source_a_small_v2/comparison_config_results.json",
    "Source B\n(MH, 139K)": "mc_source_b_small_v2/comparison_config_results.json",
    "Source C\n(Psych, 97K)": "mc_source_c_small_v2/comparison_config_results.json",
}

MODEL_ORDER = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-3-flash",
    "gemini-3.1-pro",
    "qwen3-235b",
]

MODEL_COLORS = {
    "gemini-2.5-pro": "#4285F4",
    "gemini-2.5-flash": "#34A853",
    "gemini-3-flash": "#FBBC04",
    "gemini-3.1-pro": "#EA4335",
    "qwen3-235b": "#9E9E9E",
}

MODEL_SHORT = {
    "gemini-2.5-pro": "2.5-Pro",
    "gemini-2.5-flash": "2.5-Flash",
    "gemini-3-flash": "3-Flash",
    "gemini-3.1-pro": "3.1-Pro",
    "qwen3-235b": "Qwen3-235B",
}


def load_all_results():
    """Load results from all source comparison JSONs."""
    all_data = {}
    for label, rel_path in SOURCES.items():
        path = RESULTS_DIR / rel_path
        if not path.exists():
            print(f"  SKIP: {path} not found")
            continue
        with open(path) as f:
            data = json.load(f)
        models_map = {m["name"]: m for m in data["models"]}
        all_data[label] = {
            "models": models_map,
            "pairwise": data.get("pairwise", {}),
        }
    return all_data


def chart_extraction_accuracy(all_data):
    """Grouped bar chart: Extraction Accuracy per source per model."""
    src_labels = list(all_data.keys())
    n_sources = len(src_labels)
    n_models = len(MODEL_ORDER)
    x = np.arange(n_sources)
    width = 0.15

    fig, ax = plt.subplots(figsize=(12, 5.5))

    for i, model in enumerate(MODEL_ORDER):
        vals = []
        for src in src_labels:
            m = all_data[src]["models"].get(model, {})
            acc = m.get("accuracy", {}).get("average_score", 0)
            vals.append(acc * 100)
        offset = (i - n_models / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=MODEL_SHORT[model],
                      color=MODEL_COLORS[model], edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{val:.0f}%" if val == 100 else f"{val:.1f}%",
                    ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_ylabel("Extraction Accuracy (%)")
    ax.set_title("Extraction Accuracy by Source Document (LLM Judge)", fontsize=14, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(src_labels, fontsize=10)
    ax.set_ylim(70, 106)
    ax.axhline(y=100, color="green", linestyle="--", alpha=0.2, linewidth=1)
    ax.legend(loc="lower left", framealpha=0.9, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    out = CHARTS_DIR / "1_extraction_accuracy.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


def chart_date_coverage(all_data):
    """Grouped bar chart: Date Coverage per source per model."""
    src_labels = list(all_data.keys())
    n_sources = len(src_labels)
    n_models = len(MODEL_ORDER)
    x = np.arange(n_sources)
    width = 0.15

    fig, ax = plt.subplots(figsize=(12, 5.5))

    for i, model in enumerate(MODEL_ORDER):
        vals = []
        for src in src_labels:
            m = all_data[src]["models"].get(model, {})
            dc = m.get("scores", {}).get("date_coverage", 0)
            vals.append(dc * 100)
        offset = (i - n_models / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=MODEL_SHORT[model],
                      color=MODEL_COLORS[model], edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_ylabel("Date Coverage (%)")
    ax.set_title("Date Coverage by Source Document (Missed Extraction Indicator)", fontsize=14, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(src_labels, fontsize=10)
    ax.set_ylim(30, 110)
    ax.axhline(y=100, color="green", linestyle="--", alpha=0.2, linewidth=1)
    ax.legend(loc="lower left", framealpha=0.9, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    out = CHARTS_DIR / "2_date_coverage.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


def chart_pairwise_wins(all_data):
    """Stacked horizontal bar: Pairwise win counts across all sources."""
    src_labels = list(all_data.keys())
    wins_per_source = {m: [] for m in MODEL_ORDER}

    for src in src_labels:
        pw = all_data[src].get("pairwise", {})
        wc = pw.get("win_counts", {})
        for model in MODEL_ORDER:
            wins_per_source[model].append(wc.get(model, 0))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    y = np.arange(len(MODEL_ORDER))
    left = np.zeros(len(MODEL_ORDER))

    src_hatches = ["", "//", ".."]
    src_short = ["Src A", "Src B", "Src C"]

    for s_idx, src in enumerate(src_labels):
        vals = [wins_per_source[m][s_idx] for m in MODEL_ORDER]
        bars = ax.barh(y, vals, left=left, height=0.6,
                       color=[MODEL_COLORS[m] for m in MODEL_ORDER],
                       edgecolor="white", linewidth=0.8,
                       hatch=src_hatches[s_idx], alpha=0.85)
        left += vals

    totals = [sum(wins_per_source[m]) for m in MODEL_ORDER]
    max_total = max(totals) if totals else 1
    for i, (model, total) in enumerate(zip(MODEL_ORDER, totals)):
        pct = total / (4 * len(src_labels)) * 100
        ax.text(total + 0.15, i, f"{total}/12 ({pct:.0f}%)",
                va="center", fontsize=10, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([MODEL_SHORT[m] for m in MODEL_ORDER], fontsize=11)
    ax.set_xlabel("Pairwise Wins (across 3 sources)")
    ax.set_title("Pairwise Win Count (LLM Judge)", fontsize=14, pad=15)
    ax.set_xlim(0, max_total + 2.5)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor="gray", hatch=h, alpha=0.5, label=s)
                       for h, s in zip(src_hatches, src_short)]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    plt.tight_layout()
    out = CHARTS_DIR / "3_pairwise_wins.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


def chart_scatter_accuracy_vs_coverage(all_data):
    """Scatter plot: avg Accuracy (Y) vs avg Date Coverage (X) per model."""
    fig, ax = plt.subplots(figsize=(8, 6))

    src_labels = list(all_data.keys())

    for model in MODEL_ORDER:
        acc_vals = []
        dc_vals = []
        for src in src_labels:
            m = all_data[src]["models"].get(model, {})
            acc_vals.append(m.get("accuracy", {}).get("average_score", 0) * 100)
            dc_vals.append(m.get("scores", {}).get("date_coverage", 0) * 100)
        avg_acc = np.mean(acc_vals)
        avg_dc = np.mean(dc_vals)

        ax.scatter(avg_dc, avg_acc, s=250, c=MODEL_COLORS[model],
                   edgecolors="black", linewidth=1, zorder=5)
        ax.annotate(MODEL_SHORT[model],
                    (avg_dc, avg_acc),
                    textcoords="offset points", xytext=(10, -5),
                    fontsize=10, fontweight="bold")

        for i, src in enumerate(src_labels):
            ax.scatter(dc_vals[i], acc_vals[i], s=40, c=MODEL_COLORS[model],
                       alpha=0.35, zorder=3)

    ax.set_xlabel("Avg Date Coverage (%)", fontsize=12)
    ax.set_ylabel("Avg Extraction Accuracy (%)", fontsize=12)
    ax.set_title("Accuracy vs Coverage: Model Positioning", fontsize=14, pad=15)
    ax.set_xlim(55, 105)
    ax.set_ylim(85, 102)

    ax.axhline(y=95, color="gray", linestyle=":", alpha=0.3)
    ax.axvline(x=80, color="gray", linestyle=":", alpha=0.3)
    ax.text(102, 95.5, "High Accuracy\nThreshold", fontsize=7, color="gray", ha="right")
    ax.text(81, 86, "High Coverage\nThreshold", fontsize=7, color="gray")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    out = CHARTS_DIR / "4_accuracy_vs_coverage.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


def chart_elo_ratings(all_data):
    """Horizontal bar: average Elo across sources."""
    src_labels = list(all_data.keys())

    avg_elo = {}
    for model in MODEL_ORDER:
        elos = []
        for src in src_labels:
            pw = all_data[src].get("pairwise", {})
            elo_map = pw.get("elo_scores", {})
            elos.append(elo_map.get(model, 1000))
        avg_elo[model] = np.mean(elos)

    sorted_models = sorted(MODEL_ORDER, key=lambda m: avg_elo[m], reverse=True)

    fig, ax = plt.subplots(figsize=(9, 4))
    y = np.arange(len(sorted_models))
    vals = [avg_elo[m] for m in sorted_models]
    colors = [MODEL_COLORS[m] for m in sorted_models]

    bars = ax.barh(y, vals, height=0.55, color=colors, edgecolor="white", linewidth=0.8)

    for i, (bar, val) in enumerate(zip(bars, vals)):
        ax.text(val + 1, i, f"{val:.0f}", va="center", fontsize=11, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([MODEL_SHORT[m] for m in sorted_models], fontsize=11)
    ax.set_xlabel("Average Elo Rating")
    ax.set_title("Average Pairwise Elo Rating (across 3 sources)", fontsize=14, pad=15)
    ax.set_xlim(920, 1075)
    ax.axvline(x=1000, color="gray", linestyle="--", alpha=0.3)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    out = CHARTS_DIR / "5_elo_ratings.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


def chart_summary_table(all_data):
    """Summary table as an image — the 'one slide' overview."""
    src_labels = list(all_data.keys())
    src_short = ["A", "B", "C"]

    rows = []
    for model in MODEL_ORDER:
        acc_vals, dc_vals, elo_vals, win_vals = [], [], [], []
        for src in src_labels:
            m = all_data[src]["models"].get(model, {})
            acc_vals.append(m.get("accuracy", {}).get("average_score", 0))
            dc_vals.append(m.get("scores", {}).get("date_coverage", 0))
            pw = all_data[src].get("pairwise", {})
            elo_vals.append(pw.get("elo_scores", {}).get(model, 1000))
            win_vals.append(pw.get("win_counts", {}).get(model, 0))

        rows.append([
            MODEL_SHORT[model],
            f"{np.mean(acc_vals)*100:.1f}%",
            f"{np.mean(dc_vals)*100:.1f}%",
            f"{sum(win_vals)}/12",
            f"{np.mean(elo_vals):.0f}",
        ])

    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.axis("off")

    col_labels = ["Model", "Avg Accuracy", "Avg DateCov", "Wins", "Avg Elo"]
    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.0, 1.8)

    for j in range(len(col_labels)):
        table[0, j].set_facecolor("#4285F4")
        table[0, j].set_text_props(color="white", fontweight="bold")

    for i, model in enumerate(MODEL_ORDER):
        table[i + 1, 0].set_text_props(fontweight="bold", color=MODEL_COLORS[model])

    # Highlight best in each column
    best_acc = max(range(len(MODEL_ORDER)), key=lambda i: float(rows[i][1].rstrip('%')))
    best_dc = max(range(len(MODEL_ORDER)), key=lambda i: float(rows[i][2].rstrip('%')))
    best_wins = max(range(len(MODEL_ORDER)), key=lambda i: int(rows[i][3].split('/')[0]))
    best_elo = max(range(len(MODEL_ORDER)), key=lambda i: int(rows[i][4]))

    for col_idx, best_idx in [(1, best_acc), (2, best_dc), (3, best_wins), (4, best_elo)]:
        table[best_idx + 1, col_idx].set_facecolor("#E8F5E9")
        table[best_idx + 1, col_idx].set_text_props(fontweight="bold")

    ax.set_title("Medical Chronology Benchmark — Summary\n(3 sources × 5 models, LLM Judge: gemini-2.5-pro)",
                 fontsize=13, pad=20, fontweight="bold")

    plt.tight_layout()
    out = CHARTS_DIR / "0_summary_table.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


def main():
    print("Loading benchmark results...")
    all_data = load_all_results()
    if not all_data:
        print("No results found!")
        return

    print(f"Loaded {len(all_data)} sources, generating charts...\n")

    chart_summary_table(all_data)
    chart_extraction_accuracy(all_data)
    chart_date_coverage(all_data)
    chart_pairwise_wins(all_data)
    chart_scatter_accuracy_vs_coverage(all_data)
    chart_elo_ratings(all_data)

    print(f"\nAll charts saved to: {CHARTS_DIR}/")


if __name__ == "__main__":
    main()
