"""`uv run edt <command>` entry point. Commands are added by BE-02 onwards."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    print("edt: no commands yet (spike, ingest, maps, manifest, golden arrive in BE-02..BE-10)")
    return 0 if not argv else 2


if __name__ == "__main__":
    raise SystemExit(main())
