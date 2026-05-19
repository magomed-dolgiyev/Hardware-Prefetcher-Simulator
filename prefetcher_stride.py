# prefetcher_stride.py
from prefetcher_base import BasePrefetcher

class StridePrefetcher(BasePrefetcher):
    def __init__(self, degree: int = 2, confirm_threshold: int = 2, block_size: int = 64):
        super().__init__(name="Stride Prefetcher")
        self.block_size = block_size
        self.degree = degree
        self.confirm_threshold = confirm_threshold
        # Состояние по PC: { pc: {last_addr, last_stride, confidence} }
        self.state = {}
        self._candidates = []

    def reset(self):
        self.state.clear()
        self._candidates = []

    def _line_base(self, addr: int) -> int:
        return (addr // self.block_size) * self.block_size

    def access(self, mem_access):
        pc = mem_access.pc
        addr = self._line_base(mem_access.address)

        st = self.state.get(pc)
        if st is None:
            self.state[pc] = {"last_addr": addr, "last_stride": None, "confidence": 0}
            self._candidates = []
            return

        last_addr = st["last_addr"]
        observed_stride = addr - last_addr

        if st["last_stride"] == observed_stride:
            st["confidence"] += 1
        else:
            st["last_stride"] = observed_stride
            st["confidence"] = 1

        st["last_addr"] = addr

        # Если страйд подтверждён — предсказываем несколько шагов вперёд
        self._candidates = []
        if st["confidence"] >= self.confirm_threshold and observed_stride != 0:
            next_addr = addr + observed_stride
            for _ in range(self.degree):
                self._candidates.append(next_addr)
                next_addr += observed_stride

    def get_prefetches(self) -> list:
        # Вернём и обнулим лист (Harness сам обрежет по prefetch_degree)
        cands = self._candidates
        self._candidates = []
        return cands
