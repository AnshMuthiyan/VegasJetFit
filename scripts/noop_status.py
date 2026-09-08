#!/usr/bin/env python3
"""
No-op status updater.

Used when a queue watcher should not attempt to update a campaign spreadsheet
or write auxiliary status products.
"""

from __future__ import annotations

import sys


def main() -> int:
    _ = sys.argv[1:]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
