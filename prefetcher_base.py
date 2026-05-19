"""
prefetcher_base.py — Base class for all prefetchers
Hardware Prefetcher Lab

Every prefetcher in this project must inherit from BasePrefetcher.
This ensures they all work with the PrefetcherHarness in trace.py.

There is also a NoPrefetcher here — it does nothing.
Use it as a baseline to see how much prefetching actually helps.
"""


class BasePrefetcher:
    """
    Base class that every prefetcher must inherit from.

    Teammates: copy this interface when building your prefetcher.

    Required methods:
      access(mem_access)   — called on every memory access in the trace
      get_prefetches()     — return a list of addresses to prefetch right now
      reset()              — reset all internal state (called before each run)
    """

    def __init__(self, name: str = "BasePrefetcher"):
        self.name = name

    def access(self, mem_access):
        """
        Called for every memory access in the trace.
        Update your internal state (history, stride detector, etc.) here.

        mem_access: a MemoryAccess object from trace.py
          mem_access.address  — byte address
          mem_access.pc       — program counter
          mem_access.is_write — True if store, False if load
        """
        raise NotImplementedError("Subclasses must implement access()")

    def get_prefetches(self) -> list:
        """
        Return a list of addresses to prefetch after the last access() call.
        The harness will fetch up to `prefetch_degree` of these into the cache.

        Return an empty list if you have nothing to prefetch.
        """
        raise NotImplementedError("Subclasses must implement get_prefetches()")

    def reset(self):
        """Reset all internal state. Called before each experiment run."""
        raise NotImplementedError("Subclasses must implement reset()")

    def __str__(self):
        return self.name


class NoPrefetcher(BasePrefetcher):
    """
    The baseline: does absolutely nothing.
    Use this to measure cache performance WITHOUT any prefetching.
    Every other prefetcher should beat this.
    """

    def __init__(self):
        super().__init__(name="No Prefetcher (baseline)")

    def access(self, mem_access):
        pass  # do nothing

    def get_prefetches(self) -> list:
        return []  # never prefetch anything

    def reset(self):
        pass  # nothing to reset
