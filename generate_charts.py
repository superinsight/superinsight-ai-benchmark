#!/usr/bin/env python3
"""
Generate benchmark charts from golden_benchmark_aggregated.json.

Usage:
    python generate_charts.py
    python generate_charts.py --input golden_outputs/golden_benchmark_aggregated.json --output charts/
"""

import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import seaborn as sns

GOLDEN_NAMES = ["golden_a", "golden_b", "golden_c", "golden_d", "golden_e", "golden_f"]
GOLDEN_LABELS = {
    "golden_a": "Golden A\n(DDE)",
    "golden_b": "Golden B\n(Clinical)",
    "golden_c": "Golden C\n(Mixed)",
    "golden_d": "Golden D\n(Large Doc)",
    "golden_e": "Golden E\n(High Noise)",
    "golden_f": "Golden F\n(OCR Degraded)",
}
DATASET_COLORS = {
    "golden_a": "#4285F4",
    "golden_b": "#34A853",
    "golden_c": "#EA4335",
    "golden_d": "#FBBC04",
    "golden_e": "#9B59B6",
    "golden_f": "#00B4D8",
}

MODEL_SHORT = {
    "claude-opus-4.6": "Claude\nOpus 4.6",
    "claude-opus-4.5": "Claude\nOpus 4.5",
    "gemini-3-flash": "Gemini\n3 Flash",
    "gemini-2.5-flash": "Gemini\n2.5 Flash",
    "gemini-2.5-pro": "Gemini\n2.5 Pro",
    "gemini-3.1-pro": "Gemini\n3.1 Pro",
    "qwen3-235b": "Qwen3\n235B",
    "gpt-5.4": "GPT\n5.4",
    "gpt-5.4-pro": "GPT\n5.4 Pro",
    "gpt-5.4-mini": "GPT\n5.4 Mini",
    "minimax-m2.5": "MiniMax\nM2.5",
}

PALETTE = {
    "claude-opus-4.6": "#6B4C9A",
    "claude-opus-4.5": "#9B7FC4",
    "gemini-3-flash": "#0F9D58",
    "gemini-2.5-flash": "#34A853",
    "gemini-2.5-pro": "#4285F4",
    "gemini-3.1-pro": "#1A73E8",
    "qwen3-235b": "#EA4335",
    "gpt-5.4": "#202124",
    "gpt-5.4-pro": "#555555",
    "gpt-5.4-mini": "#888888",
    "minimax-m2.5": "#00B4D8",
}


_FALLBACK_COLORS = [
    "#E67E22", "#16A085", "#8E44AD", "#2980B9", "#C0392B",
    "#27AE60", "#D35400", "#7F8C8D", "#2C3E50", "#F39C12",
]


def _auto_short_name(model_id: str) -> str:
    """Generate a 2-line short display name from a model id."""
    parts = model_id.replace("_", "-").split("-")
    if len(parts) >= 2:
        return parts[0].capitalize() + "\n" + "-".join(parts[1:])
    return model_id


def _ensure_model_maps(models: list):
    """Add fallback entries to MODEL_SHORT and PALETTE for any unknown models."""
    color_idx = 0
    for m in models:
        if m not in MODEL_SHORT:
            MODEL_SHORT[m] = _auto_short_name(m)
        if m not in PALETTE:
            PALETTE[m] = _FALLBACK_COLORS[color_idx % len(_FALLBACK_COLORS)]
            color_idx += 1


def load_data(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def get_sorted_models(data: dict) -> list:
    """Sort models by average F1 descending across all active golden datasets."""
    model_avg = {}
    all_models = set()
    active_gn = [gn for gn in GOLDEN_NAMES if gn in data]
    for gn in active_gn:
        all_models.update(data[gn].keys())
    for model in all_models:
        f1s = []
        for gn in active_gn:
            r = data.get(gn, {}).get(model)
            if r:
                f1s.append(r.get("f1", 0))
        model_avg[model] = sum(f1s) / len(f1s) if f1s else 0
    return sorted(model_avg.keys(), key=lambda m: -model_avg[m])


def chart_overall_f1(data: dict, models: list, out_dir: str):
    """Chart 0: Horizontal bar — Overall AVG F1 ranking."""
    fig, ax = plt.subplots(figsize=(10, 5))

    avgs = []
    colors = []
    labels = []
    for m in reversed(models):
        f1s = [data.get(gn, {}).get(m, {}).get("f1", 0) for gn in GOLDEN_NAMES]
        avg = sum(f1s) / len(f1s) if f1s else 0
        avgs.append(avg * 100)
        colors.append(PALETTE.get(m, "#888888"))
        labels.append(MODEL_SHORT.get(m, m))

    bars = ax.barh(range(len(models)), avgs, color=colors, height=0.6, edgecolor="white", linewidth=0.5)

    for bar, val in zip(bars, avgs):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=10, fontweight="bold")

    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(90, 102)
    ax.set_xlabel("Average F1 Score (%)", fontsize=11)
    ax.set_title("Overall F1 Ranking (3-Round Average)", fontsize=14, fontweight="bold", pad=15)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "0_overall_f1_ranking.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 0_overall_f1_ranking.png")


def chart_per_dataset_f1(data: dict, models: list, out_dir: str):
    """Chart 1: Grouped bar — F1 per dataset per model."""
    fig, ax = plt.subplots(figsize=(14, 6))

    active_gn = [gn for gn in GOLDEN_NAMES if gn in data]
    x = np.arange(len(models))
    n = len(active_gn)
    width = 0.8 / max(n, 1)

    for i, gn in enumerate(active_gn):
        vals = []
        errs = []
        for m in models:
            r = data.get(gn, {}).get(m, {})
            vals.append(r.get("f1", 0) * 100)
            errs.append(r.get("f1_std", 0) * 100)
        offset = (i - n / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, yerr=errs,
                      label=GOLDEN_LABELS.get(gn, gn).replace("\n", " "),
                      color=DATASET_COLORS.get(gn, "#888"), alpha=0.85,
                      capsize=3, error_kw={"linewidth": 1})

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT.get(m, m) for m in models], fontsize=8.5)
    ax.set_ylim(80, 105)
    ax.set_ylabel("F1 Score (%)", fontsize=11)
    ax.set_title("F1 Score by Dataset (mean ± std, 3 rounds)", fontsize=14, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(loc="lower left", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "1_f1_per_dataset.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 1_f1_per_dataset.png")


def chart_precision_recall_scatter(data: dict, models: list, out_dir: str):
    """Chart 2: Scatter — Precision vs Recall on golden_c."""
    fig, ax = plt.subplots(figsize=(8, 6))

    label_offsets = {
        "claude-opus-4.6": (8, 10),
        "gemini-3-flash": (8, -2),
        "gemini-2.5-flash": (8, -14),
        "gemini-2.5-pro": (-75, -14),
        "gemini-3.1-pro": (-75, 8),
        "qwen3-235b": (-55, 10),
        "gpt-5.4": (8, -12),
    }

    for m in models:
        r = data.get("golden_c", {}).get(m, {})
        prec = r.get("precision", 0) * 100
        rec = r.get("recall", 0) * 100
        prec_std = r.get("precision_std", 0) * 100
        rec_std = r.get("recall_std", 0) * 100
        color = PALETTE.get(m, "#888888")

        ax.errorbar(rec, prec, xerr=rec_std, yerr=prec_std,
                     fmt="o", markersize=10, color=color,
                     capsize=4, capthick=1.5, linewidth=1.5, zorder=5)
        offset = label_offsets.get(m, (8, 6))
        ax.annotate(m, (rec, prec), textcoords="offset points",
                    xytext=offset, fontsize=7.5, color=color, fontweight="bold")

    ax.set_xlim(70, 105)
    ax.set_ylim(78, 105)
    ax.set_xlabel("Recall (%)", fontsize=12)
    ax.set_ylabel("Precision (%)", fontsize=12)
    ax.set_title("Precision vs Recall — Golden C (Mixed)", fontsize=14, fontweight="bold", pad=15)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

    ax.axhline(y=100, color="#ccc", linestyle="--", linewidth=0.8)
    ax.axvline(x=100, color="#ccc", linestyle="--", linewidth=0.8)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "2_precision_recall_scatter.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 2_precision_recall_scatter.png")


def chart_stability_heatmap(data: dict, models: list, out_dir: str):
    """Chart 3: Heatmap — F1 std deviation across datasets."""
    fig, ax = plt.subplots(figsize=(7, 5))

    matrix = []
    ylabels = []
    for m in models:
        row = []
        for gn in GOLDEN_NAMES:
            r = data.get(gn, {}).get(m, {})
            row.append(r.get("f1_std", 0) * 100)
        matrix.append(row)
        ylabels.append(m)

    matrix = np.array(matrix)

    sns.heatmap(matrix, annot=True, fmt=".1f", cmap="YlOrRd",
                xticklabels=[GOLDEN_LABELS[gn].replace("\n", " ") for gn in GOLDEN_NAMES],
                yticklabels=ylabels,
                linewidths=0.5, linecolor="white",
                cbar_kws={"label": "F1 Std Dev (%)", "shrink": 0.8},
                vmin=0, vmax=15,
                ax=ax)

    ax.set_title("Multi-Round Stability (F1 Std Dev %)", fontsize=13, fontweight="bold", pad=15)
    ax.tick_params(axis="y", rotation=0)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "3_stability_heatmap.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 3_stability_heatmap.png")


def chart_tp_fn_breakdown(data: dict, models: list, out_dir: str):
    """Chart 4: Stacked bar — TP / May / FP / FN for golden_c."""
    fig, ax = plt.subplots(figsize=(10, 5))

    tp_vals, may_vals, fp_vals, fn_vals = [], [], [], []
    for m in models:
        r = data.get("golden_c", {}).get(m, {})
        tp_vals.append(r.get("true_positives", 0))
        may_vals.append(r.get("may_extract_matched", 0))
        fp_vals.append(r.get("false_positives", 0))
        fn_vals.append(r.get("false_negatives", 0))

    x = np.arange(len(models))
    w = 0.55

    ax.bar(x, tp_vals, w, label="True Positives", color="#34A853")
    ax.bar(x, may_vals, w, bottom=tp_vals, label="May Extract Matched", color="#A8DAB5")
    bottom2 = [t + m for t, m in zip(tp_vals, may_vals)]
    ax.bar(x, fp_vals, w, bottom=bottom2, label="False Positives", color="#EA4335")
    bottom3 = [b + f for b, f in zip(bottom2, fp_vals)]
    ax.bar(x, fn_vals, w, bottom=bottom3, label="False Negatives", color="#FBBC04")

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT.get(m, m) for m in models], fontsize=8.5)
    ax.set_ylabel("Number of Entries", fontsize=11)
    ax.set_title("Extraction Breakdown — Golden C (Mixed)", fontsize=14, fontweight="bold", pad=15)
    ax.legend(loc="upper right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "4_tp_fn_breakdown.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 4_tp_fn_breakdown.png")


def chart_formatting_chrono(det_data: dict, models: list, out_dir: str):
    """Chart 5: Grouped bar — Formatting & Chronological scores per dataset."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    active_gn = [gn for gn in GOLDEN_NAMES if gn in det_data]

    for ax_idx, (metric, title) in enumerate([
        ("formatting_score", "Formatting Score"),
        ("chronological_score", "Chronological Order Score"),
    ]):
        ax = axes[ax_idx]
        x = np.arange(len(models))
        n = len(active_gn)
        width = 0.8 / max(n, 1)

        for i, gn in enumerate(active_gn):
            vals = []
            errs = []
            for m in models:
                r = det_data.get(gn, {}).get(m, {})
                vals.append(r.get(metric, 0) * 100)
                errs.append(r.get(f"{metric}_std", 0) * 100)
            offset = (i - n / 2 + 0.5) * width
            ax.bar(x + offset, vals, width, yerr=errs,
                   label=GOLDEN_LABELS.get(gn, gn).replace("\n", " "),
                   color=DATASET_COLORS.get(gn, "#888"), alpha=0.85,
                   capsize=3, error_kw={"linewidth": 1})

        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_SHORT.get(m, m) for m in models], fontsize=7.5)
        ymin = 75 if metric == "chronological_score" else 95
        ax.set_ylim(ymin, 102)
        ax.set_ylabel("Score (%)", fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.3)
        if ax_idx == 0:
            ax.legend(loc="lower left", fontsize=8)

    fig.suptitle("Deterministic Quality Scores (3-Round Average)", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "5_formatting_chrono.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 5_formatting_chrono.png")


def chart_content_fidelity(det_data: dict, models: list, out_dir: str):
    """Chart 6: Grouped bar — ROUGE-L F1 (content fidelity) per dataset."""
    fig, ax = plt.subplots(figsize=(14, 6))

    active_gn = [gn for gn in GOLDEN_NAMES if gn in det_data]
    x = np.arange(len(models))
    n = len(active_gn)
    width = 0.8 / max(n, 1)

    for i, gn in enumerate(active_gn):
        vals = []
        errs = []
        for m in models:
            r = det_data.get(gn, {}).get(m, {})
            vals.append(r.get("avg_rouge_l_f1", 0) * 100)
            errs.append(r.get("avg_rouge_l_f1_std", 0) * 100)
        offset = (i - n / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, yerr=errs,
               label=GOLDEN_LABELS.get(gn, gn).replace("\n", " "),
               color=DATASET_COLORS.get(gn, "#888"), alpha=0.85,
               capsize=3, error_kw={"linewidth": 1})

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT.get(m, m) for m in models], fontsize=8.5)
    ax.set_ylim(0, 75)
    ax.set_ylabel("ROUGE-L F1 (%)", fontsize=11)
    ax.set_title("Content Fidelity — ROUGE-L F1 vs Golden Key Fields (3-Round Avg)",
                 fontsize=13, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(loc="upper right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "6_content_fidelity.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 6_content_fidelity.png")


def chart_per_field_heatmap(det_data: dict, models: list, out_dir: str):
    """Chart 7: Heatmap — Per-field ROUGE-L F1 on golden_c."""
    all_fields = set()
    for m in models:
        r = det_data.get("golden_c", {}).get(m, {})
        all_fields.update(r.get("per_field_rouge_l", {}).keys())
    fields = sorted(all_fields)
    if not fields:
        return

    field_labels = {
        "subjective": "Subjective/\nHPI",
        "objective": "Objective/\nPE",
        "social": "Social",
        "lab_results": "Labs",
        "procedures": "Procedures",
        "imaging_findings": "Imaging",
        "diagnoses": "Diagnoses",
        "plan": "Plan",
        "mss": "MSS",
        "medications": "Medications",
        "referrals": "Referrals",
    }

    fig, ax = plt.subplots(figsize=(12, 5.5))

    matrix = []
    for m in models:
        r = det_data.get("golden_c", {}).get(m, {})
        pf = r.get("per_field_rouge_l", {})
        row = [pf.get(f, 0) * 100 for f in fields]
        matrix.append(row)

    matrix = np.array(matrix)

    sns.heatmap(matrix, annot=True, fmt=".0f", cmap="YlGn",
                xticklabels=[field_labels.get(f, f) for f in fields],
                yticklabels=models,
                linewidths=0.5, linecolor="white",
                cbar_kws={"label": "ROUGE-L F1 (%)", "shrink": 0.8},
                vmin=0, vmax=100,
                ax=ax)

    ax.set_title("Per-Field Content Fidelity — Golden C (Mixed)", fontsize=13, fontweight="bold", pad=15)
    ax.tick_params(axis="y", rotation=0)
    ax.tick_params(axis="x", rotation=0)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "7_per_field_heatmap.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 7_per_field_heatmap.png")


def chart_semantic_fidelity(det_data: dict, models: list, out_dir: str):
    """Chart 8: Grouped bar — Semantic Fidelity (embedding cosine similarity) per dataset."""
    fig, ax = plt.subplots(figsize=(14, 6))
    x = range(len(models))
    golden_names = [gn for gn in GOLDEN_NAMES if gn in det_data]
    n = len(golden_names)
    width = 0.8 / max(n, 1)

    for i, gn in enumerate(golden_names):
        vals = []
        for m in models:
            v = det_data.get(gn, {}).get(m, {}).get("avg_semantic_similarity", 0) * 100
            vals.append(v)
        offset = (i - n / 2 + 0.5) * width
        ax.bar([xi + offset for xi in x], vals, width, label=gn,
               color=DATASET_COLORS.get(gn, "#999"), edgecolor="white", linewidth=0.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels([MODEL_SHORT.get(m, m) for m in models], fontsize=8.5)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Semantic Similarity (%)", fontsize=11)
    ax.set_title("Semantic Fidelity — Embedding Cosine Similarity vs Golden Key Fields",
                 fontsize=13, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(loc="lower right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "8_semantic_fidelity.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 8_semantic_fidelity.png")


def chart_hallucination(halluc_data: dict, models: list, out_dir: str):
    """Chart 9: Grouped bar — Hallucination Score per dataset (multi-judge)."""
    fig, ax = plt.subplots(figsize=(14, 6))
    x = range(len(models))
    golden_names = [gn for gn in GOLDEN_NAMES if gn in halluc_data]
    n = len(golden_names)
    width = 0.8 / max(n, 1)

    for i, gn in enumerate(golden_names):
        vals = []
        errs = []
        for m in models:
            md = halluc_data.get(gn, {}).get(m, {})
            v = md.get("score", md.get("hallucination_score", 0)) * 100
            e = md.get("score_std", md.get("hallucination_score_std", 0)) * 100
            vals.append(v)
            errs.append(e)
        offset = (i - n / 2 + 0.5) * width
        ax.bar([xi + offset for xi in x], vals, width, yerr=errs,
               label=gn, color=DATASET_COLORS.get(gn, "#999"),
               edgecolor="white", linewidth=0.5, capsize=3)

    ax.set_xticks(list(x))
    ax.set_xticklabels([MODEL_SHORT.get(m, m) for m in models], fontsize=8.5)
    ax.set_ylim(50, 105)
    ax.set_ylabel("Hallucination Score (% supported)", fontsize=11)
    ax.set_title("Hallucination Score — 3-Judge Panel, Majority Vote (higher = fewer hallucinations)",
                 fontsize=12, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(loc="lower left", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "9_hallucination_score.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  -> 9_hallucination_score.png")


def chart_radar(golden_data, det_data, halluc_data, models, out_dir):
    """Radar chart showing multi-dimensional model profiles."""
    dimensions = ["F1", "Semantic\nFidelity", "Halluc-Free\nRate", "Formatting", "Chronological", "ROUGE-L"]
    n_dims = len(dimensions)
    angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)

    top_models = models[:6]
    for model in top_models:
        vals = []
        f1s = [golden_data.get(gn, {}).get(model, {}).get("f1", 0) for gn in GOLDEN_NAMES if gn in golden_data]
        vals.append(np.mean(f1s) if f1s else 0)

        sems = [det_data.get(gn, {}).get(model, {}).get("avg_semantic_similarity", 0) for gn in GOLDEN_NAMES if gn in det_data]
        vals.append(np.mean(sems) if sems else 0)

        halluc_scores = []
        for gn in GOLDEN_NAMES:
            h = halluc_data.get(gn, {}).get(model, {})
            if isinstance(h, dict) and "score" in h:
                halluc_scores.append(h["score"])
        vals.append(np.mean(halluc_scores) if halluc_scores else 0)

        fmts = [det_data.get(gn, {}).get(model, {}).get("formatting_score", 0) for gn in GOLDEN_NAMES if gn in det_data]
        vals.append(np.mean(fmts) if fmts else 0)

        chrons = [det_data.get(gn, {}).get(model, {}).get("chronological_score", 0) for gn in GOLDEN_NAMES if gn in det_data]
        vals.append(np.mean(chrons) if chrons else 0)

        rouges = [det_data.get(gn, {}).get(model, {}).get("avg_rouge_l_f1", 0) for gn in GOLDEN_NAMES if gn in det_data]
        vals.append(np.mean(rouges) if rouges else 0)

        vals += vals[:1]
        color = PALETTE.get(model, "#999999")
        short = MODEL_SHORT.get(model, model).replace("\n", " ")
        ax.plot(angles, vals, 'o-', linewidth=2, label=short, color=color)
        ax.fill(angles, vals, alpha=0.08, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, size=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"], size=8)
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=9)
    ax.set_title("Multi-Dimensional Model Profile (Top 6)", size=14, pad=30)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "10_radar_chart.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  -> 10_radar_chart.png")


def chart_pareto(golden_data, latency_data, models, out_dir):
    """Pareto frontier: F1 vs Latency."""
    if not latency_data:
        print("  [skip] No latency data for Pareto chart")
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    points = []
    for model in models:
        f1s = [golden_data.get(gn, {}).get(model, {}).get("f1", 0) for gn in GOLDEN_NAMES if gn in golden_data]
        avg_f1 = np.mean(f1s) if f1s else 0
        latency = latency_data.get(model, {}).get("latency_seconds", {}).get("mean", 0)
        if latency > 0 and avg_f1 > 0:
            points.append((model, latency, avg_f1))

    if not points:
        print("  [skip] No valid data for Pareto chart")
        plt.close(fig)
        return

    points.sort(key=lambda p: p[1])
    pareto = []
    max_f1 = -1
    for name, lat, f1 in sorted(points, key=lambda p: p[1]):
        if f1 > max_f1:
            pareto.append((name, lat, f1))
            max_f1 = f1

    for model, lat, f1 in points:
        color = PALETTE.get(model, "#999999")
        short = MODEL_SHORT.get(model, model).replace("\n", " ")
        ax.scatter(lat, f1, s=150, c=color, zorder=5, edgecolors="white", linewidth=1.5)
        ax.annotate(short, (lat, f1), textcoords="offset points",
                    xytext=(8, 8), fontsize=8, color=color, fontweight="bold")

    if len(pareto) > 1:
        pareto_lats = [p[1] for p in pareto]
        pareto_f1s = [p[2] for p in pareto]
        ax.plot(pareto_lats, pareto_f1s, '--', color='#E74C3C', linewidth=2,
                alpha=0.7, label='Pareto Frontier', zorder=3)

    ax.set_xlabel("Average Latency (seconds)", fontsize=12)
    ax.set_ylabel("Average F1 Score", fontsize=12)
    ax.set_title("Quality vs Latency — Pareto Frontier", fontsize=14)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "11_pareto_frontier.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  -> 11_pareto_frontier.png")


def chart_significance_heatmap(bootstrap_path: str, models: list, out_dir: str):
    """Pairwise statistical significance heatmap from bootstrap results."""
    if not os.path.isfile(bootstrap_path):
        print(f"  [skip] {bootstrap_path} not found — run evaluate_bootstrap.py first")
        return

    with open(bootstrap_path) as f:
        boot = json.load(f)

    model_order = [m for m in models if m in boot.get("model_summary", {})]
    n = len(model_order)
    if n < 2:
        print("  [skip] Not enough models for significance heatmap")
        return

    idx = {m: i for i, m in enumerate(model_order)}
    pval_matrix = np.ones((n, n))
    for test in boot.get("pairwise_tests", []):
        a, b = test.get("model_a"), test.get("model_b")
        p = test.get("p_value")
        if a in idx and b in idx and p is not None:
            pval_matrix[idx[a], idx[b]] = p
            pval_matrix[idx[b], idx[a]] = p

    sig_matrix = np.where(pval_matrix < 0.05, 1, 0)
    np.fill_diagonal(sig_matrix, 0.5)

    short = [MODEL_SHORT.get(m, m).replace("\n", " ") for m in model_order]

    fig, ax = plt.subplots(figsize=(10, 8))
    cmap = sns.color_palette(["#ffffff", "#e8f0fe", "#1a73e8"], as_cmap=True)
    sns.heatmap(
        sig_matrix, ax=ax, cmap=cmap, vmin=0, vmax=1,
        xticklabels=short, yticklabels=short,
        linewidths=0.5, linecolor="#e0e0e0",
        cbar=False, square=True,
    )

    for i in range(n):
        for j in range(n):
            if i != j:
                p = pval_matrix[i, j]
                txt = f"{p:.3f}" if p >= 0.001 else "<.001"
                color = "white" if p < 0.05 else "#5f6368"
                ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center",
                        fontsize=7, color=color, fontweight="bold" if p < 0.05 else "normal")

    ax.set_title("Pairwise Statistical Significance (p-values)\nBlue = significant (p<0.05)", fontsize=13)
    ax.tick_params(axis="both", labelsize=9)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "12_significance_heatmap.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  -> 12_significance_heatmap.png")


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark charts")
    parser.add_argument("--input", "-i", default="golden_outputs/golden_benchmark_aggregated.json")
    parser.add_argument("--det-input", default="golden_outputs/deterministic_results.json",
                        help="Deterministic evaluation results JSON")
    parser.add_argument("--halluc-input", default="golden_outputs/hallucination_results.json",
                        help="Hallucination evaluation results JSON")
    parser.add_argument("--cost-input", default="golden_outputs/cost_latency_report.json",
                        help="Cost/latency report JSON")
    parser.add_argument("--output", "-o", default="charts")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    data = load_data(args.input)
    models = get_sorted_models(data)
    _ensure_model_maps(models)

    print(f"Generating charts from {args.input}")
    print(f"Models: {models}")
    print(f"Output: {args.output}/\n")

    chart_overall_f1(data, models, args.output)
    chart_per_dataset_f1(data, models, args.output)
    chart_precision_recall_scatter(data, models, args.output)
    chart_stability_heatmap(data, models, args.output)
    chart_tp_fn_breakdown(data, models, args.output)

    total = 5
    det_data = None
    if os.path.isfile(args.det_input):
        det_data = load_data(args.det_input)
        chart_formatting_chrono(det_data, models, args.output)
        chart_content_fidelity(det_data, models, args.output)
        chart_per_field_heatmap(det_data, models, args.output)
        total += 3

        has_semantic = any(
            "avg_semantic_similarity" in m_data
            for gn_data in det_data.values()
            for m_data in gn_data.values()
        )
        if has_semantic:
            chart_semantic_fidelity(det_data, models, args.output)
            total += 1
    else:
        print(f"  [skip] {args.det_input} not found — run evaluate_deterministic.py first")

    halluc_data = None
    if os.path.isfile(args.halluc_input):
        halluc_data = load_data(args.halluc_input)
        chart_hallucination(halluc_data, models, args.output)
        total += 1
    else:
        print(f"  [skip] {args.halluc_input} not found — run evaluate_hallucination.py first")

    cost_data = None
    if os.path.isfile(args.cost_input):
        cost_data = load_data(args.cost_input)

    if det_data and halluc_data:
        chart_radar(data, det_data, halluc_data, models, args.output)
        total += 1

    chart_pareto(data, cost_data, models, args.output)
    total += 1

    bootstrap_path = os.path.join(os.path.dirname(args.input), "bootstrap_results.json")
    chart_significance_heatmap(bootstrap_path, models, args.output)
    total += 1

    print(f"\nDone! {total} charts saved to {args.output}/")


if __name__ == "__main__":
    main()
