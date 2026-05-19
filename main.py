"""
main.py — Hardware Prefetcher Lab
Computer Architecture & OS — Final Project

Run this to see the full pipeline working:
  python main.py

This script:
  1. Generates several synthetic traces
  2. Saves one to a file and reloads it (to test the file loader)
  3. Runs the NoPrefetcher baseline through each trace
  4. Prints results — your teammates' prefetchers will plug in here
"""

from trace import (
    generate_sequential,
    generate_strided,
    generate_random,
    generate_mixed,
    generate_looping,
    load_trace_file,
    save_trace_file,
    PrefetcherHarness,
)
from prefetcher_base import NoPrefetcher
from prefetcher_nextline import NextLinePrefetcher
from prefetcher_stride import StridePrefetcher
from prefetcher_stream import GHBPrefetcher


def run_experiment(harness: PrefetcherHarness, prefetcher, accesses, trace_name: str):
    """Helper: run one prefetcher on one trace and print results."""
    stats = harness.run(prefetcher, accesses)
    harness.print_stats(stats, prefetcher_name=f"{prefetcher.name} | {trace_name}")
    return stats


def main():
    print("=" * 60)
    print("  Hardware Prefetcher Lab — Infrastructure Demo")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Generate synthetic traces
    # ------------------------------------------------------------------
    print("\n[1] Generating synthetic traces (1000 accesses each)...")

    traces = {
        "Sequential":  generate_sequential(num_accesses=1000),
        "Strided-128": generate_strided(num_accesses=1000, stride=128),
        "Random":      generate_random(num_accesses=1000),
        "Mixed":       generate_mixed(num_accesses=1000),
        "Looping":     generate_looping(num_accesses=1000, loop_size=16),
    }

    for name, trace in traces.items():
        print(f"  {name:15s}: {len(trace)} accesses, "
              f"first addr = 0x{trace[0].address:08x}")

    # ------------------------------------------------------------------
    # 2. Save a trace to file and reload it (tests the file loader)
    # ------------------------------------------------------------------
    print("\n[2] Testing file save/load...")
    save_trace_file(traces["Mixed"], "sample_trace.csv")

    reloaded = load_trace_file("sample_trace.csv")
    print(f"  Reloaded {len(reloaded)} accesses from file.")
    assert len(reloaded) == len(traces["Mixed"]), "Mismatch after reload!"
    print("  File save/load: OK")

    # ------------------------------------------------------------------
    # 3. Run the baseline (no prefetcher) on all traces
    # ------------------------------------------------------------------
    print("\n[3] Running baseline (No Prefetcher) on all traces...")

    harness = PrefetcherHarness(cache_size_kb=32, block_size=64, prefetch_degree=4)
    baseline = NoPrefetcher()

    for trace_name, accesses in traces.items():
        run_experiment(harness, baseline, accesses, trace_name)

    # ------------------------------------------------------------------
    # 4. Verbose demo on a tiny trace (so you can see step-by-step)
    # ------------------------------------------------------------------
    print("\n[4] Verbose step-by-step demo (10 accesses, sequential):")
    tiny_trace = generate_sequential(num_accesses=10, start=0, stride=64)
    harness.run(baseline, tiny_trace, verbose=True)

    # ------------------------------------------------------------------
    # 5. Placeholder: teammates plug their prefetchers in here
    # ------------------------------------------------------------------
    print("\n[5] Запуск и проверка алгоритмов команды:")

    # Проверяем Next-Line на последовательных адресах
    run_experiment(harness, NextLinePrefetcher(), traces['Sequential'], 'Sequential')

    # Проверяем Stride на страйдовой трассе (шаг 128)
    run_experiment(harness, StridePrefetcher(), traces['Strided-128'], 'Strided-128')

    # Проверяем сложный Stream на смешанной трассе
    run_experiment(harness, GHBPrefetcher(), traces['Strided-128'], 'Strided-128')


if __name__ == "__main__":
    main()
