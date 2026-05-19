import os
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from trace import (
    PrefetcherHarness,
    generate_sequential,
    generate_strided,
    generate_random,
    generate_mixed,
    generate_looping,
)
from prefetcher_base import NoPrefetcher
from prefetcher_nextline import NextLinePrefetcher
from prefetcher_stride import StridePrefetcher
from prefetcher_stream import GHBPrefetcher


sns.set_theme(style="whitegrid", font_scale=1.15)
PALETTE = sns.color_palette("tab10")

PREFETCHER_COLORS = {
    "No Prefetcher": PALETTE[3],
    "Next-Line":     PALETTE[0],
    "Stride":        PALETTE[1],
    "GHB / Stream":  PALETTE[2],
}

TRACE_MARKERS = {
    "Sequential": "o",
    "Strided":    "s",
    "Mixed":      "D",
    "Random":     "X",
    "Looping":    "^",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def make_prefetchers():
    return {
        "No Prefetcher": NoPrefetcher(),
        "Next-Line":     NextLinePrefetcher(),
        "Stride":        StridePrefetcher(degree=4, confirm_threshold=2),
        "GHB / Stream":  GHBPrefetcher(history_size=256, lookback=3, degree=4),
    }


def make_traces(n):
    return {
        "Sequential": generate_sequential(n),
        "Strided":    generate_strided(n, stride=128),
        "Mixed":      generate_mixed(n),
        "Random":     generate_random(n),
        "Looping":    generate_looping(n, loop_size=16),
    }


def run_experiment(prefetcher, trace, cache_kb=32):
    harness = PrefetcherHarness(cache_size_kb=cache_kb, block_size=64, prefetch_degree=4)
    return harness.run(prefetcher, trace)


def savefig(name):
    path = os.path.join(OUTPUT_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  saved -> {path}")


def exp1_hit_rate_by_trace(n_accesses):
    print("\n[Exp 1] Hit rate by trace type ...")
    traces = make_traces(n_accesses)
    pf_names = list(make_prefetchers().keys())
    trace_names = list(traces.keys())

    results = {p: {} for p in pf_names}
    for trace_name, trace in traces.items():
        pf_dict = make_prefetchers()
        for pf_name, pf in pf_dict.items():
            stats = run_experiment(pf, trace)
            results[pf_name][trace_name] = stats["hit_rate"] * 100

    x = np.arange(len(trace_names))
    width = 0.2
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, pf_name in enumerate(pf_names):
        vals = [results[pf_name][t] for t in trace_names]
        bars = ax.bar(
            x + i * width, vals, width,
            label=pf_name,
            color=PREFETCHER_COLORS[pf_name],
            edgecolor="white", linewidth=0.7
        )
        for bar, v in zip(bars, vals):
            if v > 5:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.8,
                    f"{v:.0f}%", ha="center", va="bottom", fontsize=8
                )

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(trace_names, fontsize=11)
    ax.set_ylabel("Cache Hit Rate (%)")
    ax.set_title("Cache Hit Rate by Trace Type — all prefetchers")
    ax.set_ylim(0, 110)
    ax.legend(title="Prefetcher", loc="upper right")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%g%%'))

    plt.tight_layout()
    savefig("exp1_hit_rate_by_trace.png")


def exp2_metrics_vs_cache_size(n_accesses):
    print("[Exp 2] Metrics vs cache size ...")
    cache_sizes = [8, 16, 32, 64, 128]
    trace = generate_mixed(n_accesses)
    pf_names = list(make_prefetchers().keys())
    metrics = ["hit_rate", "prefetch_accuracy", "prefetch_coverage"]
    labels = {
        "hit_rate":          "Hit Rate (%)",
        "prefetch_accuracy": "Prefetch Accuracy (%)",
        "prefetch_coverage": "Prefetch Coverage (%)",
    }

    results = {m: {p: [] for p in pf_names} for m in metrics}

    for kb in cache_sizes:
        pf_dict = make_prefetchers()
        for pf_name, pf in pf_dict.items():
            stats = run_experiment(pf, trace, cache_kb=kb)
            for m in metrics:
                results[m][pf_name].append(stats[m] * 100)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, metric in zip(axes, metrics):
        for pf_name in pf_names:
            ax.plot(
                cache_sizes,
                results[metric][pf_name],
                marker="o", linewidth=2.2, markersize=7,
                label=pf_name,
                color=PREFETCHER_COLORS[pf_name],
            )
        ax.set_xscale("log", base=2)
        ax.set_xticks(cache_sizes)
        ax.set_xticklabels([f"{kb} KB" for kb in cache_sizes], fontsize=9)
        ax.set_ylabel(labels[metric])
        ax.set_xlabel("Cache Size")
        ax.set_title(labels[metric].split(" (")[0])
        ax.set_ylim(-5, 105)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%g%%'))

    handles, lbls = axes[0].get_legend_handles_labels()
    fig.legend(handles, lbls, title="Prefetcher",
               loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.07))
    fig.suptitle("Prefetcher Metrics vs Cache Size  (Mixed trace, 4-degree)", y=1.02)
    plt.tight_layout()
    savefig("exp2_metrics_vs_cache_size.png")


def exp3_accuracy_vs_coverage(n_accesses):
    print("[Exp 3] Accuracy vs Coverage scatter ...")
    traces = make_traces(n_accesses)
    pf_names = list(make_prefetchers().keys())

    fig, ax = plt.subplots(figsize=(9, 7))

    for pf_name in pf_names:
        xs, ys, trace_labels = [], [], []
        for trace_name, trace in traces.items():
            pf_dict = make_prefetchers()
            stats = run_experiment(pf_dict[pf_name], trace)
            xs.append(stats["prefetch_accuracy"] * 100)
            ys.append(stats["prefetch_coverage"] * 100)
            trace_labels.append(trace_name)

        if pf_name == "No Prefetcher":
            continue

        for x, y, tlabel in zip(xs, ys, trace_labels):
            ax.scatter(
                x, y,
                color=PREFETCHER_COLORS[pf_name],
                marker=TRACE_MARKERS[tlabel],
                s=130, zorder=3,
                edgecolors="white", linewidths=0.8
            )
            ax.annotate(
                f"{pf_name[:4]}/{tlabel[:3]}",
                (x, y), textcoords="offset points",
                xytext=(5, 5), fontsize=7, alpha=0.8
            )

    pf_handles = [
        mpatches.Patch(color=PREFETCHER_COLORS[p], label=p)
        for p in pf_names if p != "No Prefetcher"
    ]
    trace_handles = [
        plt.Line2D([0], [0], marker=m, color="grey", linestyle="None",
                   markersize=9, label=t)
        for t, m in TRACE_MARKERS.items()
    ]

    leg1 = ax.legend(handles=pf_handles, title="Prefetcher",
                     loc="lower right", fontsize=9)
    ax.add_artist(leg1)
    ax.legend(handles=trace_handles, title="Trace type",
              loc="lower left", fontsize=9)

    ax.axvline(50, color="grey", linestyle="--", alpha=0.4, linewidth=1)
    ax.axhline(50, color="grey", linestyle="--", alpha=0.4, linewidth=1)
    ax.set_xlabel("Prefetch Accuracy  (% of issued that were useful)")
    ax.set_ylabel("Prefetch Coverage  (% of misses avoided)")
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_title("Accuracy vs Coverage — all prefetchers x all trace types")
    ax.text(52, 52, "ideal zone", fontsize=8, color="grey", alpha=0.6)

    plt.tight_layout()
    savefig("exp3_accuracy_vs_coverage.png")


def exp4_heatmap(n_accesses):
    print("[Exp 4] Metric heatmaps ...")
    traces = make_traces(n_accesses)
    pf_names = list(make_prefetchers().keys())
    trace_names = list(traces.keys())
    metrics = ["hit_rate", "prefetch_accuracy", "prefetch_coverage"]
    titles  = ["Hit Rate", "Prefetch Accuracy", "Prefetch Coverage"]

    data = {m: np.zeros((len(pf_names), len(trace_names))) for m in metrics}

    for j, (trace_name, trace) in enumerate(traces.items()):
        pf_dict = make_prefetchers()
        for i, pf_name in enumerate(pf_names):
            stats = run_experiment(pf_dict[pf_name], trace)
            for m in metrics:
                data[m][i, j] = round(stats[m] * 100, 1)

    fig, axes = plt.subplots(1, 3, figsize=(17, 4))

    for ax, m, title in zip(axes, metrics, titles):
        sns.heatmap(
            data[m], ax=ax,
            annot=True, fmt=".1f", annot_kws={"size": 10},
            cmap="YlGn", vmin=0, vmax=100,
            xticklabels=trace_names,
            yticklabels=pf_names,
            linewidths=0.5, linecolor="white",
            cbar_kws={"label": "%"},
        )
        ax.set_title(title)
        ax.set_xticklabels(trace_names, rotation=30, ha="right", fontsize=9)
        ax.set_yticklabels(pf_names, rotation=0, fontsize=9)

    fig.suptitle("Prefetcher Performance Summary  (32 KB cache)", y=1.04)
    plt.tight_layout()
    savefig("exp4_heatmap.png")


def exp5_degree_sensitivity(n_accesses):
    print("[Exp 5] Degree sensitivity ...")
    degrees = [1, 2, 3, 4, 6, 8]
    configs = [
        ("Stride / Sequential", lambda d: StridePrefetcher(degree=d), generate_sequential(n_accesses)),
        ("Stride / Mixed",      lambda d: StridePrefetcher(degree=d), generate_mixed(n_accesses)),
        ("GHB / Sequential",    lambda d: GHBPrefetcher(degree=d),    generate_sequential(n_accesses)),
        ("GHB / Mixed",         lambda d: GHBPrefetcher(degree=d),    generate_mixed(n_accesses)),
    ]
    line_styles = ["-", "--", "-.", ":"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for (label, pf_factory, trace), ls in zip(configs, line_styles):
        hit_rates = []
        acc_rates = []
        for d in degrees:
            pf = pf_factory(d)
            stats = run_experiment(pf, trace)
            hit_rates.append(stats["hit_rate"] * 100)
            acc_rates.append(stats["prefetch_accuracy"] * 100)

        color = PREFETCHER_COLORS["Stride"] if label.startswith("Stride") else PREFETCHER_COLORS["GHB / Stream"]
        axes[0].plot(degrees, hit_rates, marker="o", linestyle=ls,
                     color=color, label=label, linewidth=2)
        axes[1].plot(degrees, acc_rates, marker="o", linestyle=ls,
                     color=color, label=label, linewidth=2)

    for ax, ylabel, title in zip(axes,
                                  ["Hit Rate (%)", "Prefetch Accuracy (%)"],
                                  ["Hit Rate vs Prefetch Degree",
                                   "Prefetch Accuracy vs Prefetch Degree"]):
        ax.set_xticks(degrees)
        ax.set_xlabel("Prefetch Degree")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_ylim(-5, 105)
        ax.legend(fontsize=8)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%g%%'))

    fig.suptitle("Prefetch Degree Sensitivity  (32 KB cache)", y=1.02)
    plt.tight_layout()
    savefig("exp5_degree_sensitivity.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    n = 500 if args.quick else 2000
    print(f"Running experiments with {n} accesses per trace ...")

    exp1_hit_rate_by_trace(n)
    exp2_metrics_vs_cache_size(n)
    exp3_accuracy_vs_coverage(n)
    exp4_heatmap(n)
    exp5_degree_sensitivity(n)

    print(f"\nAll plots saved to: {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
