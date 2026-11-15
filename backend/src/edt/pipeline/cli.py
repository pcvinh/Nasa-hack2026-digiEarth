"""`uv run edt <command>`: spike, ingest, maps, manifest, golden, regions."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from edt.catalogue import get_variable, variables
from edt.config import load_settings


def _vars(arg: str | None):
    if not arg or arg == "all":
        return list(variables().values())
    v = get_variable(arg)
    if v is None:
        raise SystemExit(f"unknown variable {arg!r}; known: {', '.join(variables())}")
    return [v]


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("earthaccess").setLevel(logging.WARNING)
    p = argparse.ArgumentParser(prog="edt")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("spike")
    s.add_argument("--variable", default="all")
    s.add_argument("--month", default="2020-07")
    i = sub.add_parser("ingest")
    i.add_argument("--variable", default="all")
    i.add_argument("--start", type=int)
    i.add_argument("--end", type=int)
    i.add_argument("--keep-raw", action="store_true")
    mp = sub.add_parser("maps")
    mp.add_argument("--variable", default="all")
    sub.add_parser("manifest")
    sub.add_parser("golden")
    sub.add_parser("regions")
    a = p.parse_args(sys.argv[1:] if argv is None else argv)
    settings = load_settings()

    if a.cmd == "spike":
        from edt.pipeline.spike import spike

        for v in _vars(a.variable):
            print(json.dumps(spike(settings, v, a.month), ensure_ascii=False))
    elif a.cmd == "ingest":
        from edt.pipeline.ingest import ingest

        for v in _vars(a.variable):
            r = ingest(
                settings,
                v,
                start=f"{a.start}-01" if a.start else None,
                end=f"{a.end}-12" if a.end else None,
                keep_raw=a.keep_raw,
            )
            logging.info("%s done: %s", v.id, r)
    elif a.cmd == "maps":
        from edt.pipeline.maps import build_map

        for v in _vars(a.variable):
            logging.info("%s map: %s", v.id, build_map(settings, v))
    elif a.cmd == "manifest":
        from edt.pipeline.manifest import write_manifest

        print(json.dumps(write_manifest(settings), indent=1)[:2000])
    elif a.cmd == "golden":
        from edt.golden import write_golden

        write_golden(settings)
    elif a.cmd == "regions":
        from edt.regions.build import build_presets

        build_presets()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
