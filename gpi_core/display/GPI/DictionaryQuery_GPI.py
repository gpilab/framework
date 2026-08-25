"""Query and inspect dictionary data.

This is the canonical spelling of the legacy DictionQuery node.  The legacy
module remains available so existing networks continue to load.
"""

from .dictionquery_GPI import ExternalNode as _DictionQueryNode


class ExternalNode(_DictionQueryNode):
    """Display and selectively inspect nested dictionary data."""

    pass