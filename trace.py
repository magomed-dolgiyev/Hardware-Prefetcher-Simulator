"""
trace.py — Memory Access Trace Infrastructure
Hardware Prefetcher Lab

This module does three things:
  1. Defines what a memory access looks like (MemoryAccess)
  2. Generates synthetic traces for testing (generate_*)
  3. Loads real trace files from disk (load_trace_file)

Everyone on the team imports from this file.
"""

import random
import csv
from dataclasses import dataclass
from typing import List, Iterator


# ---------------------------------------------------------------------------
# Data structure: one memory access
# ---------------------------------------------------------------------------

@dataclass
class MemoryAccess:
    """
    Represents a single memory access in a trace.

    address : the memory address being accessed (integer)
    is_write: True if it's a store (write), False if it's a load (read)
    pc      : program counter — the instruction that caused this access
              (optional, used by advanced prefetchers like GHB)
    """
    address: int
    is_write: bool = False
    pc: int = 0

    def cache_line(self, block_size: int = 64) -> int:
        """Return which cache line this address belongs to."""
        return self.address // block_size

    def __repr__(self):
        rw = "W" if self.is_write else "R"
        return f"MemAccess({rw} addr=0x{self.address:08x} line={self.cache_line()} pc=0x{self.pc:04x})"


# ---------------------------------------------------------------------------
# Synthetic trace generators
# ---------------------------------------------------------------------------

def generate_sequential(num_accesses: int, start: int = 0, stride: int = 64) -> List[MemoryAccess]:
    """
    Sequential access pattern — like iterating over an array.
    This is the easiest pattern for a prefetcher to predict.

    Example: 0x000, 0x040, 0x080, 0x0C0, ...
    """
    accesses = []
    address = start
    for i in range(num_accesses):
        accesses.append(MemoryAccess(address=address, pc=0x1000))
        address += stride
    return accesses


def generate_strided(num_accesses: int, stride: int = 128, start: int = 0) -> List[MemoryAccess]:
    """
    Fixed-stride access pattern — like accessing every N-th element of an array.
    A stride prefetcher should detect this well.

    Example with stride=128: 0x000, 0x080, 0x100, 0x180, ...
    """
    accesses = []
    address = start
    for i in range(num_accesses):
        accesses.append(MemoryAccess(address=address, pc=0x2000))
        address += stride
    return accesses


def generate_random(num_accesses: int, address_space: int = 1024 * 1024) -> List[MemoryAccess]:
    """
    Fully random access pattern — worst case for prefetchers.
    Useful for measuring false-positive prefetch rate.

    address_space: total range of addresses to sample from (default 1MB)
    """
    accesses = []
    for _ in range(num_accesses):
        addr = random.randint(0, address_space - 1)
        # Align to 8 bytes to be more realistic
        addr = (addr // 8) * 8
        accesses.append(MemoryAccess(address=addr, pc=0x3000))
    return accesses


def generate_mixed(num_accesses: int) -> List[MemoryAccess]:
    """
    Realistic mixed pattern: mostly sequential with occasional random jumps.
    Simulates a real program that has loops but also pointer chasing.

    About 80% sequential, 20% random jumps — a common real-world ratio.
    """
    accesses = []
    address = 0
    for i in range(num_accesses):
        if random.random() < 0.8:
            # Sequential step
            address += 64
        else:
            # Random jump (pointer chase, function call, etc.)
            address = random.randint(0, 512 * 1024)
            address = (address // 64) * 64  # align to cache line
        pc = 0x4000 + (i % 16) * 4  # simulate a few different PCs
        accesses.append(MemoryAccess(address=address, pc=pc))
    return accesses


def generate_looping(num_accesses: int, loop_size: int = 16, block_size: int = 64) -> List[MemoryAccess]:
    """
    Loop pattern — repeatedly accesses the same small set of addresses.
    Models a working set that fits in L1/L2 cache.

    loop_size: how many distinct cache lines in the loop
    """
    # Create the set of addresses in the loop
    base = 0x10000
    loop_addresses = [base + i * block_size for i in range(loop_size)]

    accesses = []
    for i in range(num_accesses):
        addr = loop_addresses[i % loop_size]
        accesses.append(MemoryAccess(address=addr, pc=0x5000))
    return accesses


# ---------------------------------------------------------------------------
# File loader — reads real trace files
# ---------------------------------------------------------------------------

def load_trace_file(filepath: str, max_accesses: int = None) -> List[MemoryAccess]:
    """
    Load a memory access trace from a file.

    Supported formats:
      1. CSV with columns: address, [is_write], [pc]
         Example line:  4096,0,8192
                        means: read from address 4096, pc=8192

      2. Simple text — one address per line (hex or decimal)
         Example line:  0x00001000
                        1048576

    max_accesses: stop after this many (useful for large files)

    Returns a list of MemoryAccess objects.
    """
    accesses = []

    with open(filepath, "r") as f:
        # Peek at first non-comment line to detect format
        first_line = ""
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                first_line = line
                break

        if not first_line:
            return []  # empty file

        # Detect if it's CSV (has commas) or plain addresses
        is_csv = "," in first_line

        # Reopen to read from the beginning
        f.seek(0)

        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            try:
                if is_csv:
                    parts = line.split(",")
                    address = int(parts[0], 0)          # '0' base = auto hex/dec
                    is_write = bool(int(parts[1])) if len(parts) > 1 else False
                    pc = int(parts[2], 0) if len(parts) > 2 else 0
                else:
                    address = int(line, 0)
                    is_write = False
                    pc = 0

                accesses.append(MemoryAccess(address=address, is_write=is_write, pc=pc))

            except (ValueError, IndexError) as e:
                print(f"  [trace loader] Skipping bad line: {repr(line)} — {e}")
                continue

            if max_accesses and len(accesses) >= max_accesses:
                break

    return accesses


def save_trace_file(accesses: List[MemoryAccess], filepath: str):
    """
    Save a trace to a CSV file so it can be reused or shared with teammates.

    Format: address,is_write,pc  (one access per line)
    """
    with open(filepath, "w", newline="") as f:
        f.write("# Hardware Prefetcher Lab — Memory Trace\n")
        f.write("# Format: address,is_write,pc\n")
        for acc in accesses:
            f.write(f"{acc.address},{int(acc.is_write)},{acc.pc}\n")
    print(f"Saved {len(accesses)} accesses to {filepath}")


# ---------------------------------------------------------------------------
# Harness — plugs any prefetcher into a trace and runs it
# ---------------------------------------------------------------------------

class PrefetcherHarness:
    """
    The harness feeds a trace through a prefetcher and measures results.

    Your teammates implement prefetchers. Each prefetcher must have:
      - prefetcher.access(mem_access)  → called on every real access
      - prefetcher.get_prefetches()    → returns list of addresses to prefetch
      - prefetcher.reset()             → resets internal state

    The harness handles the cache simulation and all the bookkeeping.
    """

    def __init__(self, cache_size_kb: int = 32, block_size: int = 64, prefetch_degree: int = 4):
        """
        cache_size_kb  : how big the simulated cache is (default 32 KB)
        block_size     : cache line size in bytes (default 64 bytes — standard)
        prefetch_degree: max prefetches allowed per access
        """
        self.block_size = block_size
        self.prefetch_degree = prefetch_degree

        # Calculate how many cache lines fit
        self.num_lines = (cache_size_kb * 1024) // block_size

        # The cache: a set of cache line addresses currently in cache
        self.cache: set = set()

        # Stats counters
        self.total_accesses = 0
        self.hits = 0           # access found in cache
        self.misses = 0         # access not in cache
        self.prefetch_hits = 0  # prefetched line was actually used later
        self.prefetch_issued = 0
        self.prefetched_lines: set = set()  # lines currently prefetched but not yet used

    def reset(self):
        """Clear cache and reset all counters."""
        self.cache.clear()
        self.prefetched_lines.clear()
        self.total_accesses = 0
        self.hits = 0
        self.misses = 0
        self.prefetch_hits = 0
        self.prefetch_issued = 0

    def _cache_line_addr(self, address: int) -> int:
        """Convert a byte address to its cache line address."""
        return (address // self.block_size) * self.block_size

    def _insert_into_cache(self, line_addr: int):
        """Insert a cache line, evicting oldest if full (simple FIFO eviction)."""
        if len(self.cache) >= self.num_lines:
            # Evict one entry (convert to list for pop — simple FIFO approximation)
            evict = next(iter(self.cache))
            self.cache.discard(evict)
            self.prefetched_lines.discard(evict)
        self.cache.add(line_addr)

    def run(self, prefetcher, accesses: List[MemoryAccess], verbose: bool = False) -> dict:
        """
        Run a full trace through a prefetcher and return statistics.

        prefetcher: any prefetcher object (implements access() and get_prefetches())
        accesses  : list of MemoryAccess objects from trace.py
        verbose   : if True, print each step (useful for debugging small traces)

        Returns a dict with all statistics.
        """
        self.reset()
        prefetcher.reset()

        for acc in accesses:
            self.total_accesses += 1
            line_addr = self._cache_line_addr(acc.address)

            # --- Check if this access is a hit or miss ---
            if line_addr in self.cache:
                self.hits += 1
                if line_addr in self.prefetched_lines:
                    self.prefetch_hits += 1
                    self.prefetched_lines.discard(line_addr)
                if verbose:
                    print(f"  HIT  {acc}")
            else:
                self.misses += 1
                self._insert_into_cache(line_addr)
                if verbose:
                    print(f"  MISS {acc}")

            # --- Ask the prefetcher what to fetch next ---
            prefetcher.access(acc)
            candidates = prefetcher.get_prefetches()

            # Only issue up to prefetch_degree prefetches
            for pf_addr in candidates[:self.prefetch_degree]:
                pf_line = self._cache_line_addr(pf_addr)
                if pf_line not in self.cache:
                    self._insert_into_cache(pf_line)
                    self.prefetched_lines.add(pf_line)
                    self.prefetch_issued += 1
                    if verbose:
                        print(f"    PREFETCH → 0x{pf_addr:08x} (line 0x{pf_line:08x})")

        return self._compute_stats()

    def _compute_stats(self) -> dict:
        """Calculate and return all metrics as a dictionary."""
        hit_rate = self.hits / self.total_accesses if self.total_accesses > 0 else 0
        miss_rate = self.misses / self.total_accesses if self.total_accesses > 0 else 0

        # Accuracy: of all prefetches issued, how many were actually used?
        accuracy = self.prefetch_hits / self.prefetch_issued if self.prefetch_issued > 0 else 0

        # Coverage: of all misses, how many did prefetching turn into hits?
        total_potential_misses = self.misses + self.prefetch_hits
        coverage = self.prefetch_hits / total_potential_misses if total_potential_misses > 0 else 0
        return {
            "total_accesses": self.total_accesses,
            "hits":           self.hits,
            "misses":         self.misses,
            "hit_rate":       round(hit_rate, 4),
            "miss_rate":      round(miss_rate, 4),
            "prefetch_issued":  self.prefetch_issued,
            "prefetch_hits":    self.prefetch_hits,
            "prefetch_accuracy": round(accuracy, 4),   # precision
            "prefetch_coverage": round(coverage, 4),   # recall
        }

    def print_stats(self, stats: dict, prefetcher_name: str = "Prefetcher"):
        """Pretty-print the statistics from a run."""
        print(f"\n{'='*50}")
        print(f"  Results: {prefetcher_name}")
        print(f"{'='*50}")
        print(f"  Total accesses : {stats['total_accesses']}")
        print(f"  Cache hits     : {stats['hits']}  ({stats['hit_rate']*100:.1f}%)")
        print(f"  Cache misses   : {stats['misses']} ({stats['miss_rate']*100:.1f}%)")
        print(f"  Prefetches issued : {stats['prefetch_issued']}")
        print(f"  Prefetch hits     : {stats['prefetch_hits']}")
        print(f"  Prefetch accuracy : {stats['prefetch_accuracy']*100:.1f}%  (issued that were used)")
        print(f"  Prefetch coverage : {stats['prefetch_coverage']*100:.1f}%  (misses avoided)")
        print(f"{'='*50}\n")
