"""Build regions/presets.geojson (committed). Run with `uv run edt regions`.

Boundaries: geoBoundaries gbOpen ADM1 (simplified release, commit 9469f09, build 12 Dec 2023).
"""

from __future__ import annotations

import json
import unicodedata
import urllib.request
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

OUT = Path(__file__).with_name("presets.geojson")
GB = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/{c}/ADM1/geoBoundaries-{c}-ADM1_simplified.geojson"
MAX_VERTICES = 500

MEKONG = [
    "Long An",
    "Tiền Giang",
    "Bến Tre",
    "Trà Vinh",
    "Vĩnh Long",
    "Đồng Tháp",
    "An Giang",
    "Kiên Giang",
    "Cần Thơ",
    "Hậu Giang",
    "Sóc Trăng",
    "Bạc Liêu",
    "Cà Mau",
]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def _fetch(country: str) -> dict:
    import ssl

    import certifi

    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(GB.format(c=country), timeout=120, context=ctx) as r:
        return json.load(r)


def _units(country: str, names: list[str]):
    data = _fetch(country)
    want = {_norm(n) for n in names}
    geoms = [
        shape(f["geometry"])
        for f in data["features"]
        if _norm(f["properties"]["shapeName"]) in want
    ]
    found = {_norm(f["properties"]["shapeName"]) for f in data["features"]} & want
    if found != want:
        raise RuntimeError(f"{country}: missing units {want - found}")
    return unary_union(geoms)


def _vertices(g) -> int:
    polys = getattr(g, "geoms", [g])
    return sum(len(p.exterior.coords) + sum(len(i.coords) for i in p.interiors) for p in polys)


def _simplify(g):
    tol = 0.0
    out = g
    while _vertices(out) >= MAX_VERTICES:
        tol = tol * 1.5 if tol else 0.005
        out = g.simplify(tol, preserve_topology=True)
    return out


def build_presets() -> None:
    gb_note = (
        "geoBoundaries gbOpen ADM1, simplified release (github wmgeolab/geoBoundaries "
        "commit 9469f09, build 12 Dec 2023); {lic}; {extra}Simplified to <500 vertices. "
        "Accessed 15 Nov 2026."
    )
    regions = [
        dict(
            id="mekong-delta",
            name="Mekong Delta",
            country="Vietnam",
            regionType="river_delta",
            description="The low, flat delta where the Mekong River meets the sea in southern "
            "Vietnam: rice paddies, fruit orchards, fish farms and many canals.",
            geom=_units("VNM", MEKONG),
            geometrySource=gb_note.format(
                lic="Public Domain (per geoBoundaries metadata)",
                extra="Union of the 13 Mekong Delta provinces in the 2008-based edition (before "
                "Vietnam's 2025 province mergers): " + ", ".join(MEKONG) + ". ",
            ),
            suggestedVariableIds=["precipitation", "soil_moisture", "ndvi", "air_temperature"],
        ),
        dict(
            id="central-java",
            name="Central Java",
            country="Indonesia",
            regionType="agricultural",
            description="A densely farmed Indonesian province on the island of Java, with rice "
            "terraces, volcanoes and a monsoon climate.",
            geom=_units("IDN", ["Central Java"]),
            geometrySource=gb_note.format(
                lic="source OpenStreetMap/Wambacher, licence ODbL 1.0 (© OpenStreetMap "
                "contributors)",
                extra="ADM1 unit 'Central Java'. ",
            ),
            suggestedVariableIds=["precipitation", "ndvi", "soil_moisture", "air_temperature"],
        ),
        dict(
            id="johor",
            name="Johor",
            country="Malaysia",
            regionType="agricultural",
            description="The southern tip of peninsular Malaysia, next to Singapore, with large "
            "oil palm and rubber plantations and growing cities.",
            geom=_units("MYS", ["Johor"]),
            geometrySource=gb_note.format(
                lic="source OpenStreetMap/Wambacher, licence ODbL 1.0 (© OpenStreetMap "
                "contributors)",
                extra="ADM1 unit 'Johor'. ",
            ),
            suggestedVariableIds=["ndvi", "precipitation", "air_temperature", "soil_moisture"],
        ),
        dict(
            id="amazon-central",
            name="Central Amazon",
            country="Brazil",
            regionType="rainforest",
            description="The heart of the Amazon rainforest around Manaus, where the Rio Negro "
            "and the Solimões join.",
            geom=box(-66.0, -7.0, -56.0, -1.0),
            geometrySource="Documented simplified rectangle, not an official boundary: longitude "
            "66°W–56°W, latitude 7°S–1°S, centred on the Manaus area of the central Amazon basin. "
            "Chosen to cover mostly continuous rainforest at 0.5° resolution. Defined 15 Nov 2026.",
            suggestedVariableIds=["precipitation", "ndvi", "air_temperature", "soil_moisture"],
        ),
        dict(
            id="sahel",
            name="Sahel",
            country=None,
            regionType="desert_edge",
            description="The semi-arid belt south of the Sahara, from Senegal to Sudan, where "
            "rainfall decides whether grass and crops can grow.",
            geom=box(-17.0, 12.0, 35.0, 18.0),
            geometrySource="Documented simplified band, not an official boundary: latitude "
            "12°N–18°N, longitude 17°W–35°E (Atlantic coast of Senegal to central Sudan, stopping "
            "west of the Ethiopian highlands). Common climatological Sahel definition. Defined 15 "
            "Nov 2026.",
            suggestedVariableIds=["precipitation", "ndvi", "soil_moisture", "air_temperature"],
        ),
    ]
    features = []
    for r in regions:
        g = _simplify(r.pop("geom"))
        c = g.centroid
        props = {
            **r,
            "center": [round(c.x, 4), round(c.y, 4)],
            "bbox": [round(v, 4) for v in g.bounds],
            "vertexCount": _vertices(g),
        }
        features.append({"type": "Feature", "properties": props, "geometry": mapping(g)})
    OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    for f in features:
        print(f["properties"]["id"], f["properties"]["vertexCount"], f["properties"]["bbox"])
