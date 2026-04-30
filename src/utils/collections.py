"""Custom collection types for the application."""

from collections import OrderedDict


class BoundedDict[K, V](OrderedDict[K, V]):
    """A dictionary with a fixed maximum size, evicting the oldest items."""

    def __init__(self, *args: object, maxsize: int = 1000, **kwargs: V) -> None:
        """Initialize the BoundedDict.

        Args:
            *args: Variable length argument list.
            maxsize: Maximum number of items to keep.
            **kwargs: Arbitrary keyword arguments.
        """
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: K, value: V) -> None:
        """Add an item to the dictionary, evicting the oldest if full.

        Args:
            key: The key to add.
            value: The value to add.
        """
        if key not in self and len(self) >= self.maxsize:
            self.popitem(last=False)
        super().__setitem__(key, value)
