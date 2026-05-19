from prefetcher_base import BasePrefetcher
from collections import deque


class GHBPrefetcher(BasePrefetcher):
    """
    GHB (Global History Buffer) Prefetcher — PC-indexed delta correlation.
 Fixed version: prediction is made AFTER the history is updated,
 to avoid eternal blocking due to deque size limitations.
    """

    def __init__(
            self,
            history_size: int = 256,
            lookback: int = 2,
            degree: int = 4,
            block_size: int = 64,
    ):
        super().__init__(name="GHB Prefetcher (PC-indexed)")
        self.block_size = block_size
        self.history_size = history_size
        self.lookback = lookback
        self.degree = degree

        # Global buffer to match the GHB concept
        self.ghb: deque = deque(maxlen=history_size)

        # Store the cache line history for each PC (maxlen = lookback + 1)
        self.pc_lines: dict = {}
        self._candidates: list = []

    def reset(self):
        self.ghb.clear()
        self.pc_lines.clear()
        self._candidates = []

    def _line_base(self, addr: int) -> int:
        return (addr // self.block_size) * self.block_size

    def access(self, mem_access):
        addr_line = self._line_base(mem_access.address)
        pc = mem_access.pc

        self._candidates = []

        # 1. First, we UPDATE the history
        self.ghb.append((pc, addr_line))

        if pc not in self.pc_lines:
            self.pc_lines[pc] = deque(maxlen=self.lookback + 1)
        self.pc_lines[pc].appendleft(addr_line)  # The new address falls at the beginning (index 0)

        # 2. Now we make a prediction
        history = self.pc_lines[pc]
        if len(history) >= self.lookback + 1:
            lines = list(history)  # [current, last, second-to-last]

            # We calculate the deltas (differences) between adjacent addresses
            # If lookback=2, there will be two deltas: (current - last) and (last - позапрошлый)
            deltas = [lines[i] - lines[i + 1] for i in range(self.lookback)]

            # If all deltas are the same and not equal to zero (there is a stable step/stride)
            if all(d == deltas[0] for d in deltas) and deltas[0] != 0:
                stride = deltas[0]
                # Generate addresses forward by the degree of pre-election (degree)
                next_line = addr_line + stride
                for _ in range(self.degree):
                    self._candidates.append(next_line)
                    next_line += stride

    def get_prefetches(self) -> list:
        c = self._candidates
        self._candidates = []
        return c