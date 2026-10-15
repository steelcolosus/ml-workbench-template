"""
Local-first store for pipeline data and artifacts, with optional S3 sync.

See the "Store" section of the project README for configuration and examples.
"""

from core.store.store import STORE_CONFIG_ENV, Location, Store

__all__ = ["STORE_CONFIG_ENV", "Location", "Store"]
