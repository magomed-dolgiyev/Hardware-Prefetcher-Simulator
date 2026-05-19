# prefetcher_nextline.py
from prefetcher_base import BasePrefetcher

class NextLinePrefetcher(BasePrefetcher):
    def __init__(self, block_size: int = 64):
        super().__init__(name="Next-Line Prefetcher")
        self.block_size = block_size
        self._next = None  # последняя предложенная адресация (необязательно)

    def reset(self):
        self._next = None

    def access(self, mem_access):
        # Префетчим следующий кэш-лайн относительно текущего адреса
        line_base = (mem_access.address // self.block_size) * self.block_size
        self._next = line_base + self.block_size

    def get_prefetches(self) -> list:
        # Возвращаем один кандидат — следующий кэш-лайн
        return [self._next] if self._next is not None else []
