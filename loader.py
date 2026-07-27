"""Compatibility import for older notebooks.

New code should import :class:`minidatadev.data.DatasetLoader`.
"""

from minidatadev.data import DatasetLoader

__all__ = ["DatasetLoader"]
