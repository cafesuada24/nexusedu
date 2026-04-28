from collections import OrderedDict


class BoundedDict[K, V](OrderedDict[K, V]):
    """A dictionary with a fixed maximum size, evicting the oldest items."""
    def __init__(self, *args: object, maxsize: int = 1000, **kwargs: V) -> None:
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: K, value: V) -> None:
        if key not in self and len(self) >= self.maxsize:
            self.popitem(last=False)
        super().__setitem__(key, value)
